-- Enabled Pragmas for Performance and Reliability
PRAGMA journal_mode = WAL;
PRAGMA synchronous = NORMAL;
PRAGMA foreign_keys = ON;

-- ==================================================================================
-- 1. NODES (The Entities)
-- Stores the objects of the graph.
-- Uses JSONB (if available) or JSON blob for flexible properties.
-- ==================================================================================
CREATE TABLE IF NOT EXISTS nodes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    
    -- "Concept", "Person", "Observation", "Document"
    type TEXT NOT NULL,
    
    -- The flexible payload (e.g., {"name": "Glucose", "unit": "mg/dL"})
    body TEXT NOT NULL CHECK(json_valid(body)), 
    
    -- Generated Columns for Indexing (Optimization)
    -- Allows O(log N) lookup without parsing the whole JSON
    name TEXT GENERATED ALWAYS AS (json_extract(body, '$.name')) VIRTUAL,
    code TEXT GENERATED ALWAYS AS (json_extract(body, '$.code')) VIRTUAL,
    
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_nodes_type_name ON nodes(type, name);
CREATE INDEX IF NOT EXISTS idx_nodes_code ON nodes(code);

-- ==================================================================================
-- 2. EDGES (The Relationships)
-- Modeled as a pure adjacency list using WITHOUT ROWID for clustering.
-- This ensures that finding all edges for a node is a sequential read.
-- ==================================================================================
CREATE TABLE IF NOT EXISTS edges (
    source_id INTEGER NOT NULL,
    target_id INTEGER NOT NULL,
    
    -- "CAUSES", "INDICATES", "OCCURRED_DURING", "EXTRACTED_FROM"
    rel_type TEXT NOT NULL,
    
    -- Confidence score (0.0 - 1.0)
    weight REAL DEFAULT 1.0,
    
    -- JSON payload for edge attributes (e.g., {"provenance": "Gemini 1.5"})
    properties TEXT,
    
    PRIMARY KEY (source_id, target_id, rel_type),
    
    FOREIGN KEY (source_id) REFERENCES nodes(id) ON DELETE CASCADE,
    FOREIGN KEY (target_id) REFERENCES nodes(id) ON DELETE CASCADE
) WITHOUT ROWID;

-- Reverse index for upstream traversals (Target -> Source)
CREATE INDEX IF NOT EXISTS idx_edges_reverse ON edges(target_id, source_id, rel_type);

-- ==================================================================================
-- 3. OBSERVATIONS (The Conflicting Truths)
-- This implements the "Observation Model" requested by the user.
-- It separates "Who said it" from "What is true".
-- ==================================================================================
CREATE TABLE IF NOT EXISTS observations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    
    -- What file did this come from?
    source_document_id INTEGER, 
    
    -- What concept are we talking about? (e.g., Cancer Node ID)
    concept_node_id INTEGER NOT NULL,
    
    -- The raw value extracted (e.g., "120", "Positive", "Present")
    value_text TEXT,
    value_numeric REAL,
    
    -- When was this OBSERVED (Valid Time)?
    observation_date DATETIME,
    
    -- Meta
    confidence REAL DEFAULT 1.0,
    status TEXT DEFAULT 'FINAL', -- 'PRELIMINARY', 'FINAL', 'AMENDED'
    
    FOREIGN KEY (source_document_id) REFERENCES nodes(id),
    FOREIGN KEY (concept_node_id) REFERENCES nodes(id)
);

CREATE INDEX IF NOT EXISTS idx_observations_date ON observations(observation_date);
CREATE INDEX IF NOT EXISTS idx_observations_concept ON observations(concept_node_id);

-- ==================================================================================
-- 4. CONCEPTS (Local Terminology Server)
-- Used for fast lookup of LOINC/SNOMED codes without API calls.
-- ==================================================================================
CREATE TABLE IF NOT EXISTS concepts (
    code TEXT PRIMARY KEY, -- "LOINC:2339-0"
    display_name TEXT NOT NULL,
    system TEXT NOT NULL, -- "LOINC", "SNOMED"
    
    -- Full JSON for synonyms, hierarchy, etc.
    definition TEXT 
);

-- Full Text Search for fuzzy matching ("Sugar" -> "Glucose")
-- We use a separated FTS table that triggers on the concepts table (managed in app logic usually, or triggers)
CREATE VIRTUAL TABLE IF NOT EXISTS concepts_fts USING fts5(
    code,
    display_name,
    synonyms
);
