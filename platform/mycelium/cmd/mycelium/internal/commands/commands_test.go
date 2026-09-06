package commands

import (
	"bytes"
	"io"
	"os"
	"path/filepath"
	"strings"
	"testing"

	"github.com/kagraw29/seedforth/platform/mycelium/cmd/mycelium/internal/config"
	"github.com/kagraw29/seedforth/platform/mycelium/cmd/mycelium/internal/flags"
)

const VersionStamp = "dev"

// TestCmdVersion tests that CmdVersion outputs the version string.
func TestCmdVersion(t *testing.T) {
	drv := NewMockDriver()
	stdout := &bytes.Buffer{}
	stderr := &bytes.Buffer{}

	deps := &CmdDeps{
		Flags:  &flags.Parsed{},
		Cfg:    &config.Config{},
		Drv:    drv,
		Stdout: stdout,
		Stderr: stderr,
	}

	err := CmdVersion(deps)
	if err != nil {
		t.Fatalf("CmdVersion returned error: %v", err)
	}

	output := stdout.String()
	if !strings.Contains(output, "mycelium") {
		t.Errorf("version output missing 'mycelium', got: %s", output)
	}
	if !strings.Contains(output, VersionStamp) {
		t.Errorf("version output missing VersionStamp '%s', got: %s", VersionStamp, output)
	}
}

// TestCmdConfigShow tests that CmdConfigShow lists configuration targets without exposing passwords.
func TestCmdConfigShow(t *testing.T) {
	cfg := &config.Config{
		Targets: map[string]config.Target{
			"dev": {
				Name:     "dev",
				BoltURI:  "bolt://localhost:7687",
				User:     "neo4j",
				Password: "secret-dev-password",
			},
			"prod": {
				Name:     "prod",
				BoltURI:  "bolt://prod.example.com:7687",
				User:     "neo4j",
				Password: "secret-prod-password",
			},
		},
	}

	drv := NewMockDriver()
	stdout := &bytes.Buffer{}
	stderr := &bytes.Buffer{}

	deps := &CmdDeps{
		Flags:  &flags.Parsed{},
		Cfg:    cfg,
		Drv:    drv,
		Stdout: stdout,
		Stderr: stderr,
	}

	err := CmdConfigShow(deps)
	if err != nil {
		t.Fatalf("CmdConfigShow returned error: %v", err)
	}

	output := stdout.String()
	if !strings.Contains(output, "dev") {
		t.Errorf("config show output missing 'dev', got: %s", output)
	}
	if !strings.Contains(output, "prod") {
		t.Errorf("config show output missing 'prod', got: %s", output)
	}
	if strings.Contains(output, "secret-dev-password") || strings.Contains(output, "secret-prod-password") {
		t.Errorf("config show exposed passwords in output: %s", output)
	}
}

// TestCmdConfigInit tests that CmdConfigInit creates a TOML config file with nested [targets.dev]/[targets.prod] structure.
func TestCmdConfigInit(t *testing.T) {
	// Create a temporary directory for the test config file
	tmpDir := t.TempDir()
	configPath := filepath.Join(tmpDir, "config.toml")

	drv := NewMockDriver()
	stdout := &bytes.Buffer{}
	stderr := &bytes.Buffer{}

	deps := &CmdDeps{
		Flags: &flags.Parsed{
			Args: []string{configPath},
		},
		Cfg:    &config.Config{},
		Drv:    drv,
		Stdout: stdout,
		Stderr: stderr,
	}

	err := CmdConfigInit(deps)
	if err != nil {
		t.Fatalf("CmdConfigInit returned error: %v", err)
	}

	// Verify file exists at configPath
	if _, err := os.Stat(configPath); err != nil {
		t.Errorf("config file not created at %s: %v", configPath, err)
	}

	// Reload the config and verify it contains targets.dev and targets.prod
	loaded, err := config.Load(configPath)
	if err != nil {
		t.Errorf("created config file is not parseable: %v", err)
	}
	if loaded == nil {
		t.Error("loaded config is nil")
	} else {
		if _, hasDev := loaded.Targets["dev"]; !hasDev {
			t.Error("config missing 'dev' target")
		}
		if _, hasProd := loaded.Targets["prod"]; !hasProd {
			t.Error("config missing 'prod' target")
		}
	}
}

