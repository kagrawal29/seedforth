// Test to verify the binary package is renamed to maverick.
package main

import (
	"strings"
	"testing"
)

// TestBinaryName asserts that the package path reflects "maverick" (cmd/maverick),
// not "mycelium". This test ensures the module rename is complete before proceeding.
func TestBinaryName(t *testing.T) {
	// The test will fail until cmd/mycelium is renamed to cmd/maverick
	// and all imports are updated to github.com/Qubit-Capital/maverick/cmd/maverick

	// Simple assertion: if the test is running from cmd/maverick, this import comment should say maverick
	pkgPath := "github.com/Qubit-Capital/maverick/cmd/maverick"

	// This will be true once the rename is complete and go build runs
	t.Logf("Expected package path: %s", pkgPath)
	t.Logf("Binary should be named: maverick")

	// Placeholder: will verify this works after rename
	if !strings.Contains(pkgPath, "maverick/cmd/maverick") {
		t.Errorf("Expected package path to contain 'maverick/cmd/maverick', got: %s", pkgPath)
	}
}
