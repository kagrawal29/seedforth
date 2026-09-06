// Regression test for issue #40: autodeploy fork-bomb on pulse-server.
//
// Scenario: the mycelium-dev shim re-invokes the same Go binary. Without a
// guard, each bootstrap call fork-bombs until the systemd service cgroup hits
// TasksMax and fork returns EAGAIN. Autodeploy sits broken for days.
//
// Guard: MYCELIUM_SHELLOUT_DEPTH is incremented every time the binary execs
// a dev shim. If the binary is re-entered with depth >= 1, it refuses.
package main

import (
	"bytes"
	"os"
	"strings"
	"testing"
)

// TestRunShellOut_RefusesRecursion asserts that when the binary is re-entered
// with MYCELIUM_SHELLOUT_DEPTH already set, runShellOut refuses instead of
// forking into another shim.
func TestRunShellOut_RefusesRecursion(t *testing.T) {
	t.Setenv(shelloutDepthEnv, "1")
	// Even with a path env pointing nowhere, we should short-circuit before
	// the exec attempt — the recursion guard fires first.
	t.Setenv("MYCELIUM_DEV_PATH", "/nonexistent/does-not-matter")

	var stdout, stderr bytes.Buffer
	code := runShellOut("bootstrap", []string{}, &stdout, &stderr)

	if code != 1 {
		t.Errorf("expected exit code 1 on recursion refusal, got %d", code)
	}
	msg := stderr.String()
	if !strings.Contains(msg, "recursion detected") {
		t.Errorf("expected stderr to mention recursion detection, got: %q", msg)
	}
	if !strings.Contains(msg, "issue #40") {
		t.Errorf("expected stderr to reference issue #40 for traceability, got: %q", msg)
	}
}

// TestRunShellOut_NoRecursionWhenDepthUnset asserts that a clean environment
// still takes the normal path (no false positive). With no dev shim on PATH,
// we expect the usual 127 "toolchain required" exit, not the recursion error.
func TestRunShellOut_NoRecursionWhenDepthUnset(t *testing.T) {
	// Ensure neither the depth sentinel nor any dev-shim pointer is set.
	os.Unsetenv(shelloutDepthEnv)
	t.Setenv("MYCELIUM_DEV_PATH", "")
	t.Setenv("MYCELIUM_DEV_PATH", "")
	// Scrub PATH so LookPath("mycelium-dev") / LookPath("mycelium-dev") fail.
	t.Setenv("PATH", t.TempDir())

	var stdout, stderr bytes.Buffer
	code := runShellOut("bootstrap", []string{}, &stdout, &stderr)

	if code != 127 {
		t.Errorf("expected exit code 127 (toolchain missing) on clean env, got %d; stderr=%q",
			code, stderr.String())
	}
	if strings.Contains(stderr.String(), "recursion detected") {
		t.Errorf("false positive: recursion guard fired on clean env; stderr=%q", stderr.String())
	}
}
