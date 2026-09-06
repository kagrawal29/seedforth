package embedded

import (
	"fmt"
	"os"
)

// EmbeddedCreds holds database connection settings for different environments.
// Values are loaded from the process environment at runtime. Secrets are never
// embedded in the CLI binary or committed to the repository.
type EmbeddedCreds struct {
	Dev struct {
		BoltURI  string `toml:"bolt_uri"`
		User     string `toml:"user"`
		Password string `toml:"password"`
	} `toml:"dev"`
	Staging struct {
		BoltURI  string `toml:"bolt_uri"`
		User     string `toml:"user"`
		Password string `toml:"password"`
	} `toml:"staging"`
	Prod struct {
		BoltURI  string `toml:"bolt_uri"`
		User     string `toml:"user"`
		Password string `toml:"password"`
	} `toml:"prod"`
}

// Load reads runtime credentials from MYCELIUM_{TARGET}_{FIELD} variables.
// For example: MYCELIUM_DEV_BOLT_URI, MYCELIUM_DEV_USER, and
// MYCELIUM_DEV_PASSWORD. The deployment environment is responsible for
// injecting these values through its secret manager.
func Load() (*EmbeddedCreds, error) {
	creds := &EmbeddedCreds{}
	creds.Dev.BoltURI = os.Getenv("MYCELIUM_DEV_BOLT_URI")
	creds.Dev.User = os.Getenv("MYCELIUM_DEV_USER")
	creds.Dev.Password = os.Getenv("MYCELIUM_DEV_PASSWORD")
	creds.Staging.BoltURI = os.Getenv("MYCELIUM_STAGING_BOLT_URI")
	creds.Staging.User = os.Getenv("MYCELIUM_STAGING_USER")
	creds.Staging.Password = os.Getenv("MYCELIUM_STAGING_PASSWORD")
	creds.Prod.BoltURI = os.Getenv("MYCELIUM_PROD_BOLT_URI")
	creds.Prod.User = os.Getenv("MYCELIUM_PROD_USER")
	creds.Prod.Password = os.Getenv("MYCELIUM_PROD_PASSWORD")

	if creds.Dev.BoltURI == "" && creds.Staging.BoltURI == "" && creds.Prod.BoltURI == "" {
		return nil, fmt.Errorf("runtime graph credentials are missing; configure MYCELIUM_<TARGET>_BOLT_URI/USER/PASSWORD")
	}
	return creds, nil
}

// VersionStamp is the version embedded at compile time via -ldflags.
// Overridden by wi-ob-21.
var VersionStamp = "dev"

// BuildTime is the build timestamp embedded at compile time via -ldflags.
// Overridden by wi-ob-21.
var BuildTime = "unknown"
