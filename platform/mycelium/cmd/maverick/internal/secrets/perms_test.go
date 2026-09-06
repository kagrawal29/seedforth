package secrets

import (
	"errors"
	"os"
	"runtime"
	"testing"
)

func TestCheckFilePerms(t *testing.T) {
	// Test case a: 0600 permissions on linux/mac should pass
	t.Run("0600_permissions_valid", func(t *testing.T) {
		if runtime.GOOS == "windows" {
			t.Skip("POSIX permissions not applicable on Windows")
		}

		tmpdir := t.TempDir()
		file := tmpdir + "/credentials"
		err := os.WriteFile(file, []byte("secret"), 0644)
		if err != nil {
			t.Fatalf("failed to create test file: %v", err)
		}

		// Set to 0600
		err = os.Chmod(file, 0600)
		if err != nil {
			t.Fatalf("failed to chmod file to 0600: %v", err)
		}

		err = CheckFilePerms(file)
		if err != nil {
			t.Errorf("expected nil for 0600 permissions, got error: %v", err)
		}
	})

	// Test case b: 0640 permissions should return error with "permissions" or "mode" and mention expected 0600
	t.Run("0640_permissions_invalid", func(t *testing.T) {
		if runtime.GOOS == "windows" {
			t.Skip("POSIX permissions not applicable on Windows")
		}

		tmpdir := t.TempDir()
		file := tmpdir + "/credentials"
		err := os.WriteFile(file, []byte("secret"), 0644)
		if err != nil {
			t.Fatalf("failed to create test file: %v", err)
		}

		// Set to 0640
		err = os.Chmod(file, 0640)
		if err != nil {
			t.Fatalf("failed to chmod file to 0640: %v", err)
		}

		err = CheckFilePerms(file)
		if err == nil {
			t.Errorf("expected error for 0640 permissions, got nil")
		}

		errStr := err.Error()
		if !containsWord(errStr, "permissions") && !containsWord(errStr, "mode") {
			t.Errorf("error should contain 'permissions' or 'mode', got: %s", errStr)
		}

		if !containsWord(errStr, "0600") {
			t.Errorf("error should mention expected 0600, got: %s", errStr)
		}
	})

	// Test case c: 0644 permissions should return error with "permissions" or "mode" and mention expected 0600
	t.Run("0644_permissions_invalid", func(t *testing.T) {
		if runtime.GOOS == "windows" {
			t.Skip("POSIX permissions not applicable on Windows")
		}

		tmpdir := t.TempDir()
		file := tmpdir + "/credentials"
		err := os.WriteFile(file, []byte("secret"), 0644)
		if err != nil {
			t.Fatalf("failed to create test file: %v", err)
		}

		// File is already 0644 from WriteFile
		err = CheckFilePerms(file)
		if err == nil {
			t.Errorf("expected error for 0644 permissions, got nil")
		}

		errStr := err.Error()
		if !containsWord(errStr, "permissions") && !containsWord(errStr, "mode") {
			t.Errorf("error should contain 'permissions' or 'mode', got: %s", errStr)
		}

		if !containsWord(errStr, "0600") {
			t.Errorf("error should mention expected 0600, got: %s", errStr)
		}
	})

	// Test case d: 0600 on Windows should be skipped
	t.Run("0600_permissions_windows", func(t *testing.T) {
		if runtime.GOOS == "windows" {
			t.Skip("POSIX perms not applicable")
		}

		tmpdir := t.TempDir()
		file := tmpdir + "/credentials"
		err := os.WriteFile(file, []byte("secret"), 0644)
		if err != nil {
			t.Fatalf("failed to create test file: %v", err)
		}

		err = os.Chmod(file, 0600)
		if err != nil {
			t.Fatalf("failed to chmod file to 0600: %v", err)
		}

		err = CheckFilePerms(file)
		if err != nil {
			t.Errorf("expected nil for 0600 permissions on non-Windows, got error: %v", err)
		}
	})

	// Test case e: File does not exist should return error wrapping os.ErrNotExist
	t.Run("file_not_exist", func(t *testing.T) {
		err := CheckFilePerms("/nonexistent/path/to/credentials")
		if err == nil {
			t.Errorf("expected error for nonexistent file, got nil")
		}

		if !errors.Is(err, os.ErrNotExist) {
			t.Errorf("expected error to wrap os.ErrNotExist, got: %v", err)
		}
	})
}

// containsWord checks if the string contains the given word (case-insensitive substring check).
func containsWord(s, word string) bool {
	for i := 0; i < len(s); i++ {
		if i+len(word) > len(s) {
			break
		}
		match := true
		for j := 0; j < len(word); j++ {
			sc := s[i+j]
			wc := word[j]
			// Simple case-insensitive comparison
			if sc >= 'A' && sc <= 'Z' {
				sc = sc - 'A' + 'a'
			}
			if wc >= 'A' && wc <= 'Z' {
				wc = wc - 'A' + 'a'
			}
			if sc != wc {
				match = false
				break
			}
		}
		if match {
			return true
		}
	}
	return false
}