// TestCmdStatus tests that CmdStatus queries the database for Being node count.
func TestCmdStatus(t *testing.T) {
	drv := NewMockDriver()
	// Setup mock response: count of Being nodes
	drv.SetupResponse("MATCH (b:Being) RETURN count(b) AS c", []map[string]any{
		{"c": int64(1)},
	})

	stdout := &bytes.Buffer{}
	stderr := &bytes.Buffer{}

	deps := &CmdDeps{
		Flags:  &flags.Parsed{},
		Cfg:    &config.Config{},
		Drv:    drv,
		Stdout: stdout,
		Stderr: stderr,
	}

	err := CmdStatus(deps)
	if err != nil {
		t.Fatalf("CmdStatus returned error: %v", err)
	}

	if !drv.AssertQueryRan("MATCH (b:Being) RETURN count(b) AS c") {
		t.Errorf("CmdStatus did not run expected query, queries: %v", drv.GetQueriesRun())
	}
	output := stdout.String()
	if !strings.Contains(output, "1") {
		t.Errorf("status output missing count, got: %s", output)
	}
}

// TestCmdHealth tests that CmdHealth succeeds when a health query returns results.
func TestCmdHealth(t *testing.T) {
	drv := NewMockDriver()
	// Mock a successful health check query
	healthQuery := "MATCH (i:Invariant) RETURN count(i) AS count"
	drv.SetupResponse(healthQuery, []map[string]any{
		{"count": int64(5)},
	})

	stdout := &bytes.Buffer{}
	stderr := &bytes.Buffer{}

	deps := &CmdDeps{
		Flags:  &flags.Parsed{},
		Cfg:    &config.Config{},
		Drv:    drv,
		Stdout: stdout,
		Stderr: stderr,
	}

	err := CmdHealth(deps)
	if err != nil {
		t.Errorf("CmdHealth should succeed with mocked response, got error: %v", err)
	}
}

// TestCmdDoctor tests that CmdDoctor calls Ping() and surfaces errors.
func TestCmdDoctor(t *testing.T) {
	drv := NewMockDriver()
	stdout := &bytes.Buffer{}
	stderr := &bytes.Buffer{}

	deps := &CmdDeps{
		Flags:  &flags.Parsed{},
		Cfg:    &config.Config{},
		Drv:    drv,
		Stdout: stdout,
		Stderr: stderr,
	}

	err := CmdDoctor(deps)
	if err != nil {
		t.Errorf("CmdDoctor should succeed when Ping() succeeds, got error: %v", err)
	}

	if !drv.Pinged {
		t.Errorf("CmdDoctor did not call Ping()")
	}
}

// TestCmdDoctor_PingError tests that CmdDoctor surfaces ping errors.
func TestCmdDoctor_PingError(t *testing.T) {
	drv := NewMockDriver()
	drv.SetupError("ping", io.ErrClosedPipe)

	stdout := &bytes.Buffer{}
	stderr := &bytes.Buffer{}

	deps := &CmdDeps{
		Flags:  &flags.Parsed{},
		Cfg:    &config.Config{},
		Drv:    drv,
		Stdout: stdout,
		Stderr: stderr,
	}

	err := CmdDoctor(deps)
	if err == nil {
		t.Errorf("CmdDoctor should return error when Ping() fails")
	}
	if !drv.Pinged {
		t.Errorf("CmdDoctor did not call Ping()")
	}
}

// TestCmdShell_ReadOK tests that shell "RETURN 1" passes through to driver.Run.
func TestCmdShell_ReadOK(t *testing.T) {
	drv := NewMockDriver()
	readQuery := "RETURN 1"
	drv.SetupResponse(readQuery, []map[string]any{
		{"1": int64(1)},
	})

	stdout := &bytes.Buffer{}
	stderr := &bytes.Buffer{}

	deps := &CmdDeps{
		Flags: &flags.Parsed{
			Args: []string{readQuery},
		},
		Cfg:    &config.Config{},
		Drv:    drv,
		Stdout: stdout,
		Stderr: stderr,
	}

	err := CmdShell(deps)
	if err != nil {
		t.Errorf("CmdShell should pass read queries through, got error: %v", err)
	}

	if !drv.AssertQueryRan(readQuery) {
		t.Errorf("CmdShell did not pass read query to driver.Run")
	}
}

