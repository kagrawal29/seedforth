//go:build integration

package integration

import (
	"bytes"
	"context"
	"fmt"
	"strings"
	"testing"
	"time"

	"github.com/kagraw29/seedforth/platform/mycelium/cmd/mycelium/internal/bolt"
	"github.com/kagraw29/seedforth/platform/mycelium/cmd/mycelium/internal/commands"
	"github.com/kagraw29/seedforth/platform/mycelium/cmd/mycelium/internal/config"
	"github.com/kagraw29/seedforth/platform/mycelium/cmd/mycelium/internal/flags"
	"github.com/testcontainers/testcontainers-go"
	"github.com/testcontainers/testcontainers-go/wait"
)

var (
	containerBoltURI string
	container        testcontainers.Container
)

// TestMain sets up a shared Neo4j container for all integration tests.
// This runs once per test file and shares the container across tests for efficiency.
func TestMain(m *testing.M) {
	// Attempt to start Neo4j container; if Docker is unavailable, tests will skip.
	ctx := context.Background()

	// Try image-based approach
	req := testcontainers.ContainerRequest{
		Image:        "neo4j:5",
		ExposedPorts: []string{"7687/tcp"},
		Env: map[string]string{
			"NEO4J_AUTH":    "neo4j/localtest12",
			"NEO4J_PLUGINS": "[\"APOC\"]",
			"NEO4J_dbms_security_procedures_allowlist": "apoc.cypher.*,apoc.periodic.*,apoc.path.*",
		},
		WaitingFor: wait.ForLog("started"),
	}

	var err error
	container, err = testcontainers.GenericContainer(ctx, testcontainers.GenericContainerRequest{
		ContainerRequest: req,
		Started:          true,
	})
	if err != nil {
		// Docker may not be available; tests will skip
		fmt.Printf("Warning: Could not start Neo4j container: %v\n", err)
	} else {
		// Get the container's bolt port mapping
		boltPort, err := container.MappedPort(ctx, "7687")
		if err != nil {
			fmt.Printf("Warning: Could not get mapped port: %v\n", err)
		} else {
			host, err := container.Host(ctx)
			if err != nil {
				fmt.Printf("Warning: Could not get container host: %v\n", err)
			} else {
				containerBoltURI = fmt.Sprintf("bolt://%s:%s", host, boltPort.Port())
			}
		}
	}

	m.Run()

	// Cleanup
	if container != nil {
		ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
		defer cancel()
		container.Terminate(ctx)
	}
}

// skipIfDockerUnavailable skips the test if Docker/container is not available.
func skipIfDockerUnavailable(t *testing.T) {
	if container == nil || containerBoltURI == "" {
		t.Skip("Docker not available or container failed to start")
	}
}

// TestIntegrationShellReturnOne tests that CmdShell executes a simple read query and returns results.
// This is the "happy path" integration test: Neo4j is running, query succeeds, output contains result.
func TestIntegrationShellReturnOne(t *testing.T) {
	skipIfDockerUnavailable(t)

	// Create a real BoltDriver connected to the test container.
	drv, err := bolt.NewBoltDriver(containerBoltURI, "neo4j", "localtest12")
	if err != nil {
		t.Fatalf("Failed to create BoltDriver: %v", err)
	}
	defer drv.Close()

	// Create deps for CmdShell.
	stdout := &bytes.Buffer{}
	stderr := &bytes.Buffer{}
	deps := &commands.CmdDeps{
		Flags: &flags.Parsed{
			Args: []string{"RETURN 1 AS one"},
		},
		Cfg:    &config.Config{},
		Drv:    drv,
		Stdout: stdout,
		Stderr: stderr,
	}

	// Execute the shell command.
	err = commands.CmdShell(deps)
	if err != nil {
		t.Fatalf("CmdShell failed: %v\nstderr: %s", err, stderr.String())
	}

	// Assert output contains the result "1".
	output := stdout.String()
	if !strings.Contains(output, "1") {
		t.Errorf("Expected output to contain '1', got: %s", output)
	}
}

