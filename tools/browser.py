#!/usr/bin/env python3
"""browser.py -- token-efficient CDP browser control for delta agents.

Drives the persistent, logged-in Chromium profiles that already run on
delta-server, over the Chrome DevTools Protocol. No Claude-in-Chrome, no
Playwright MCP -- a plain CLI that returns concise text, so agents spend
tokens on the task, not on browser plumbing.

Each profile is a long-lived `*-chromium.service` with its own user-data-dir
(kept logged in). We only CONNECT to it; we never launch or log in here.

Profiles (name -> CDP port) available to delta agents:
  charlie    9224   /home/charlie-browser/chromium     (charlietheagent606@gmail.com)
  seedforth  9223   /home/seedforth-browser/chromium   (Google session)

(iris on 9222 is Revti Digital's browser and is intentionally NOT exposed here.)

Concurrency model (so many delta instances can share one browser):
  Task verbs (get/shot/eval) open their OWN throwaway tab, do the work, then
  close it -- they share the profile's LOGIN COOKIES but never touch each
  other's tab or the human's noVNC tab. Safe to run from many agents at once.
  Inspection verbs (read/open) act on the current visible tab -- use for
  checking state after a manual login in noVNC.

Two ways to use a profile:

CONCURRENT READ (own throwaway tab, safe for many agents at once):
  browser.py profiles                          list profiles + reachability
  browser.py get   <profile> <url> [--max N]   own tab: navigate, print page text
  browser.py shot  <profile> <url> <path.png>  own tab: navigate, full-page screenshot
  browser.py eval  <profile> <url> "<js>"      own tab: navigate, run JS, print result

INTERACTIVE FLOW (drives the ONE visible tab -- do one flow at a time per
profile). This is how you log into a service and pull a key:
  browser.py open  <profile> <url>             navigate the visible tab
  browser.py see   <profile> [path.png]        screenshot the visible tab (your eyes)
  browser.py read  <profile> [--max N]         print the visible tab's text
  browser.py click <profile> "<text|css>"      click a button/link (by text, else CSS)
  browser.py fill  <profile> "<css>" "<value>" type into an input field
  browser.py press <profile> <Key>             keyboard press (e.g. Enter, Tab)

Typical "sign in with Google as charlie" flow:
  browser.py open  charlie https://vercel.com/login
  browser.py see   charlie /tmp/step.png       # look, then decide next click
  browser.py click charlie "Continue with Google"
  browser.py see   charlie /tmp/step.png
  browser.py click charlie "charlietheagent606@gmail.com"   # account chooser
  # ...land on dashboard, navigate to tokens, read/copy the key
"""
import sys
import json

PROFILES = {
    "charlie": 9224,
    "seedforth": 9223,
}


def _connect(pw, port):
    b = pw.chromium.connect_over_cdp(f"http://127.0.0.1:{port}", timeout=8000)
    ctx = b.contexts[0] if b.contexts else b.new_context()
    pg = ctx.pages[0] if ctx.pages else ctx.new_page()
    return b, pg


def cmd_profiles():
    import urllib.request
    for name, port in PROFILES.items():
        status = "unreachable"
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/json/version", timeout=4) as r:
                v = json.load(r)
                status = f"up ({v.get('Browser', '?')})"
        except Exception as e:
            status = f"down ({type(e).__name__})"
        print(f"{name:10} port {port}  {status}")


def _run(profile, fn):
    """Run fn against the profile's CURRENT visible tab (read/open)."""
    if profile not in PROFILES:
        sys.exit(f"unknown profile {profile!r}; known: {', '.join(PROFILES)}")
    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        b, pg = _connect(pw, PROFILES[profile])
        try:
            return fn(pg)
        finally:
            b.close()  # detaches CDP; does NOT close the persistent browser


def _run_fresh(profile, url, fn):
    """Open an OWN throwaway tab (shares login cookies), navigate, run fn, close it.

    This is what lets many delta instances share one logged-in browser without
    colliding on a tab.
    """
    if profile not in PROFILES:
        sys.exit(f"unknown profile {profile!r}; known: {', '.join(PROFILES)}")
    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        b = pw.chromium.connect_over_cdp(f"http://127.0.0.1:{PROFILES[profile]}", timeout=8000)
        ctx = b.contexts[0] if b.contexts else b.new_context()
        pg = ctx.new_page()
        try:
            pg.goto(url, wait_until="domcontentloaded", timeout=30000)
            return fn(pg)
        finally:
            try:
                pg.close()
            finally:
                b.close()


