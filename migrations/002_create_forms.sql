CREATE TABLE IF NOT EXISTS forms (
    id TEXT PRIMARY KEY,
    form TEXT NOT NULL,
    phonetic_transcription TEXT,
    morphological_features TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_forms_form ON forms(form);
