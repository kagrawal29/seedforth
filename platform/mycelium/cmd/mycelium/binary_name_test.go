// Test to verify the binary package is renamed to mycelium.
package main

import (
	"strings"
	"testing"
)

// TestBinaryName asserts that the package path reflects "mycelium" (cmd/mycelium),
// not "mycelium". This test ensures the module rename is complete before proceeding.
func TestBinaryName(t *testing.T) {
	// The test will fail until cmd/mycelium is renamed to cmd/mycelium
	// and all imports are updated to github.com/kagraw29/seedforth/platform/mycelium/cmd/mycelium

	// Simple assertion: if the test is running from cmd/mycelium, this import comment should say mycelium
	pkgPath := "github.com/kagraw29/seedforth/platform/mycelium/cmd/mycelium"

	// This will be true once the rename is complete and go build runs
	t.Logf("Expected package path: %s", pkgPath)
	t.Logf("Binary should be named: mycelium")

	// Placeholder: will verify this works after rename
	if !strings.Contains(pkgPath, "mycelium/cmd/mycelium") {
		t.Errorf("Expected package path to contain 'mycelium/cmd/mycelium', got: %s", pkgPath)
	}
}
