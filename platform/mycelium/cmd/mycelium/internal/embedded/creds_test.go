package embedded

import (
	"testing"
)

func clearRuntimeCredentials(t *testing.T) {
	t.Helper()
	for _, name := range []string{
		"MYCELIUM_DEV_BOLT_URI", "MYCELIUM_DEV_USER", "MYCELIUM_DEV_PASSWORD",
		"MYCELIUM_STAGING_BOLT_URI", "MYCELIUM_STAGING_USER", "MYCELIUM_STAGING_PASSWORD",
		"MYCELIUM_PROD_BOLT_URI", "MYCELIUM_PROD_USER", "MYCELIUM_PROD_PASSWORD",
	} {
		t.Setenv(name, "")
	}
}

func TestLoadRequiresRuntimeCredentials(t *testing.T) {
	clearRuntimeCredentials(t)
	if _, err := Load(); err == nil {
		t.Fatal("Load() succeeded without runtime credentials")
	}
}

func TestLoadReadsRuntimeCredentials(t *testing.T) {
	clearRuntimeCredentials(t)
	t.Setenv("MYCELIUM_DEV_BOLT_URI", "bolt://example.test:7687")
	t.Setenv("MYCELIUM_DEV_USER", "neo4j")
	t.Setenv("MYCELIUM_DEV_PASSWORD", "test-only-secret")

	creds, err := Load()
	if err != nil {
		t.Fatalf("Load() returned error: %v", err)
	}
	if creds.Dev.BoltURI != "bolt://example.test:7687" || creds.Dev.User != "neo4j" || creds.Dev.Password != "test-only-secret" {
		t.Fatalf("runtime credentials were not loaded correctly: %#v", creds.Dev)
	}
}

// TestVersionStampNonEmpty ensures VersionStamp is non-empty.
func TestVersionStampNonEmpty(t *testing.T) {
	if VersionStamp == "" {
		t.Fatal("VersionStamp is empty")
	}
}
