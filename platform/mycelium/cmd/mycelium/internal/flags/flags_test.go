package flags

import (
	"strings"
	"testing"
	"time"
)

// Test case (a): --target dev before subcommand
func TestTargetBeforeSubcommand(t *testing.T) {
	argv := []string{"--target", "dev", "status"}
	p, err := Parse(argv)
	if err != nil {
		t.Fatalf("Parse failed: %v", err)
	}
	if p.Target != "dev" {
		t.Errorf("expected Target='dev', got %q", p.Target)
	}
	if p.Subcommand != "status" {
		t.Errorf("expected Subcommand='status', got %q", p.Subcommand)
	}
}

// Test case (b): status --target dev after subcommand (order-independent)
func TestTargetAfterSubcommand(t *testing.T) {
	argv := []string{"status", "--target", "dev"}
	p, err := Parse(argv)
	if err != nil {
		t.Fatalf("Parse failed: %v", err)
	}
	if p.Target != "dev" {
		t.Errorf("expected Target='dev', got %q", p.Target)
	}
	if p.Subcommand != "status" {
		t.Errorf("expected Subcommand='status', got %q", p.Subcommand)
	}
}

// Test case (c): multiple --target positions; last one wins.
// Behavior: when --target is specified multiple times, the last occurrence wins.
// This test documents that behavior. If you want "ambiguous target" error instead,
// change this test and update Parse() to detect duplicates and error.
func TestMultipleTargets(t *testing.T) {
	argv := []string{"status", "--target", "dev", "shell", "--target", "prod"}
	p, err := Parse(argv)
	if err != nil {
		t.Fatalf("Parse failed: %v", err)
	}
	// Last --target wins: prod
	if p.Target != "prod" {
		t.Errorf("expected Target='prod' (last wins), got %q", p.Target)
	}
	if p.Subcommand != "status" {
		t.Errorf("expected Subcommand='status', got %q", p.Subcommand)
	}
}

// Test case (d): invalid target value should error.
// Error message must mention the invalid value and valid options.
func TestInvalidTarget(t *testing.T) {
	argv := []string{"--target", "junk", "status"}
	p, err := Parse(argv)
	if err == nil {
		t.Fatalf("expected error for invalid target, got result: %+v", p)
	}
	errMsg := err.Error()
	// Error must mention the invalid value or that it's unknown
	if !strings.Contains(errMsg, "junk") &&
		!strings.Contains(errMsg, "unknown target") &&
		!strings.Contains(errMsg, "invalid target") {
		t.Errorf("error message should mention invalid value or 'unknown target': %s", errMsg)
	}
	// Error should hint at valid values
	if !strings.Contains(errMsg, "dev") &&
		!strings.Contains(errMsg, "prod") &&
		!strings.Contains(errMsg, "valid") {
		t.Errorf("error message should list or hint at valid targets: %s", errMsg)
	}
}

// Test case (e): --json flag sets JSON=true
func TestJSONFlag(t *testing.T) {
	argv := []string{"--json", "status"}
	p, err := Parse(argv)
	if err != nil {
		t.Fatalf("Parse failed: %v", err)
	}
	if !p.JSON {
		t.Errorf("expected JSON=true, got false")
	}
	if p.Subcommand != "status" {
		t.Errorf("expected Subcommand='status', got %q", p.Subcommand)
	}
}

// Test case (f): --timeout 45s parses duration correctly
func TestTimeoutFlag(t *testing.T) {
	argv := []string{"--timeout", "45s", "status"}
	p, err := Parse(argv)
	if err != nil {
		t.Fatalf("Parse failed: %v", err)
	}
	expected := 45 * time.Second
	if p.Timeout != expected {
		t.Errorf("expected Timeout=%v, got %v", expected, p.Timeout)
	}
}

// Test case (g): invalid duration should error with "timeout" or "duration" in message
func TestInvalidTimeout(t *testing.T) {
	argv := []string{"--timeout", "invalid", "status"}
	p, err := Parse(argv)
	if err == nil {
		t.Fatalf("expected error for invalid timeout, got result: %+v", p)
	}
	errMsg := strings.ToLower(err.Error())
	if !strings.Contains(errMsg, "timeout") &&
		!strings.Contains(errMsg, "duration") {
		t.Errorf("error message should mention 'timeout' or 'duration': %s", err.Error())
	}
}

// Test case (h): --quiet flag sets Quiet=true
func TestQuietFlag(t *testing.T) {
	argv := []string{"--quiet", "status"}
	p, err := Parse(argv)
	if err != nil {
		t.Fatalf("Parse failed: %v", err)
	}
	if !p.Quiet {
		t.Errorf("expected Quiet=true, got false")
	}
	if p.Subcommand != "status" {
		t.Errorf("expected Subcommand='status', got %q", p.Subcommand)
	}
}