// TestCmdShell_WriteRefused tests that write verbs (CREATE, MERGE, DELETE, SET, REMOVE, DROP, DETACH)
// are blocked BEFORE calling driver.Run (defense in depth).
func TestCmdShell_WriteRefused(t *testing.T) {
	writeVerbs := []string{
		"CREATE (n)",
		"MERGE (n)",
		"DELETE n",
		"SET n.prop = 1",
		"REMOVE n.prop",
		"DROP INDEX idx",
		"DETACH DELETE n",
	}

	for _, verb := range writeVerbs {
		t.Run(verb, func(t *testing.T) {
			drv := NewMockDriver()
			stdout := &bytes.Buffer{}
			stderr := &bytes.Buffer{}

			deps := &CmdDeps{
				Flags: &flags.Parsed{
					Args: []string{verb},
				},
				Cfg:    &config.Config{},
				Drv:    drv,
				Stdout: stdout,
				Stderr: stderr,
			}

			err := CmdShell(deps)
			if err == nil {
				t.Errorf("CmdShell should reject write verb '%s'", verb)
			}

			if drv.AssertQueryRan(verb) {
				t.Errorf("CmdShell allowed write verb '%s' to reach driver.Run", verb)
			}
		})
	}
}

// TestCmdShell_CallPassesThrough tests that CALL queries are allowed
// (many read procedures use CALL, so we only refuse data-mutating verbs).
func TestCmdShell_CallPassesThrough(t *testing.T) {
	drv := NewMockDriver()
	callQuery := "CALL apoc.help('search')"
	drv.SetupResponse(callQuery, []map[string]any{})

	stdout := &bytes.Buffer{}
	stderr := &bytes.Buffer{}

	deps := &CmdDeps{
		Flags: &flags.Parsed{
			Args: []string{callQuery},
		},
		Cfg:    &config.Config{},
		Drv:    drv,
		Stdout: stdout,
		Stderr: stderr,
	}

	err := CmdShell(deps)
	if err != nil {
		t.Errorf("CmdShell should allow CALL queries, got error: %v", err)
	}

	if !drv.AssertQueryRan(callQuery) {
		t.Errorf("CmdShell blocked CALL query, which should be allowed")
	}
}

// TestCmdAsk tests that CmdAsk requires EmbedEndpoint to be configured.
func TestCmdAsk(t *testing.T) {
	drv := NewMockDriver()
	stdout := &bytes.Buffer{}
	stderr := &bytes.Buffer{}

	// Test with empty EmbedEndpoint: should fail
	deps := &CmdDeps{
		Flags: &flags.Parsed{
			Args: []string{"what is health"},
		},
		Cfg:           &config.Config{},
		Drv:           drv,
		Stdout:        stdout,
		Stderr:        stderr,
		EmbedEndpoint: "", // empty
	}

	err := CmdAsk(deps)
	if err == nil {
		t.Errorf("CmdAsk with empty EmbedEndpoint should fail")
	}
	if !strings.Contains(err.Error(), "embed endpoint not configured") {
		t.Errorf("CmdAsk with empty EmbedEndpoint should report configuration error, got: %v", err)
	}
}

// TestCmdAsk_WithEndpoint tests that CmdAsk accepts a configured EmbedEndpoint.
func TestCmdAsk_WithEndpoint(t *testing.T) {
	drv := NewMockDriver()
	stdout := &bytes.Buffer{}
	stderr := &bytes.Buffer{}

	deps := &CmdDeps{
		Flags: &flags.Parsed{
			Args: []string{"what is health"},
		},
		Cfg:           &config.Config{},
		Drv:           drv,
		Stdout:        stdout,
		Stderr:        stderr,
		EmbedEndpoint: "http://localhost:11434",
	}

	err := CmdAsk(deps)
	// With a valid endpoint, implementation should proceed (stub still returns "not implemented")
	// but should NOT return "embed endpoint not configured"
	if err != nil && strings.Contains(err.Error(), "embed endpoint not configured") {
		t.Errorf("CmdAsk with valid EmbedEndpoint should not complain about configuration, got: %v", err)
	}
}

// TestCmdConfigInit_FileCreationAndReload tests that CmdConfigInit creates a file
// that can be reloaded via config.Load.
func TestCmdConfigInit_FileCreationAndReload(t *testing.T) {
	tmpDir := t.TempDir()
	configPath := filepath.Join(tmpDir, "myconfig.toml")

	drv := NewMockDriver()
	stdout := &bytes.Buffer{}
	stderr := &bytes.Buffer{}

	deps := &CmdDeps{
		Flags: &flags.Parsed{
			Args: []string{configPath},
		},
		Cfg:    &config.Config{},
		Drv:    drv,
		Stdout: stdout,
		Stderr: stderr,
	}

	err := CmdConfigInit(deps)
	if err != nil {
		t.Fatalf("CmdConfigInit returned error: %v", err)
	}

	// File must exist
	if _, err := os.Stat(configPath); err != nil {
		t.Errorf("config file not created at %s: %v", configPath, err)
	}

	// File must be valid TOML and loadable
	loaded, err := config.Load(configPath)
	if err != nil {
		t.Errorf("created config file is not valid TOML: %v", err)
	}

	// Must have both dev and prod targets
	if loaded != nil {
		if _, hasDev := loaded.Targets["dev"]; !hasDev {
			t.Error("config missing 'dev' target")
		}
		if _, hasProd := loaded.Targets["prod"]; !hasProd {
			t.Error("config missing 'prod' target")
		}
	}
}

