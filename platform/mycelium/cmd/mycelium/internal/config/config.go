package config

import (
	"fmt"
	"io"
	"os"
	"strings"

	"github.com/BurntSushi/toml"
)

// CheckDeprecatedEnv logs a deprecation warning if the legacy variable is set.
// Call this after Resolve to emit the warning to stderr.
func CheckDeprecatedEnv(stderr io.Writer) {
	if os.Getenv("MAVERICK_TARGET") != "" {
		fmt.Fprintf(stderr, "warning: MAVERICK_TARGET is deprecated, use MYCELIUM_TARGET instead\n")
	}
}

// Target represents a Neo4j connection target.
type Target struct {
	BoltURI  string
	User     string
	Password string
	Name     string
}

// Config holds the parsed configuration with all targets.
type Config struct {
	Targets map[string]Target
}

// rawConfig is the intermediate structure for parsing TOML.
type rawConfig struct {
	// Flat schema: [dev], [prod], etc.
	Flat map[string]map[string]interface{} `toml:"-"`
	// Nested schema: [targets.dev], [targets.prod], etc.
	Targets map[string]map[string]interface{} `toml:"targets"`
}

// Load reads and parses a TOML configuration file.
// Returns error if file does not exist or is malformed.
func Load(path string) (*Config, error) {
	// Read file
	data, err := os.ReadFile(path)
	if err != nil {
		if os.IsNotExist(err) {
			return nil, err
		}
		return nil, fmt.Errorf("failed to read config file: %w", err)
	}

	// Parse TOML
	var raw rawConfig
	if err := toml.Unmarshal(data, &raw); err != nil {
		return nil, fmt.Errorf("TOML parse error: %w", err)
	}

	// Also manually parse flat schema by unmarshaling into a generic map
	var flatData map[string]interface{}
	if err := toml.Unmarshal(data, &flatData); err != nil {
		return nil, fmt.Errorf("TOML parse error: %w", err)
	}

	// Extract flat targets (non-nested sections)
	raw.Flat = make(map[string]map[string]interface{})
	for k, v := range flatData {
		if k != "targets" { // Skip the nested section
			if m, ok := v.(map[string]interface{}); ok {
				raw.Flat[k] = m
			}
		}
	}

	// Build Config.Targets map
	// Nested schema wins if both present for same target
	targets := make(map[string]Target)

	// First, add flat schema targets
	for name, fields := range raw.Flat {
		t := Target{Name: name}
		if v, ok := fields["bolt_uri"].(string); ok {
			t.BoltURI = v
		}
		if v, ok := fields["user"].(string); ok {
			t.User = v
		}
		if v, ok := fields["password"].(string); ok {
			t.Password = v
		}
		targets[name] = t
	}

	// Then, overlay nested schema targets (these win)
	for name, fields := range raw.Targets {
		t := Target{Name: name}
		if v, ok := fields["bolt_uri"].(string); ok {
			t.BoltURI = v
		}
		if v, ok := fields["user"].(string); ok {
			t.User = v
		}
		if v, ok := fields["password"].(string); ok {
			t.Password = v
		}
		targets[name] = t
	}

	return &Config{Targets: targets}, nil
}

// Resolve returns the Target for a given name.
// If name is empty, uses MYCELIUM_TARGET environment variable.
// Falls back to the legacy MAVERICK_TARGET for backcompat.
// Returns error if target not found or required fields are missing.
func (c *Config) Resolve(targetName string) (*Target, error) {
	// If empty, consult environment variables
	if targetName == "" {
		// Prefer the canonical variable.
		if target := os.Getenv("MYCELIUM_TARGET"); target != "" {
			targetName = target
		} else if target := os.Getenv("MAVERICK_TARGET"); target != "" {
			// Backcompat: accept MAVERICK_TARGET; the caller may emit the warning.
			// Note: logging to stderr happens at the caller level (main.go)
			targetName = target
		}
	}

	// Look up target
	target, exists := c.Targets[targetName]
	if !exists {
		// Build list of valid targets for error message
		var validTargets []string
		for k := range c.Targets {
			validTargets = append(validTargets, k)
		}
		return nil, fmt.Errorf("unknown target %q (valid: %s)", targetName, strings.Join(validTargets, ", "))
	}

	// Validate required fields
	if target.BoltURI == "" {
		return nil, fmt.Errorf("target %q missing required field: bolt_uri", targetName)
	}

	return &target, nil
}
