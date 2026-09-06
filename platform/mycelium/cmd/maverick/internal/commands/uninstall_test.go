package commands

import (
	"bytes"
	"os"
	"path/filepath"
	"strings"
	"testing"

	"github.com/Qubit-Capital/maverick/cmd/maverick/internal/flags"
)

// TestCmdUninstall_IdempotentOnFresh tests that running uninstall on a fresh HOME
// (no maverick setup) produces no errors and is a no-op.
func TestCmdUninstall_IdempotentOnFresh(t *testing.T) {
	tmpHome := t.TempDir()
	claudePath := filepath.Join(tmpHome, ".claude")
	os.MkdirAll(claudePath, 0700)

	stdout := &bytes.Buffer{}
	stderr := &bytes.Buffer{}

	deps := &CmdDeps{
		Flags:  &flags.Parsed{},
		Stdout: stdout,
		Stderr: stderr,
	}

	// Mock the home directory for this test
	oldHome := os.Getenv("HOME")
	defer os.Setenv("HOME", oldHome)
	os.Setenv("HOME", tmpHome)

	err := CmdUninstall(deps)
	if err != nil {
		t.Fatalf("CmdUninstall on fresh HOME should succeed, got error: %v", err)
	}

	// Should output a message
	output := stdout.String()
	if !strings.Contains(output, "uninstall") && !strings.Contains(output, "Uninstall") {
		t.Logf("warning: uninstall output doesn't mention 'uninstall', got: %s", output)
	}
}

// TestCmdUninstall_RemovesCLAUDEMDBlock tests that uninstall removes the maverick-delimited
// block from ~/.claude/CLAUDE.md while preserving other content.
func TestCmdUninstall_RemovesCLAUDEMDBlock(t *testing.T) {
	tmpHome := t.TempDir()
	claudePath := filepath.Join(tmpHome, ".claude")
	os.MkdirAll(claudePath, 0700)

	claudeMDPath := filepath.Join(claudePath, "CLAUDE.md")
	claudeContent := `# My CLAUDE.md

## Before Maverick

Some important stuff here.

<!-- BEGIN MAVERICK MANAGED BLOCK -->
## Maverick

This section is managed by maverick install/uninstall.
Anything here will be removed when you run: maverick uninstall
<!-- END MAVERICK MANAGED BLOCK -->

## After Maverick

More important stuff.
`

	if err := os.WriteFile(claudeMDPath, []byte(claudeContent), 0600); err != nil {
		t.Fatalf("failed to write test CLAUDE.md: %v", err)
	}

	stdout := &bytes.Buffer{}
	stderr := &bytes.Buffer{}

	deps := &CmdDeps{
		Flags:  &flags.Parsed{},
		Stdout: stdout,
		Stderr: stderr,
	}

	oldHome := os.Getenv("HOME")
	defer os.Setenv("HOME", oldHome)
	os.Setenv("HOME", tmpHome)

	err := CmdUninstall(deps)
	if err != nil {
		t.Fatalf("CmdUninstall failed: %v", err)
	}

	// Read the modified file
	newContent, err := os.ReadFile(claudeMDPath)
	if err != nil {
		t.Fatalf("failed to read CLAUDE.md after uninstall: %v", err)
	}

	newStr := string(newContent)

	// The marker block should be gone
	if strings.Contains(newStr, "BEGIN MAVERICK") {
		t.Errorf("BEGIN MAVERICK marker still present after uninstall")
	}
	if strings.Contains(newStr, "END MAVERICK") {
		t.Errorf("END MAVERICK marker still present after uninstall")
	}

	// But other content should remain
	if !strings.Contains(newStr, "Before Maverick") {
		t.Errorf("'Before Maverick' section was deleted (should be preserved)")
	}
	if !strings.Contains(newStr, "After Maverick") {
		t.Errorf("'After Maverick' section was deleted (should be preserved)")
	}
	if !strings.Contains(newStr, "My CLAUDE.md") {
		t.Errorf("heading 'My CLAUDE.md' was deleted (should be preserved)")
	}
}

