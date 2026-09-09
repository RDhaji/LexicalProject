CREATE TABLE IF NOT EXISTS lexemes_es (
    id TEXT PRIMARY KEY,
    lemma TEXT NOT NULL UNIQUE,
    pos TEXT,
    created_at INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS forms_es (
    id TEXT PRIMARY KEY,
    form TEXT NOT NULL,
    created_at INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_lexemes_es_lemma ON lexemes_es(lemma);
CREATE INDEX IF NOT EXISTS idx_forms_es_form ON forms_es(form);