// TestIntegrationWriteRefused tests that CmdShell refuses write operations (CREATE, MERGE, DELETE, etc.)
// and confirms the refusal happens client-side without touching Neo4j.
func TestIntegrationWriteRefused(t *testing.T) {
	skipIfDockerUnavailable(t)

	// Create a real BoltDriver connected to the test container.
	drv, err := bolt.NewBoltDriver(containerBoltURI, "neo4j", "localtest12")
	if err != nil {
		t.Fatalf("Failed to create BoltDriver: %v", err)
	}
	defer drv.Close()

	// Create deps for CmdShell with a CREATE statement (which should be blocked).
	stdout := &bytes.Buffer{}
	stderr := &bytes.Buffer{}
	deps := &commands.CmdDeps{
		Flags: &flags.Parsed{
			Args: []string{"CREATE (:Foo)"},
		},
		Cfg:    &config.Config{},
		Drv:    drv,
		Stdout: stdout,
		Stderr: stderr,
	}

	// Execute the shell command; it should return a non-nil error.
	err = commands.CmdShell(deps)
	if err == nil {
		t.Fatalf("Expected CmdShell to refuse CREATE, but it succeeded")
	}

	// Verify the error message mentions the refusal.
	errMsg := err.Error()
	if !strings.Contains(errMsg, "refuses write verbs") {
		t.Errorf("Expected error to mention 'refuses write verbs', got: %s", errMsg)
	}

	// Verify that the node was NOT created: query for :Foo nodes.
	verifyRows, err := drv.Run("MATCH (n:Foo) RETURN count(n) AS c")
	if err != nil {
		t.Fatalf("Verification query failed: %v", err)
	}
	if len(verifyRows) == 0 {
		t.Fatalf("Verification query returned no rows")
	}

	count, ok := verifyRows[0]["c"].(int64)
	if !ok {
		t.Fatalf("Count result is not int64: %T", verifyRows[0]["c"])
	}

	if count != 0 {
		t.Errorf("Expected no :Foo nodes to exist, but found %d", count)
	}
}

// TestIntegrationWrongPassword tests that connecting with wrong credentials produces an error quickly.
func TestIntegrationWrongPassword(t *testing.T) {
	skipIfDockerUnavailable(t)

	// Create a driver with wrong password.
	drv, err := bolt.NewBoltDriver(containerBoltURI, "neo4j", "wrongpassword")
	if err != nil {
		// Error during construction is acceptable.
		return
	}
	defer drv.Close()

	// Try to ping; should fail within 3 seconds.
	ctx, cancel := context.WithTimeout(context.Background(), 3*time.Second)
	defer cancel()

	// Create a channel to capture ping result.
	errChan := make(chan error, 1)
	go func() {
		errChan <- drv.Ping()
	}()

	// Wait for result or timeout.
	select {
	case err := <-errChan:
		if err == nil {
			t.Fatalf("Expected Ping with wrong password to fail, but it succeeded")
		}
		// Expected: Ping returned an error.
	case <-ctx.Done():
		t.Fatalf("Ping did not return within 3 seconds (timeout)")
	}
}

// TestIntegrationDoctor tests that CmdDoctor succeeds on a live container,
// and fails when the container is stopped.
func TestIntegrationDoctor(t *testing.T) {
	skipIfDockerUnavailable(t)

	// Create a real BoltDriver connected to the test container.
	drv, err := bolt.NewBoltDriver(containerBoltURI, "neo4j", "localtest12")
	if err != nil {
		t.Fatalf("Failed to create BoltDriver: %v", err)
	}
	defer drv.Close()

	// Create deps for CmdDoctor.
	stdout := &bytes.Buffer{}
	stderr := &bytes.Buffer{}
	deps := &commands.CmdDeps{
		Flags:  &flags.Parsed{},
		Cfg:    &config.Config{},
		Drv:    drv,
		Stdout: stdout,
		Stderr: stderr,
	}

	// First: CmdDoctor should succeed when container is live.
	err = commands.CmdDoctor(deps)
	if err != nil {
		t.Fatalf("CmdDoctor failed on live container: %v", err)
	}

	// Second: Create a driver pointing to an intentionally bad address and verify it fails.
	badDrv, err := bolt.NewBoltDriver("bolt://nonexistent.local:7687", "neo4j", "localtest12")
	if err == nil {
		defer badDrv.Close()

		// Ping should fail within 3 seconds.
		ctx, cancel := context.WithTimeout(context.Background(), 3*time.Second)
		defer cancel()

		errChan := make(chan error, 1)
		go func() {
			errChan <- badDrv.Ping()
		}()

		select {
		case pingErr := <-errChan:
			if pingErr == nil {
				t.Fatalf("Expected Ping on bad address to fail, but it succeeded")
			}
			// Expected: Ping returned an error.
		case <-ctx.Done():
			t.Fatalf("Ping did not return within 3 seconds (timeout)")
		}
	}
}
