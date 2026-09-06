// @node_id: protocol-apoc-ingest
// @label: "apoc-ingest"
// Protocol: apoc-ingest
// Purpose: Ingest the full APOC + Neo4j function/procedure library as first-class graph nodes
// so the graph is AWARE of its own toolbox. Procedures and functions become discoverable
// via vector search and natural language queries.
//
// Idempotent: All operations use MERGE
// Constraints: Only ingest procedures/functions that exist on the live instance
// File type markers: 'apoc-procedure', 'apoc-function'
//
// Output: APOCProcedure nodes, APOCFunction nodes, APOCCategory nodes, wired to Ontology
// and cross-referenced with CypherAtom nodes that use them.

// ========== STEP 1: INGEST APOC PROCEDURES ==========
// Extract procedures from the live catalog and create APOCProcedure nodes.
// Each procedure gets: name, description, signature, mode, category, node_id.

CALL {
  SHOW PROCEDURES YIELD name, description, signature, mode
  WHERE name STARTS WITH 'apoc' OR name STARTS WITH 'db.index.vector'
  WITH name, description, signature, mode,
       split(name, '.')[1] AS category
  MERGE (proc:APOCProcedure:HasEmbedding {
    node_id: 'apoc-proc-' + replace(name, '.', '-')
  })
  SET proc.name = name,
      proc.description = description,
      proc.signature = signature,
      proc.mode = mode,
      proc.category = category,
      proc.file_type = 'apoc-procedure',
      proc.created_at = datetime.transaction(),
      proc.embedding_dirty = true
} IN TRANSACTIONS OF 50 ROWS;

// ========== STEP 2: INGEST APOC FUNCTIONS ==========
// Extract functions from the live catalog and create APOCFunction nodes.
// Each function gets: name, description, signature, is_builtin, category, node_id.

CALL {
  SHOW FUNCTIONS YIELD name, description, signature, isBuiltIn
  WHERE name STARTS WITH 'apoc' OR name STARTS WITH 'vector'
  WITH name, description, signature, isBuiltIn,
       split(name, '.')[1] AS category
  MERGE (func:APOCFunction:HasEmbedding {
    node_id: 'apoc-fn-' + replace(name, '.', '-')
  })
  SET func.name = name,
      func.description = description,
      func.signature = signature,
      func.is_builtin = isBuiltIn,
      func.category = category,
      func.file_type = 'apoc-function',
      func.created_at = datetime.transaction(),
      func.embedding_dirty = true
} IN TRANSACTIONS OF 50 ROWS;

// ========== STEP 3: INGEST APOC CATEGORIES ==========
// Create :APOCCategory nodes for each unique category (coll, map, text, convert, etc.)
// Wire each procedure/function to its category via [:BELONGS_TO]

WITH ['algo', 'agg', 'atomic', 'coll', 'config', 'convert', 'create',
      'cypher', 'date', 'debug', 'export', 'generate', 'graph', 'hashing',
      'index', 'import', 'json', 'load', 'lock', 'log', 'map', 'math',
      'meta', 'misc', 'number', 'periodic', 'refactor', 'rel', 'schema',
      'spatial', 'stats', 'text', 'trigger', 'util', 'version', 'vector',
      'db'] AS categories
UNWIND categories AS cat
MERGE (category:APOCCategory {
  node_id: 'apoc-cat-' + cat
})
SET category.name = cat,
    category.created_at = datetime.transaction();

// Wire procedures to categories
MATCH (proc:APOCProcedure)
MATCH (cat:APOCCategory {name: proc.category})
MERGE (proc)-[:BELONGS_TO]->(cat);

// Wire functions to categories
MATCH (func:APOCFunction)
MATCH (cat:APOCCategory {name: func.category})
MERGE (func)-[:BELONGS_TO]->(cat);

// ========== STEP 4: WIRE TO ONTOLOGY ==========
// Create CAPABILITY_OF edges from APOC procedures/functions to the :Ontology node.
// This asserts that these procedures/functions are capabilities the graph possesses.

MATCH (ontology:Ontology)
WITH ontology
CALL {
  MATCH (proc:APOCProcedure)
  MERGE (proc)-[:CAPABILITY_OF]->(ontology)
} IN TRANSACTIONS OF 50 ROWS;

MATCH (ontology:Ontology)
WITH ontology
CALL {
  MATCH (func:APOCFunction)
  MERGE (func)-[:CAPABILITY_OF]->(ontology)
} IN TRANSACTIONS OF 50 ROWS;

// ========== STEP 5: CROSS-REFERENCE WITH CYPHER ATOMS ==========
// For each CypherAtom, check if its cypher text contains calls to APOC procedures/functions.
// Create USED_BY edges from procedures/functions to the atoms that reference them.

CALL {
  MATCH (proc:APOCProcedure)
  MATCH (atom:CypherAtom)
  WHERE atom.cypher CONTAINS proc.name
  MERGE (proc)-[:USED_BY]->(atom)
} IN TRANSACTIONS OF 50 ROWS;

CALL {
  MATCH (func:APOCFunction)
  MATCH (atom:CypherAtom)
  WHERE atom.cypher CONTAINS func.name
  MERGE (func)-[:USED_BY]->(atom)
} IN TRANSACTIONS OF 50 ROWS;

// ========== SUMMARY ==========
// Emit counts for verification
MATCH (proc:APOCProcedure) WITH count(proc) AS procCount
MATCH (func:APOCFunction) WITH procCount, count(func) AS funcCount
MATCH (cat:APOCCategory) WITH procCount, funcCount, count(cat) AS catCount
MATCH (:APOCProcedure)-[r:USED_BY]->(:CypherAtom) WITH procCount, funcCount, catCount, count(r) AS procUsage
MATCH (:APOCFunction)-[r:USED_BY]->(:CypherAtom) WITH procCount, funcCount, catCount, procUsage, count(r) AS funcUsage
MATCH (:APOCProcedure)-[r:CAPABILITY_OF]->(:Ontology) WITH procCount, funcCount, catCount, procUsage, funcUsage, count(r) AS procCapability
MATCH (:APOCFunction)-[r:CAPABILITY_OF]->(:Ontology) WITH procCount, funcCount, catCount, procUsage, funcUsage, procCapability, count(r) AS funcCapability
RETURN {
  apoc_procedures: procCount,
  apoc_functions: funcCount,
  apoc_categories: catCount,
  procedure_used_by_edges: procUsage,
  function_used_by_edges: funcUsage,
  procedure_capability_edges: procCapability,
  function_capability_edges: funcCapability,
  total_usage_edges: procUsage + funcUsage,
  total_capability_edges: procCapability + funcCapability
} AS summary;
