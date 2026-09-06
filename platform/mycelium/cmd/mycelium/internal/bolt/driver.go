package bolt

import (
	"context"
	"fmt"
	"time"

	"github.com/neo4j/neo4j-go-driver/v5/neo4j"
)

// BoltDriver wraps the neo4j-go-driver v5 and implements the commands.Driver interface.
// It provides a thin adapter for executing Cypher queries against Neo4j.
type BoltDriver struct {
	driver neo4j.DriverWithContext
}

// NewBoltDriver creates a new BoltDriver connected to the specified Neo4j instance.
// uri: bolt connection string (e.g., "bolt://localhost:7687")
// user: Neo4j username
// pass: Neo4j password
func NewBoltDriver(uri, user, pass string) (*BoltDriver, error) {
	// Create the neo4j driver.
	driver, err := neo4j.NewDriverWithContext(uri, neo4j.BasicAuth(user, pass, ""))
	if err != nil {
		return nil, fmt.Errorf("failed to create neo4j driver: %w", err)
	}

	return &BoltDriver{driver: driver}, nil
}

func (b *BoltDriver) Run(cypher string) ([]map[string]any, error) {
	ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
	defer cancel()

	session := b.driver.NewSession(ctx, neo4j.SessionConfig{AccessMode: neo4j.AccessModeRead})
	defer session.Close(ctx)

	result, err := neo4j.ExecuteRead(ctx, session, func(tx neo4j.ManagedTransaction) (any, error) {
		res, err := tx.Run(ctx, cypher, nil)
		if err != nil {
			return nil, err
		}
		rows := []map[string]any{}
		for res.Next(ctx) {
			rec := res.Record()
			row := make(map[string]any, len(rec.Keys))
			for _, k := range rec.Keys {
				v, _ := rec.Get(k)
				row[k] = v
			}
			rows = append(rows, row)
		}
		if err := res.Err(); err != nil {
			return nil, err
		}
		return rows, nil
	})
	if err != nil {
		return nil, fmt.Errorf("run cypher: %w", err)
	}
	return result.([]map[string]any), nil
}

// Ping tests the connection to Neo4j by executing "RETURN 1".
// It times out after 3 seconds.
func (b *BoltDriver) Ping() error {
	ctx, cancel := context.WithTimeout(context.Background(), 3*time.Second)
	defer cancel()

	// Execute a simple query to verify connectivity.
	session := b.driver.NewSession(ctx, neo4j.SessionConfig{AccessMode: neo4j.AccessModeRead})
	defer session.Close(ctx)

	_, err := session.Run(ctx, "RETURN 1", nil)
	if err != nil {
		return fmt.Errorf("ping failed: %w", err)
	}

	return nil
}

// Close closes the Neo4j driver connection.
func (b *BoltDriver) Close() error {
	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()

	if err := b.driver.Close(ctx); err != nil {
		return fmt.Errorf("close driver: %w", err)
	}

	return nil
}