// Test case (i): default values when no flags are provided.
// Defaults: Target="" (empty), Timeout=30s, JSON=false, Quiet=false.
func TestDefaults(t *testing.T) {
	argv := []string{"status"}
	p, err := Parse(argv)
	if err != nil {
		t.Fatalf("Parse failed: %v", err)
	}
	if p.Target != "" {
		t.Errorf("expected Target='' (empty), got %q", p.Target)
	}
	expected := 30 * time.Second
	if p.Timeout != expected {
		t.Errorf("expected Timeout=%v (default), got %v", expected, p.Timeout)
	}
	if p.JSON {
		t.Errorf("expected JSON=false (default), got true")
	}
	if p.Quiet {
		t.Errorf("expected Quiet=false (default), got true")
	}
	if p.Subcommand != "status" {
		t.Errorf("expected Subcommand='status', got %q", p.Subcommand)
	}
}

// Additional tests for robustness

// Test: multiple flags mixed with subcommand and args
func TestMixedFlagsAndArgs(t *testing.T) {
	argv := []string{"--target", "prod", "--json", "shell", "MATCH", "(n)", "RETURN", "n"}
	p, err := Parse(argv)
	if err != nil {
		t.Fatalf("Parse failed: %v", err)
	}
	if p.Target != "prod" {
		t.Errorf("expected Target='prod', got %q", p.Target)
	}
	if !p.JSON {
		t.Errorf("expected JSON=true, got false")
	}
	if p.Subcommand != "shell" {
		t.Errorf("expected Subcommand='shell', got %q", p.Subcommand)
	}
	expectedArgs := []string{"MATCH", "(n)", "RETURN", "n"}
	if len(p.Args) != len(expectedArgs) {
		t.Errorf("expected Args length %d, got %d", len(expectedArgs), len(p.Args))
	}
	for i, arg := range expectedArgs {
		if i >= len(p.Args) || p.Args[i] != arg {
			t.Errorf("expected Args[%d]=%q, got %q", i, arg, p.Args[i])
		}
	}
}

// Test: --quiet and --json together
func TestQuietAndJSON(t *testing.T) {
	argv := []string{"--quiet", "--json", "ask", "hello world"}
	p, err := Parse(argv)
	if err != nil {
		t.Fatalf("Parse failed: %v", err)
	}
	if !p.Quiet {
		t.Errorf("expected Quiet=true, got false")
	}
	if !p.JSON {
		t.Errorf("expected JSON=true, got false")
	}
	if p.Subcommand != "ask" {
		t.Errorf("expected Subcommand='ask', got %q", p.Subcommand)
	}
}

// Test: flags after subcommand with args
func TestFlagsAfterSubcommandWithArgs(t *testing.T) {
	argv := []string{"shell", "MATCH", "(x)", "--target", "staging"}
	p, err := Parse(argv)
	if err != nil {
		t.Fatalf("Parse failed: %v", err)
	}
	if p.Target != "staging" {
		t.Errorf("expected Target='staging', got %q", p.Target)
	}
	if p.Subcommand != "shell" {
		t.Errorf("expected Subcommand='shell', got %q", p.Subcommand)
	}
	// Args should contain MATCH and (x)
	if len(p.Args) < 2 {
		t.Errorf("expected Args to include subcommand args, got %v", p.Args)
	}
}

// Test: all targets are recognized
func TestAllValidTargets(t *testing.T) {
	for target := range ValidTargets {
		argv := []string{"--target", target, "status"}
		p, err := Parse(argv)
		if err != nil {
			t.Errorf("unexpected error for valid target %q: %v", target, err)
		}
		if p == nil {
			t.Errorf("Parse returned nil for valid target %q", target)
		}
		if p != nil && p.Target != target {
			t.Errorf("expected Target=%q, got %q", target, p.Target)
		}
	}
}

// Test: timeout with different units
func TestTimeoutVariants(t *testing.T) {
	tests := []struct {
		input    string
		expected time.Duration
	}{
		{"1s", 1 * time.Second},
		{"60s", 60 * time.Second},
		{"1m", 1 * time.Minute},
		{"1m30s", 1*time.Minute + 30*time.Second},
	}
	for _, tt := range tests {
		argv := []string{"--timeout", tt.input, "status"}
		p, err := Parse(argv)
		if err != nil {
			t.Errorf("unexpected error for timeout %q: %v", tt.input, err)
			continue
		}
		if p.Timeout != tt.expected {
			t.Errorf("timeout %q: expected %v, got %v", tt.input, tt.expected, p.Timeout)
		}
	}
}
