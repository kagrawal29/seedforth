package commands

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"regexp"
	"strings"
)

// CmdUninstall removes all mycelium-managed global Claude Code changes:
// 1. Removes the marker-delimited block from ~/.claude/CLAUDE.md
// 2. Removes ~/.claude/skills/mycelium/ directory
// 3. Removes mycelium-managed permissions from ~/.claude/settings.json
// and the _myceliumManagedSince key
//
// Does NOT remove the binary (~/.mycelium); user must manually remove it.
// Preserves all non-mycelium content in those files.
// Idempotent: safe to run multiple times.
func CmdUninstall(d *CmdDeps) error {
	home, err := os.UserHomeDir()
	if err != nil {
		return fmt.Errorf("failed to get home directory: %w", err)
	}

	claudeDir := filepath.Join(home, ".claude")

	// Step 1: Remove mycelium block from CLAUDE.md
	claudeMDPath := filepath.Join(claudeDir, "CLAUDE.md")
	if err := removeMyceliumBlockFromCLAUDEMD(claudeMDPath); err != nil {
		return fmt.Errorf("failed to clean CLAUDE.md: %w", err)
	}

	// Step 2: Remove ~/.claude/skills/mycelium directory
	myceliumSkillPath := filepath.Join(claudeDir, "skills", "mycelium")
	if err := removeMyceliumSkillDir(myceliumSkillPath); err != nil {
		return fmt.Errorf("failed to remove mycelium skills: %w", err)
	}

	// Step 3: Remove mycelium permissions from settings.json
	settingsPath := filepath.Join(claudeDir, "settings.json")
	if err := cleanSettingsJSON(settingsPath); err != nil {
		return fmt.Errorf("failed to clean settings.json: %w", err)
	}

	// Print success message and instructions
	fmt.Fprintf(d.Stdout, "mycelium uninstalled successfully.\n")
	fmt.Fprintf(d.Stdout, "\nTo fully clean up, remove the binary directory:\n")
	fmt.Fprintf(d.Stdout, "  rm -rf ~/.mycelium\n")
	fmt.Fprintf(d.Stdout, "\nTo remove the symlink if it exists:\n")
	fmt.Fprintf(d.Stdout, "  sudo rm -f /usr/local/bin/mycelium\n")

	return nil
}

// removeMyceliumBlockFromCLAUDEMD removes the marker-delimited block from CLAUDE.md,
// preserving all other content. If the file doesn't exist, this is a no-op.
func removeMyceliumBlockFromCLAUDEMD(path string) error {
	content, err := os.ReadFile(path)
	if err != nil {
		if os.IsNotExist(err) {
			// File doesn't exist, nothing to clean
			return nil
		}
		return err
	}

	// Remove the block delimited by <!-- BEGIN MYCELIUM MANAGED BLOCK --> and <!-- END MYCELIUM MANAGED BLOCK -->
	// We use a regex with (?s) flag (dotall) to match across newlines.
	blockRegex := regexp.MustCompile(
		`(?s)<!--\s*BEGIN\s+MYCELIUM\s+MANAGED\s+BLOCK\s*-->.*?<!--\s*END\s+MYCELIUM\s+MANAGED\s+BLOCK\s*-->`,
	)

	newContent := blockRegex.ReplaceAllString(string(content), "")

	// Write back only if changed
	if newContent != string(content) {
		if err := os.WriteFile(path, []byte(newContent), 0600); err != nil {
			return err
		}
	}

	return nil
}

// removeMyceliumSkillDir removes the ~/.claude/skills/mycelium directory if it exists.
// If it doesn't exist, this is a no-op.
func removeMyceliumSkillDir(path string) error {
	if err := os.RemoveAll(path); err != nil && !os.IsNotExist(err) {
		return err
	}
	return nil
}

// cleanSettingsJSON removes mycelium-managed permissions and the _myceliumManagedSince key
// from ~/.claude/settings.json, preserving all other content.
// If the file doesn't exist, this is a no-op.
func cleanSettingsJSON(path string) error {
	content, err := os.ReadFile(path)
	if err != nil {
		if os.IsNotExist(err) {
			// File doesn't exist, nothing to clean
			return nil
		}
		return err
	}

	// Parse as JSON
	var obj map[string]interface{}
	if err := json.Unmarshal(content, &obj); err != nil {
		// If it's not valid JSON, just skip. The file might be empty or corrupted.
		return nil
	}

	// Remove the _myceliumManagedSince key at the top level
	delete(obj, "_myceliumManagedSince")

	// Remove mycelium-managed permissions from permissions.allow_mcp
	if perms, ok := obj["permissions"].(map[string]interface{}); ok {
		if allowMCP, ok := perms["allow_mcp"].(map[string]interface{}); ok {
			// Remove all mycelium_* keys from allow_mcp
			for key := range allowMCP {
				if strings.HasPrefix(key, "mycelium_") {
					delete(allowMCP, key)
				}
			}
			perms["allow_mcp"] = allowMCP
		}
		obj["permissions"] = perms
	}

	// Marshal back to JSON with nice formatting
	newContent, err := json.MarshalIndent(obj, "", "  ")
	if err != nil {
		return err
	}

	// Write back only if changed
	if string(newContent) != string(content) {
		if err := os.WriteFile(path, newContent, 0600); err != nil {
			return err
		}
	}

	return nil
}
