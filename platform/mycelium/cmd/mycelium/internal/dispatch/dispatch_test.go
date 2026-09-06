package dispatch

import (
	"os"
	"path/filepath"
	"slices"
	"testing"
)

func TestLookup_NativeCommands(t *testing.T) {
	nativeCommands := []string{"status", "shell", "health", "doctor", "ask", "version", "config"}
	for _, verb := range nativeCommands {
		t.Run(verb, func(t *testing.T) {
			route := Lookup(verb)
			if route.Kind != KindNative {
				t.Errorf("Lookup(%q) Kind = %v, want KindNative", verb, route.Kind)
			}
		})
	}
}

func TestLookup_ShellOutCommands(t *testing.T) {
	shellOutCommands := []string{
		"bootstrap", "start", "stop", "swarm", "dream", "migrate",
		"ingest-repo", "fork", "sync", "drift", "dump", "restore",
	}
	for _, verb := range shellOutCommands {
		t.Run(verb, func(t *testing.T) {
			route := Lookup(verb)
			if route.Kind != KindShellOut {
				t.Errorf("Lookup(%q) Kind = %v, want KindShellOut", verb, route.Kind)
			}
		})
	}
}

func TestLookup_UnknownVerb(t *testing.T) {
	route := Lookup("bogus")
	if route.Kind != KindUnknown {
		t.Errorf("Lookup(\"bogus\") Kind = %v, want KindUnknown", route.Kind)
	}
}

func TestRegistry_NonEmpty(t *testing.T) {
	routes := Registry()
	if len(routes) < 15 {
		t.Errorf("Registry() returned %d routes, want at least 15", len(routes))
	}
}

func TestRegistry_Sorted(t *testing.T) {
	routes := Registry()
	if len(routes) == 0 {
		t.Skip("Registry is empty, skipping sort check")
	}

	for i := 1; i < len(routes); i++ {
		if routes[i].Verb < routes[i-1].Verb {
			t.Errorf("Registry not sorted: routes[%d].Verb (%q) < routes[%d].Verb (%q)",
				i, routes[i].Verb, i-1, routes[i-1].Verb)
		}
	}
}

func TestRegistry_AllHaveDescription(t *testing.T) {
	routes := Registry()
	for i, route := range routes {
		if route.Description == "" {
			t.Errorf("routes[%d] (%q) has empty Description", i, route.Verb)
		}
	}
}

func TestFindMyceliumDev_RespectsNewEnvVar(t *testing.T) {
	// Create a temporary file to act as mycelium-dev
	tmpDir := t.TempDir()
	fakeExe := filepath.Join(tmpDir, "mycelium-dev")
	if err := os.WriteFile(fakeExe, []byte("#!/bin/sh\n"), 0755); err != nil {
		t.Fatalf("failed to create fake mycelium-dev: %v", err)
	}

	// Set the new env var
	t.Setenv("MYCELIUM_DEV_PATH", fakeExe)
	t.Setenv("MAVERICK_DEV_PATH", "")

	result := FindMyceliumDev()
	if result != fakeExe {
		t.Errorf("FindMyceliumDev() with MYCELIUM_DEV_PATH=%q returned %q, want %q",
			fakeExe, result, fakeExe)
	}
}

func TestFindMyceliumDev_BackcompatOldEnvVar(t *testing.T) {
	// Create a temporary file to act as mycelium-dev (using old name)
	tmpDir := t.TempDir()
	fakeExe := filepath.Join(tmpDir, "mycelium-dev")
	if err := os.WriteFile(fakeExe, []byte("#!/bin/sh\n"), 0755); err != nil {
		t.Fatalf("failed to create fake mycelium-dev: %v", err)
	}

	// Set the old env var
	t.Setenv("MAVERICK_DEV_PATH", fakeExe)
	t.Setenv("MYCELIUM_DEV_PATH", "")

	result := FindMyceliumDev()
	if result != fakeExe {
		t.Errorf("FindMyceliumDev() with MYCELIUM_DEV_PATH=%q returned %q, want %q",
			fakeExe, result, fakeExe)
	}
}

func TestFindMyceliumDev_FallsBackToPATH(t *testing.T) {
	// Create a temporary directory and add it to PATH
	tmpDir := t.TempDir()
	fakeExe := filepath.Join(tmpDir, "mycelium-dev")
	if err := os.WriteFile(fakeExe, []byte("#!/bin/sh\n"), 0755); err != nil {
		t.Fatalf("failed to create fake mycelium-dev: %v", err)
	}

	// Clear the env vars
	t.Setenv("MYCELIUM_DEV_PATH", "")
	t.Setenv("MAVERICK_DEV_PATH", "")

	// Prepend tmpDir to PATH
	originalPath := os.Getenv("PATH")
	newPath := tmpDir + string(os.PathListSeparator) + originalPath
	t.Setenv("PATH", newPath)

	result := FindMyceliumDev()
	if result != fakeExe {
		t.Errorf("FindMyceliumDev() with PATH containing %q returned %q, want %q",
			tmpDir, result, fakeExe)
	}
}

func TestFindMyceliumDev_NotFound(t *testing.T) {
	// Clear both env vars and PATH to ensure it's not found
	t.Setenv("MYCELIUM_DEV_PATH", "")
	t.Setenv("MAVERICK_DEV_PATH", "")
	t.Setenv("PATH", "")

	result := FindMyceliumDev()
	if result != "" {
		t.Errorf("FindMyceliumDev() with clean env returned %q, want empty string", result)
	}
}

func TestLookup_AllRegistryVerbsAreResolvable(t *testing.T) {
	routes := Registry()
	for _, route := range routes {
		lookedUp := Lookup(route.Verb)
		if lookedUp.Kind == KindUnknown {
			t.Errorf("Lookup(%q) returned KindUnknown, but %q is in Registry", route.Verb, route.Verb)
		}
		if lookedUp.Verb != route.Verb {
			t.Errorf("Lookup(%q).Verb = %q, want %q", route.Verb, lookedUp.Verb, route.Verb)
		}
	}
}

func TestRegistry_NoVerbDuplicates(t *testing.T) {
	routes := Registry()
	seen := make(map[string]bool)
	for i, route := range routes {
		if seen[route.Verb] {
			t.Errorf("routes[%d] (%q) is a duplicate", i, route.Verb)
		}
		seen[route.Verb] = true
	}
}

func TestRegistry_AllHaveKind(t *testing.T) {
	routes := Registry()
	for i, route := range routes {
		if route.Kind == KindUnknown {
			t.Errorf("routes[%d] (%q) has Kind=KindUnknown", i, route.Verb)
		}
	}
}

func TestRegistry_ExpectedVerbsPresent(t *testing.T) {
	routes := Registry()
	verbs := make([]string, len(routes))
	for i, route := range routes {
		verbs[i] = route.Verb
	}

	expectedNative := []string{"status", "shell", "health", "doctor", "ask", "version", "config"}
	expectedShellOut := []string{
		"bootstrap", "start", "stop", "swarm", "dream", "migrate",
		"ingest-repo", "fork", "sync", "drift", "dump", "restore",
	}
	expectedAll := append(expectedNative, expectedShellOut...)

	for _, verb := range expectedAll {
		if !slices.Contains(verbs, verb) {
			t.Errorf("Registry missing expected verb %q", verb)
		}
	}
}