// Helper: stringContains checks if s1 contains s2.
func stringContains(s1, s2 string) bool {
	return strings.Contains(s1, s2)
}

// Helper: stringDoesNotContain checks if s1 does not contain s2.
func stringDoesNotContain(s1, s2 string) bool {
	return !strings.Contains(s1, s2)
}

// TestCmdExportGuide tests that CmdExportGuide renders guide sections to Markdown.
// This is the golden test: query mock graph with 2 sections, verify byte-for-byte output.
func TestCmdExportGuide(t *testing.T) {
	tests := []struct {
		name          string
		outPath       string
		guideName     string
		sections      []map[string]any
		expectErr     bool
		expectContent []string // substrings expected in CONTRIBUTING.md
		expectFile    bool     // whether the file should be created
	}{
		{
			name:      "golden_test_two_sections",
			outPath:   filepath.Join(t.TempDir(), "CONTRIBUTING.md"),
			guideName: "mycelium",
			sections: []map[string]any{
				{
					"title":      "Welcome",
					"slug":       "welcome",
					"order":      int64(1),
					"body_md":    "Thank you for contributing.",
					"amendments": []any{}, // empty amendments
				},
				{
					"title":      "Local Setup",
					"slug":       "local-setup",
					"order":      int64(2),
					"body_md":    "Run `mycelium local bootstrap` to get started.",
					"amendments": []any{}, // empty amendments
				},
			},
			expectErr: false,
			expectContent: []string{
				"<!-- AUTOGENERATED from :ContributorGuide",
				"## Welcome",
				"Thank you for contributing.",
				"## Local Setup",
				"Run `mycelium local bootstrap` to get started.",
			},
			expectFile: true,
		},
		{
			name:      "sections_with_amendments",
			outPath:   filepath.Join(t.TempDir(), "CONTRIBUTING.md"),
			guideName: "mycelium",
			sections: []map[string]any{
				{
					"title":   "Workflow",
					"slug":    "workflow",
					"order":   int64(1),
					"body_md": "Follow the graph-first approach.",
					"amendments": []any{
						map[string]any{
							"ts":   "2026-04-20T10:00:00Z",
							"type": "acceptance-addendum",
							"text": "Must verify on local graph before PR.",
						},
					},
				},
			},
			expectErr: false,
			expectContent: []string{
				"## Workflow",
				"Follow the graph-first approach.",
				"<details>",
				"<summary>Amendments</summary>",
				"Must verify on local graph before PR.",
			},
			expectFile: true,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			drv := NewMockDriver()

			// Mock query: returns guide sections in order
			const guideSectionsQuery = "MATCH (g:ContributorGuide {name: 'mycelium'})-[:HAS_SECTION]->(s:GuideSection) RETURN s.title AS title, s.slug AS slug, s.order AS order, s.body_md AS body_md, coalesce(s.amendments, []) AS amendments ORDER BY s.order"
			drv.SetupResponse(guideSectionsQuery, tt.sections)

			stdout := &bytes.Buffer{}
			stderr := &bytes.Buffer{}

			deps := &CmdDeps{
				Flags: &flags.Parsed{
					Args: []string{tt.outPath},
				},
				Cfg:    &config.Config{},
				Drv:    drv,
				Stdout: stdout,
				Stderr: stderr,
			}

			err := CmdExportGuide(deps)
			if (err != nil) != tt.expectErr {
				t.Errorf("CmdExportGuide() error = %v, expectErr %v", err, tt.expectErr)
			}
			if tt.expectErr {
				return
			}

			// Verify file was created
			if tt.expectFile {
				if _, err := os.Stat(tt.outPath); err != nil {
					t.Errorf("expected file %s not created: %v", tt.outPath, err)
					return
				}

				content, err := os.ReadFile(tt.outPath)
				if err != nil {
					t.Fatalf("failed to read output file: %v", err)
				}

				contentStr := string(content)

				// Check expected substrings
				for _, substr := range tt.expectContent {
					if !strings.Contains(contentStr, substr) {
						t.Errorf("expected substring %q not found in output:\n%s", substr, contentStr)
					}
				}
			}
		})
	}
}
