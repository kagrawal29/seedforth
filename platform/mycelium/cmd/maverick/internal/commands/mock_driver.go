package commands

import "fmt"

// MockDriver is a test double for the Driver interface.
type MockDriver struct {
	Responses    map[string][]map[string]any
	Errors       map[string]error
	Pinged       bool
	Closed       bool
	WriteRefused bool
	// Track which cypherqueries were run for assertion in tests
	RanQueries []string
}

// Run executes a Cypher query and returns its results or a mocked error.
func (m *MockDriver) Run(cypher string) ([]map[string]any, error) {
	m.RanQueries = append(m.RanQueries, cypher)

	// Check if there's a mocked error for this query
	if err, exists := m.Errors[cypher]; exists {
		return nil, err
	}

	// Return the mocked response
	if resp, exists := m.Responses[cypher]; exists {
		return resp, nil
	}

	// Default: return empty result set
	return []map[string]any{}, nil
}

// Ping tests the connection to Neo4j.
func (m *MockDriver) Ping() error {
	m.Pinged = true

	// Check if there's a mocked error for ping
	if err, exists := m.Errors["ping"]; exists {
		return err
	}

	return nil
}

// Close closes the connection.
func (m *MockDriver) Close() error {
	m.Closed = true
	return nil
}

// NewMockDriver creates a new MockDriver with empty maps.
func NewMockDriver() *MockDriver {
	return &MockDriver{
		Responses:    make(map[string][]map[string]any),
		Errors:       make(map[string]error),
		Pinged:       false,
		Closed:       false,
		WriteRefused: false,
		RanQueries:   []string{},
	}
}

// SetupResponse sets a successful response for a query.
func (m *MockDriver) SetupResponse(cypher string, result []map[string]any) {
	m.Responses[cypher] = result
}

// SetupError sets an error for a query.
func (m *MockDriver) SetupError(cypher string, err error) {
	m.Errors[cypher] = err
}

// AssertQueryRan checks if a specific query was run.
func (m *MockDriver) AssertQueryRan(cypher string) bool {
	for _, q := range m.RanQueries {
		if q == cypher {
			return true
		}
	}
	return false
}

// AssertQueryNotRan checks if a specific query was NOT run.
func (m *MockDriver) AssertQueryNotRan(cypher string) bool {
	return !m.AssertQueryRan(cypher)
}

// GetQueriesRun returns the list of all queries that were run.
func (m *MockDriver) GetQueriesRun() []string {
	return m.RanQueries
}

// LastQuery returns the most recent query that was run, or empty string if none.
func (m *MockDriver) LastQuery() string {
	if len(m.RanQueries) == 0 {
		return ""
	}
	return m.RanQueries[len(m.RanQueries)-1]
}

// QueryCount returns how many queries were run.
func (m *MockDriver) QueryCount() int {
	return len(m.RanQueries)
}

// AssertWriteQueryBlocked checks that a write-like query was not executed.
// This is used by tests to verify that CmdShell blocks certain verbs before calling driver.Run.
func (m *MockDriver) AssertWriteQueryBlocked(writeKeyword string) bool {
	for _, q := range m.RanQueries {
		if q == writeKeyword {
			return false // It was executed, not blocked
		}
	}
	return true // It was not executed (blocked)
}

// ResetTrackingState clears the list of ran queries but keeps responses/errors.
func (m *MockDriver) ResetTrackingState() {
	m.RanQueries = []string{}
	m.Pinged = false
	m.Closed = false
}

// String formats the mock driver state for debugging.
func (m *MockDriver) String() string {
	return fmt.Sprintf("MockDriver{Closed:%v, Pinged:%v, QueriesRun:%d}", m.Closed, m.Pinged, len(m.RanQueries))
}
