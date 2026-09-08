ALTER TABLE lexemes ADD COLUMN frequency_zipf REAL DEFAULT NULL;
ALTER TABLE lexemes ADD COLUMN corpus_source TEXT DEFAULT NULL;

CREATE TABLE IF NOT EXISTS semantic_frames (
    frame_id TEXT PRIMARY KEY,
    frame_name TEXT NOT NULL,
    description TEXT
);

CREATE TABLE IF NOT EXISTS verb_classes (
    class_id TEXT PRIMARY KEY,
    class_name TEXT NOT NULL,
    parent_class_id TEXT
);

CREATE INDEX IF NOT EXISTS idx_edges_evokes ON edges(source_id, target_id) WHERE relation_type = 'EVOKES';
CREATE INDEX IF NOT EXISTS idx_edges_member_of_class ON edges(source_id, target_id) WHERE relation_type = 'MEMBER_OF_CLASS';
