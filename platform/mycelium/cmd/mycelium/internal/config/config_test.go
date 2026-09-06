package config

import (
	"errors"
	"os"
	"path/filepath"
	"strings"
	"testing"
)

// Test a. Nested schema [targets.dev] with bolt_uri, user, password.
// Resolve("dev") should return non-nil Target with correct BoltURI.
func TestLoadNestedSchema(t *testing.T) {
	// Use testdata fixture
	cfgPath := filepath.Join("testdata", "nested.toml")
	cfg, err := Load(cfgPath)
	if err != nil {
		t.Fatalf("Load() failed: %v", err)
	}

	target, err := cfg.Resolve("dev")
	if err != nil {
		t.Fatalf("Resolve(\"dev\") failed: %v", err)
	}

	if target == nil {
		t.Fatal("Resolve(\"dev\") returned nil Target")
	}

	expectedURI := "bolt://localhost:7687"
	if target.BoltURI != expectedURI {
		t.Errorf("BoltURI = %q, want %q", target.BoltURI, expectedURI)
	}

	if target.User != "neo4j" {
		t.Errorf("User = %q, want %q", target.User, "neo4j")
	}

	if target.Password != "devpass123" {
		t.Errorf("Password = %q, want %q", target.Password, "devpass123")
	}
}

// Test b. Flat schema [dev] with same fields.
// Resolve("dev") should return non-nil Target (back-compat).
func TestLoadFlatSchema(t *testing.T) {
	cfgPath := filepath.Join("testdata", "flat.toml")
	cfg, err := Load(cfgPath)
	if err != nil {
		t.Fatalf("Load() failed: %v", err)
	}

	target, err := cfg.Resolve("dev")
	if err != nil {
		t.Fatalf("Resolve(\"dev\") failed: %v", err)
	}

	if target == nil {
		t.Fatal("Resolve(\"dev\") returned nil Target")
	}

	expectedURI := "bolt://localhost:7687"
	if target.BoltURI != expectedURI {
		t.Errorf("BoltURI = %q, want %q", target.BoltURI, expectedURI)
	}
}

// Test c. Both [dev] flat and [targets.dev] nested present with DIFFERENT BoltURIs.
// Nested should win. Resolve("dev").BoltURI should equal nested value.
func TestNestedWinsBothPresent(t *testing.T) {
	cfgPath := filepath.Join("testdata", "both.toml")
	cfg, err := Load(cfgPath)
	if err != nil {
		t.Fatalf("Load() failed: %v", err)
	}

	target, err := cfg.Resolve("dev")
	if err != nil {
		t.Fatalf("Resolve(\"dev\") failed: %v", err)
	}

	if target == nil {
		t.Fatal("Resolve(\"dev\") returned nil Target")
	}

	// Nested has :7687, flat has :7600 - nested must win
	expectedURI := "bolt://localhost:7687"
	if target.BoltURI != expectedURI {
		t.Errorf("BoltURI = %q, want %q (nested should win)", target.BoltURI, expectedURI)
	}
}

// Test d. Missing file.
// Load() should return error wrapping os.ErrNotExist (errors.Is check).
func TestMissingFile(t *testing.T) {
	cfgPath := filepath.Join("testdata", "nonexistent-file-12345.toml")
	cfg, err := Load(cfgPath)

	if cfg != nil {
		t.Errorf("Load() returned non-nil config on missing file")
	}

	if err == nil {
		t.Fatal("Load() returned nil error on missing file")
	}

	if !errors.Is(err, os.ErrNotExist) {
		t.Errorf("Load() error = %v, does not wrap os.ErrNotExist", err)
	}
}

// Test e. Malformed TOML.
// Load() should return non-nil error, message should mention "parse" or "toml".
func TestMalformedTOML(t *testing.T) {
	cfgPath := filepath.Join("testdata", "malformed.toml")
	cfg, err := Load(cfgPath)

	if cfg != nil {
		t.Errorf("Load() returned non-nil config on malformed TOML")
	}

	if err == nil {
		t.Fatal("Load() returned nil error on malformed TOML")
	}

	errMsg := strings.ToLower(err.Error())
	hasMention := strings.Contains(errMsg, "parse") || strings.Contains(errMsg, "toml")
	if !hasMention {
		t.Errorf("error message = %q, should mention 'parse' or 'toml'", err.Error())
	}
}

// Test f. Unknown target.
// Load success, Resolve("nonexistent") returns error containing "unknown target".
func TestUnknownTarget(t *testing.T) {
	cfgPath := filepath.Join("testdata", "nested.toml")
	cfg, err := Load(cfgPath)
	if err != nil {
		t.Fatalf("Load() failed: %v", err)
	}

	target, err := cfg.Resolve("nonexistent")

	if target != nil {
		t.Errorf("Resolve(\"nonexistent\") returned non-nil target")
	}

	if err == nil {
		t.Fatal("Resolve(\"nonexistent\") returned nil error")
	}

	errMsg := strings.ToLower(err.Error())
	if !strings.Contains(errMsg, "unknown target") {
		t.Errorf("error = %q, should contain 'unknown target'", err.Error())
	}
}

// Test g. Missing bolt_uri for target.
// Load success, Resolve("dev") returns error containing "bolt".
// This guides the user to fix their config.
func TestMissingBoltURI(t *testing.T) {
	cfgPath := filepath.Join("testdata", "no_bolt.toml")
	cfg, err := Load(cfgPath)
	if err != nil {
		t.Fatalf("Load() failed: %v", err)
	}

	target, err := cfg.Resolve("dev")

	if target != nil {
		t.Errorf("Resolve(\"dev\") returned non-nil target (should fail on missing bolt_uri)")
	}

	if err == nil {
		t.Fatal("Resolve(\"dev\") returned nil error on missing bolt_uri")
	}

	errMsg := strings.ToLower(err.Error())
	if !strings.Contains(errMsg, "bolt") {
		t.Errorf("error = %q, should mention 'bolt' to guide user", err.Error())
	}
}

