CREATE TABLE IF NOT EXISTS pronunciations (
    id TEXT PRIMARY KEY,
    target_id TEXT NOT NULL,
    target_type TEXT NOT NULL CHECK(target_type IN ('LEXEME', 'FORM')),
    notation TEXT NOT NULL CHECK(notation IN ('IPA', 'ARPABET')),
    transcription TEXT NOT NULL,
    variety TEXT,
    epistemic_class TEXT NOT NULL CHECK(epistemic_class IN ('ATTESTED', 'EXPLICIT')),
    provenance_id TEXT
);
CREATE INDEX IF NOT EXISTS idx_pronunciations_target ON pronunciations(target_id, target_type);

CREATE TABLE IF NOT EXISTS search_phonetic_index (
    phonetic_key TEXT NOT NULL,
    target_id TEXT NOT NULL,
    target_type TEXT NOT NULL,
    algorithm TEXT NOT NULL,
    epistemic_class TEXT NOT NULL DEFAULT 'GENERATED'
);
CREATE INDEX IF NOT EXISTS idx_search_phonetic_key ON search_phonetic_index(phonetic_key, algorithm);
