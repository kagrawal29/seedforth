# Human interface release checks

Use Microsoft's `@playwright/cli`, pinned here to 0.1.19. These are browser
journeys, not replacements for API, Cypher, isolation or product acceptance tests.

Start the shipped static UI in one terminal:

```sh
python3 -m http.server 18787 --bind 127.0.0.1 --directory platform/control/web
```

Run the synthetic-response regression through the CLI:

```sh
npx --yes @playwright/cli@0.1.19 -s=seedforth-upgrade open http://127.0.0.1:18787
npx --yes @playwright/cli@0.1.19 -s=seedforth-upgrade run-code --filename platform/integration-tests/control-ui.playwright.js --raw
```

This covers login, credential storage, untrusted graph text, stale observations,
selected-file drift and explicit partial-coverage warnings,
legacy work, hold/version conflict, outage recovery, desktop/mobile layout,
out-of-order inspectors, in-flight logout and revocation. Screenshots go to the
ignored `.playwright-cli/` directory. API failures intentionally exercised by the
test appear as browser network errors; unexpected failures must be investigated.

For real HTTP + Cypher end-to-end qualification, first run the disposable graph
integration suite to seed the canonical plan and scope fixtures. Never substitute
the production or restored-production endpoint. In separate terminals:

```sh
ssh -N -L 27474:127.0.0.1:27474 root@185.192.96.100
python3 platform/integration-tests/serve-control-ui-fixture.py
```

Wait for the fixture gateway's ready message, then:

```sh
npx --yes @playwright/cli@0.1.19 -s=seedforth-upgrade run-code --filename platform/integration-tests/control-ui-graph.playwright.js --raw
npx --yes @playwright/cli@0.1.19 -s=seedforth-upgrade close
```

The graph journey uses a deliberately synthetic platform-only credential, loads
22 plan items, toggles a versioned hold, reconnects to verify persistence, restores
the original hold disposition, and checks denial of another scope. Signals remain
as test evidence in the disposable graph. It never changes production. Stop the
fixture gateway and tunnel when finished. Its temporary credential directory is
removed on normal shutdown. Do not put real credentials in CLI arguments or traces.

Public OAuth/MCP, team provisioning, conversation, richer controls/reviews and
future interfaces require additional real end-to-end journeys as they land. These
two passing suites do not qualify those unimplemented experiences.