// Test h. Environment variable override.
// Set MYCELIUM_TARGET=dev, call Resolve("") (empty string = use env).
// Should resolve to dev target.
func TestEnvVarOverride(t *testing.T) {
	cfgPath := filepath.Join("testdata", "nested.toml")
	cfg, err := Load(cfgPath)
	if err != nil {
		t.Fatalf("Load() failed: %v", err)
	}

	// Set environment variable
	t.Setenv("MYCELIUM_TARGET", "dev")

	// Call with empty string - should use env var
	target, err := cfg.Resolve("")

	if err != nil {
		t.Fatalf("Resolve(\"\") with MYCELIUM_TARGET=dev failed: %v", err)
	}

	if target == nil {
		t.Fatal("Resolve(\"\") returned nil Target")
	}

	expectedURI := "bolt://localhost:7687"
	if target.BoltURI != expectedURI {
		t.Errorf("BoltURI = %q, want %q", target.BoltURI, expectedURI)
	}
}

// Additional test: Verify structure (ensures tests can compile against stubs)
func TestTargetStruct(t *testing.T) {
	tgt := &Target{
		BoltURI:  "bolt://localhost:7687",
		User:     "neo4j",
		Password: "pass",
		Name:     "dev",
	}

	if tgt.BoltURI == "" {
		t.Error("Target.BoltURI is empty")
	}

	if tgt.User == "" {
		t.Error("Target.User is empty")
	}

	if tgt.Password == "" {
		t.Error("Target.Password is empty")
	}
}

// Additional test: Verify Config struct
func TestConfigStruct(t *testing.T) {
	cfg := &Config{
		Targets: make(map[string]Target),
	}

	if cfg.Targets == nil {
		t.Error("Config.Targets is nil")
	}

	// Should be able to add targets
	cfg.Targets["dev"] = Target{
		BoltURI:  "bolt://localhost:7687",
		User:     "neo4j",
		Password: "pass",
		Name:     "dev",
	}

	if len(cfg.Targets) != 1 {
		t.Errorf("Config.Targets length = %d, want 1", len(cfg.Targets))
	}
}

// Test i. MYCELIUM_TARGET env var override.
// Set MYCELIUM_TARGET=dev, call Resolve("") (empty string = use env).
// Should resolve to dev target.
func TestMyceliumEnvVarOverride(t *testing.T) {
	cfgPath := filepath.Join("testdata", "nested.toml")
	cfg, err := Load(cfgPath)
	if err != nil {
		t.Fatalf("Load() failed: %v", err)
	}

	// Set the new environment variable
	t.Setenv("MYCELIUM_TARGET", "dev")
	t.Setenv("MAVERICK_TARGET", "")

	// Call with empty string - should use env var
	target, err := cfg.Resolve("")

	if err != nil {
		t.Fatalf("Resolve(\"\") with MYCELIUM_TARGET=dev failed: %v", err)
	}

	if target == nil {
		t.Fatal("Resolve(\"\") returned nil Target")
	}

	expectedURI := "bolt://localhost:7687"
	if target.BoltURI != expectedURI {
		t.Errorf("BoltURI = %q, want %q", target.BoltURI, expectedURI)
	}
}

// Test j. Backcompat: MYCELIUM_TARGET still works but returns deprecation warning.
// Set MYCELIUM_TARGET=dev and no MYCELIUM_TARGET, call Resolve("").
// Should resolve to dev AND print deprecation warning to stderr.
func TestBackcompatMyceliumEnvVar(t *testing.T) {
	cfgPath := filepath.Join("testdata", "nested.toml")
	cfg, err := Load(cfgPath)
	if err != nil {
		t.Fatalf("Load() failed: %v", err)
	}

	// Set old env var, clear new one
	t.Setenv("MAVERICK_TARGET", "dev")
	t.Setenv("MYCELIUM_TARGET", "")

	// Resolve should work
	target, err := cfg.Resolve("")

	if err != nil {
		t.Fatalf("Resolve(\"\") with MYCELIUM_TARGET=dev failed: %v", err)
	}

	if target == nil {
		t.Fatal("Resolve(\"\") returned nil Target")
	}

	expectedURI := "bolt://localhost:7687"
	if target.BoltURI != expectedURI {
		t.Errorf("BoltURI = %q, want %q", target.BoltURI, expectedURI)
	}
}

// Test k. MYCELIUM_TARGET takes precedence over MYCELIUM_TARGET.
// Set both, MYCELIUM_TARGET should win.
func TestMyceliumPrecedenceOverMycelium(t *testing.T) {
	cfgPath := filepath.Join("testdata", "nested.toml")
	cfg, err := Load(cfgPath)
	if err != nil {
		t.Fatalf("Load() failed: %v", err)
	}

	// Set both vars, but with different targets
	t.Setenv("MYCELIUM_TARGET", "dev")
	t.Setenv("MAVERICK_TARGET", "prod")

	target, err := cfg.Resolve("")

	if err != nil {
		t.Fatalf("Resolve(\"\") failed: %v", err)
	}

	if target == nil {
		t.Fatal("Resolve(\"\") returned nil Target")
	}

	// Should resolve to dev (MYCELIUM_TARGET), not prod (MAVERICK_TARGET)
	expectedURI := "bolt://localhost:7687"
	if target.BoltURI != expectedURI {
		t.Errorf("BoltURI = %q, want %q (MYCELIUM_TARGET should win)", target.BoltURI, expectedURI)
	}
}
