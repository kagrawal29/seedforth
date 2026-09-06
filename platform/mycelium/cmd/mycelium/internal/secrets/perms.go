package secrets

import (
	"fmt"
	"os"
	"runtime"
)

// CheckFilePerms verifies that a file has secure permissions (0600 on POSIX systems).
// The implementation will use os.Stat to retrieve file metadata, then check the
// permission bits via FileMode.Perm(). This avoids subprocess calls and integrates
// directly with the standard library's file permission model.
// On Windows, the permission model is different and this check is not applicable.
func CheckFilePerms(path string) error {
	// On Windows, permissions are not applicable
	if runtime.GOOS == "windows" {
		return nil
	}

	// Stat the file
	info, err := os.Stat(path)
	if err != nil {
		// Wrap the error if it's NotExist or similar
		return fmt.Errorf("failed to stat file: %w", err)
	}

	// Get the permission bits
	perms := info.Mode().Perm()

	// Check if permissions are exactly 0600
	if perms != 0600 {
		return fmt.Errorf("file has insecure permissions: mode %#o (expected 0600), path: %s", perms, path)
	}

	return nil
}