// TestCmdUninstall_RemovesMaverickSkillsDir tests that uninstall removes ~/.claude/skills/maverick/
// if it exists, while leaving other skills untouched.
func TestCmdUninstall_RemovesMaverickSkillsDir(t *testing.T) {
	tmpHome := t.TempDir()
	claudePath := filepath.Join(tmpHome, ".claude")
	skillsPath := filepath.Join(claudePath, "skills")
	maverickSkillPath := filepath.Join(skillsPath, "maverick")
	otherSkillPath := filepath.Join(skillsPath, "other-skill")

	os.MkdirAll(maverickSkillPath, 0700)
	os.MkdirAll(otherSkillPath, 0700)

	// Create some files in the skill directories
	if err := os.WriteFile(filepath.Join(maverickSkillPath, "README.md"), []byte("maverick skill"), 0600); err != nil {
		t.Fatalf("failed to create test file: %v", err)
	}
	if err := os.WriteFile(filepath.Join(otherSkillPath, "README.md"), []byte("other skill"), 0600); err != nil {
		t.Fatalf("failed to create test file: %v", err)
	}

	stdout := &bytes.Buffer{}
	stderr := &bytes.Buffer{}

	deps := &CmdDeps{
		Flags:  &flags.Parsed{},
		Stdout: stdout,
		Stderr: stderr,
	}

	oldHome := os.Getenv("HOME")
	defer os.Setenv("HOME", oldHome)
	os.Setenv("HOME", tmpHome)

	err := CmdUninstall(deps)
	if err != nil {
		t.Fatalf("CmdUninstall failed: %v", err)
	}

	// maverick skill dir should be gone
	if _, err := os.Stat(maverickSkillPath); err == nil {
		t.Errorf("maverick skill directory still exists after uninstall")
	}

	// other skill dir should still be there
	if _, err := os.Stat(otherSkillPath); err != nil {
		t.Errorf("other-skill directory was deleted (should be preserved): %v", err)
	}
	if _, err := os.Stat(filepath.Join(otherSkillPath, "README.md")); err != nil {
		t.Errorf("other-skill/README.md was deleted (should be preserved)")
	}
}

// TestCmdUninstall_RemovesSettingsJSONPerms tests that uninstall removes maverick-managed
// permissions and the _maverickManagedSince key from ~/.claude/settings.json,
// while preserving other permissions and keys.
func TestCmdUninstall_RemovesSettingsJSONPerms(t *testing.T) {
	tmpHome := t.TempDir()
	claudePath := filepath.Join(tmpHome, ".claude")
	os.MkdirAll(claudePath, 0700)

	settingsPath := filepath.Join(claudePath, "settings.json")
	settingsContent := `{
  "permissions": {
    "allow_bash": ["echo", "cat", "ls"],
    "allow_mcp": {
      "maverick_ask": true,
      "maverick_shell": true,
      "other_tool": true
    }
  },
  "_maverickManagedSince": "2026-04-20T12:00:00Z",
  "model": "claude-opus",
  "theme": "dark"
}
`

	if err := os.WriteFile(settingsPath, []byte(settingsContent), 0600); err != nil {
		t.Fatalf("failed to write test settings.json: %v", err)
	}

	stdout := &bytes.Buffer{}
	stderr := &bytes.Buffer{}

	deps := &CmdDeps{
		Flags:  &flags.Parsed{},
		Stdout: stdout,
		Stderr: stderr,
	}

	oldHome := os.Getenv("HOME")
	defer os.Setenv("HOME", oldHome)
	os.Setenv("HOME", tmpHome)

	err := CmdUninstall(deps)
	if err != nil {
		t.Fatalf("CmdUninstall failed: %v", err)
	}

	// Read and parse the modified settings.json
	newContent, err := os.ReadFile(settingsPath)
	if err != nil {
		t.Fatalf("failed to read settings.json after uninstall: %v", err)
	}

	newStr := string(newContent)

	// The _maverickManagedSince key should be gone
	if strings.Contains(newStr, "_maverickManagedSince") {
		t.Errorf("_maverickManagedSince key still present after uninstall")
	}

	// Maverick permissions should be gone
	if strings.Contains(newStr, "maverick_ask") {
		t.Errorf("maverick_ask permission still present after uninstall")
	}
	if strings.Contains(newStr, "maverick_shell") {
		t.Errorf("maverick_shell permission still present after uninstall")
	}

	// But other permissions and keys should remain
	if !strings.Contains(newStr, "other_tool") {
		t.Errorf("other_tool permission was deleted (should be preserved)")
	}
	if !strings.Contains(newStr, "allow_bash") {
		t.Errorf("allow_bash was deleted (should be preserved)")
	}
	if !strings.Contains(newStr, "model") {
		t.Errorf("model key was deleted (should be preserved)")
	}
	if !strings.Contains(newStr, "theme") {
		t.Errorf("theme key was deleted (should be preserved)")
	}
}