def cmd_get(profile, url, max_chars):
    def fn(pg):
        txt = pg.inner_text("body")
        print(f"[{pg.url}] {pg.title()}\n---")
        print(txt[:max_chars])
    _run_fresh(profile, url, fn)


def cmd_shot(profile, url, path):
    def fn(pg):
        pg.screenshot(path=path, full_page=True)
        print(f"saved {path}")
    _run_fresh(profile, url, fn)


def cmd_eval(profile, url, js):
    def fn(pg):
        print(json.dumps(pg.evaluate(js), default=str)[:4000])
    _run_fresh(profile, url, fn)


def cmd_open(profile, url):
    def fn(pg):
        pg.goto(url, wait_until="domcontentloaded", timeout=30000)
        print(f"{pg.title()}\n{pg.url}")
    _run(profile, fn)


def cmd_read(profile, max_chars):
    def fn(pg):
        txt = pg.inner_text("body")
        print(f"[{pg.url}] {pg.title()}\n---")
        print(txt[:max_chars])
    _run(profile, fn)


def cmd_see(profile, path):
    def fn(pg):
        pg.screenshot(path=path, full_page=False)
        print(f"[{pg.url}] {pg.title()}\nsaved {path}")
    _run(profile, fn)


def _looks_like_css(target):
    return target.startswith((".", "#", "[")) or target.endswith((")", "]")) or " > " in target


def cmd_click(profile, target):
    def fn(pg):
        # Prefer a visible text/role match (buttons, links, account chooser rows);
        # fall back to a raw CSS selector.
        if not _looks_like_css(target):
            for locator in (
                pg.get_by_role("button", name=target),
                pg.get_by_role("link", name=target),
                pg.get_by_text(target, exact=False),
            ):
                try:
                    if locator.count() == 0:
                        continue
                    locator.first.click(timeout=6000)
                    print(f"clicked {target!r} -> now {pg.url[:70]}")
                    return
                except Exception:
                    continue
            sys.exit(f"no button/link/text matching {target!r} on {pg.url[:70]} "
                     f"(use `see` to look, or pass a CSS selector)")
        pg.click(target, timeout=8000)
        print(f"clicked {target!r} -> now {pg.url[:70]}")
    _run(profile, fn)


def cmd_fill(profile, selector, value):
    def fn(pg):
        pg.fill(selector, value, timeout=8000)
        print(f"filled {selector!r}")
    _run(profile, fn)


def cmd_press(profile, key):
    def fn(pg):
        pg.keyboard.press(key)
        print(f"pressed {key} -> now {pg.url[:70]}")
    _run(profile, fn)


def main(argv):
    if not argv or argv[0] in ("-h", "--help", "help"):
        print(__doc__)
        return
    cmd, rest = argv[0], argv[1:]
    mx = 4000
    if "--max" in rest:
        i = rest.index("--max")
        mx = int(rest[i + 1])
        rest = rest[:i] + rest[i + 2:]
    if cmd == "profiles":
        cmd_profiles()
    elif cmd == "get":
        cmd_get(rest[0], rest[1], mx)
    elif cmd == "shot":
        cmd_shot(rest[0], rest[1], rest[2])
    elif cmd == "eval":
        cmd_eval(rest[0], rest[1], rest[2])
    elif cmd == "open":
        cmd_open(rest[0], rest[1])
    elif cmd == "read":
        cmd_read(rest[0], mx)
    elif cmd == "see":
        cmd_see(rest[0], rest[1] if len(rest) > 1 else "/tmp/browser-see.png")
    elif cmd == "click":
        cmd_click(rest[0], rest[1])
    elif cmd == "fill":
        cmd_fill(rest[0], rest[1], rest[2])
    elif cmd == "press":
        cmd_press(rest[0], rest[1])
    else:
        sys.exit(f"unknown command {cmd!r}; see --help")


if __name__ == "__main__":
    main(sys.argv[1:])
