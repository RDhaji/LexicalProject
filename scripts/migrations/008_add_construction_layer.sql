CREATE TABLE IF NOT EXISTS constructions (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    created_at INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_edges_realizes ON edges(relation_type) WHERE relation_type = 'REALIZES';