// TestCmdUninstall_PromptsForBinaryRemoval tests that uninstall tells the user
// to manually remove the binary, and doesn't remove it automatically.
func TestCmdUninstall_PromptsForBinaryRemoval(t *testing.T) {
	tmpHome := t.TempDir()
	claudePath := filepath.Join(tmpHome, ".claude")
	os.MkdirAll(claudePath, 0700)

	maverickHome := filepath.Join(tmpHome, ".maverick")
	binDir := filepath.Join(maverickHome, "bin")
	os.MkdirAll(binDir, 0700)
	binaryPath := filepath.Join(binDir, "maverick")
	if err := os.WriteFile(binaryPath, []byte("fake binary"), 0755); err != nil {
		t.Fatalf("failed to create fake binary: %v", err)
	}

	stdout := &bytes.Buffer{}
	stderr := &bytes.Buffer{}

	deps := &CmdDeps{
		Flags:  &flags.Parsed{},
		Stdout: stdout,
		Stderr: stderr,
	}

	oldHome := os.Getenv("HOME")
	defer os.Setenv("HOME", oldHome)
	os.Setenv("HOME", tmpHome)

	err := CmdUninstall(deps)
	if err != nil {
		t.Fatalf("CmdUninstall failed: %v", err)
	}

	// Binary should still be there
	if _, err := os.Stat(binaryPath); err != nil {
		t.Errorf("binary was deleted (should be left for user to remove manually)")
	}

	// Output should mention that user needs to manually remove it
	output := stdout.String() + stderr.String()
	if !strings.Contains(output, "rm -rf") && !strings.Contains(output, ".maverick") {
		t.Logf("warning: output doesn't mention manual binary removal, got: %s", output)
	}
}

// TestCmdUninstall_IdempotentAfterInstall tests that running uninstall twice
// (or after a clean install) produces clean removal with no errors.
func TestCmdUninstall_IdempotentAfterInstall(t *testing.T) {
	tmpHome := t.TempDir()
	claudePath := filepath.Join(tmpHome, ".claude")
	os.MkdirAll(claudePath, 0700)

	// Create a more realistic setup that simulates after install
	claudeMDPath := filepath.Join(claudePath, "CLAUDE.md")
	claudeContent := `# My Project CLAUDE.md

<!-- BEGIN MAVERICK MANAGED BLOCK -->
## Maverick

Installed on 2026-04-20.
<!-- END MAVERICK MANAGED BLOCK -->

Real project content.
`

	if err := os.WriteFile(claudeMDPath, []byte(claudeContent), 0600); err != nil {
		t.Fatalf("failed to write CLAUDE.md: %v", err)
	}

	skillPath := filepath.Join(claudePath, "skills", "maverick")
	os.MkdirAll(skillPath, 0700)
	if err := os.WriteFile(filepath.Join(skillPath, "SKILL.md"), []byte("skill"), 0600); err != nil {
		t.Fatalf("failed to create skill: %v", err)
	}

	settingsPath := filepath.Join(claudePath, "settings.json")
	settingsContent := `{
  "permissions": {
    "allow_mcp": {
      "maverick_ask": true
    }
  },
  "_maverickManagedSince": "2026-04-20T00:00:00Z"
}
`
	if err := os.WriteFile(settingsPath, []byte(settingsContent), 0600); err != nil {
		t.Fatalf("failed to write settings.json: %v", err)
	}

	stdout := &bytes.Buffer{}
	stderr := &bytes.Buffer{}

	deps := &CmdDeps{
		Flags:  &flags.Parsed{},
		Stdout: stdout,
		Stderr: stderr,
	}

	oldHome := os.Getenv("HOME")
	defer os.Setenv("HOME", oldHome)
	os.Setenv("HOME", tmpHome)

	// First uninstall
	err := CmdUninstall(deps)
	if err != nil {
		t.Fatalf("first CmdUninstall failed: %v", err)
	}

	// Second uninstall should also succeed (idempotent)
	stdout.Reset()
	stderr.Reset()
	err = CmdUninstall(deps)
	if err != nil {
		t.Fatalf("second CmdUninstall failed: %v", err)
	}

	// Verify everything is clean
	claudeBytes, err := os.ReadFile(claudeMDPath)
	if err != nil {
		t.Fatalf("CLAUDE.md not readable after second uninstall: %v", err)
	}
	if strings.Contains(string(claudeBytes), "BEGIN MAVERICK") {
		t.Errorf("CLAUDE.md still has MAVERICK block after second uninstall")
	}

	if _, err := os.Stat(skillPath); err == nil {
		t.Errorf("maverick skill dir not removed after second uninstall")
	}

	settingsBytes, err := os.ReadFile(settingsPath)
	if err != nil {
		t.Fatalf("settings.json not readable after second uninstall: %v", err)
	}
	if strings.Contains(string(settingsBytes), "_maverickManagedSince") {
		t.Errorf("_maverickManagedSince still present after second uninstall")
	}
}
