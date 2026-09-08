CREATE TABLE IF NOT EXISTS lexemes (
    id TEXT PRIMARY KEY,
    lemma TEXT NOT NULL UNIQUE,
    pos TEXT,
    created_at INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS forms (
    id TEXT PRIMARY KEY,
    form TEXT NOT NULL,
    created_at INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS edges (
    id TEXT PRIMARY KEY,
    source_id TEXT NOT NULL,
    source_type TEXT NOT NULL,
    relation_type TEXT NOT NULL,
    target_id TEXT NOT NULL,
    target_type TEXT NOT NULL,
    epistemic_class TEXT NOT NULL CHECK(epistemic_class IN ('EXPLICIT','GENERATED','ATTESTED','INFERRED','UNCERTAIN')),
    created_at INTEGER NOT NULL
);

INSERT OR IGNORE INTO lexemes (id, lemma, pos, created_at) VALUES
    ('lex_run', 'run', 'VERB', strftime('%s','now')),
    ('lex_fast', 'fast', 'ADJ', strftime('%s','now')),
    ('lex_happy', 'happy', 'ADJ', strftime('%s','now')),
    ('lex_go', 'go', 'VERB', strftime('%s','now')),
    ('lex_good', 'good', 'ADJ', strftime('%s','now')),
    ('lex_bad', 'bad', 'ADJ', strftime('%s','now')),
    ('lex_bank', 'bank', 'NOUN', strftime('%s','now'));
