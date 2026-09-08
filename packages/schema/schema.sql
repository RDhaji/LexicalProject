-- =====================================================================
-- Lexical Explorer Canonical SQLite Schema (lexical_graph.db)
-- Version: 1.0.0-PROD
-- Downstream From: PRD.md, ONTOLOGY.md, ARCHITECTURE.md, ADR-001..007
-- =====================================================================

PRAGMA foreign_keys = ON;
PRAGMA journal_mode = WAL;
PRAGMA synchronous = NORMAL;

-- ---------------------------------------------------------------------
-- 1. Metadata & Source Claims Ledger (ADR-002, PRD §18, §19)
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS sources (
    id TEXT PRIMARY KEY,                       -- e.g. "OEWN_2025", "WIKTIONARY_KAIKKI"
    name TEXT NOT NULL,
    version TEXT NOT NULL,
    release_date TEXT,
    downloaded_at TEXT NOT NULL,
    sha256 TEXT NOT NULL,
    license TEXT NOT NULL,
    attribution_url TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS claims (
    id TEXT PRIMARY KEY,                       -- Deterministic UUIDv5
    source_id TEXT NOT NULL REFERENCES sources(id),
    source_version TEXT NOT NULL,
    subject_type TEXT NOT NULL,                -- "LEXEME", "FORM", "SENSE", "SYNSET", etc.
    subject_source_id TEXT NOT NULL,
    predicate TEXT NOT NULL,                   -- e.g. "HAS_POS", "HAS_DEFINITION", "DERIVED_FROM"
    object_type TEXT,
    object_source_id TEXT,
    raw_payload JSON NOT NULL,
    normalized_payload JSON,
    evidence_type TEXT NOT NULL CHECK(evidence_type IN ("EXPLICIT", "GENERATED", "ATTESTED", "INFERRED", "UNCERTAIN")),
    confidence REAL NOT NULL CHECK(confidence >= 0.0 AND confidence <= 1.0),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_claims_subject ON claims(subject_type, subject_source_id);
CREATE INDEX IF NOT EXISTS idx_claims_predicate ON claims(predicate);

-- ---------------------------------------------------------------------
-- 2. Core Entities (Nodes) (ONTOLOGY.md §1, PRD §4)
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS forms (
    id TEXT PRIMARY KEY,                       -- Deterministic UUIDv5
    surface TEXT NOT NULL,
    normalized_surface TEXT NOT NULL,          -- Lowercase, NFC, whitespace trimmed
    script TEXT NOT NULL DEFAULT "Latn",
    language TEXT NOT NULL DEFAULT "eng",
    phonemic_ipa TEXT,
    phonetic_ipa TEXT,
    features_json JSON,                        -- UniMorph bundle: {number, tense, person, degree...}
    form_type TEXT NOT NULL CHECK(form_type IN ("BASE", "INFLECTED", "IRREGULAR", "SUPPLETIVE", "ANALYTIC")),
    source TEXT NOT NULL,
    evidence TEXT NOT NULL CHECK(evidence IN ("EXPLICIT", "GENERATED", "ATTESTED")),
    confidence REAL NOT NULL CHECK(confidence >= 0.0 AND confidence <= 1.0)
);

CREATE INDEX IF NOT EXISTS idx_forms_surface ON forms(surface);
CREATE INDEX IF NOT EXISTS idx_forms_normalized_surface ON forms(normalized_surface);

CREATE TABLE IF NOT EXISTS lexemes (
    id TEXT PRIMARY KEY,                       -- Deterministic UUIDv5
    lemma TEXT NOT NULL,
    normalized_lemma TEXT NOT NULL,
    language TEXT NOT NULL DEFAULT "eng",
    pos TEXT NOT NULL CHECK(pos IN (
        "NOUN", "VERB", "ADJECTIVE", "ADVERB", "PRONOUN", 
        "DETERMINER", "PREPOSITION", "CONJUNCTION", "INTERJECTION", 
        "AUXILIARY", "NUMERAL", "PARTICLE", "OTHER"
    )),
    lemma_form_id TEXT REFERENCES forms(id),
    lexeme_key TEXT UNIQUE NOT NULL,           -- HASH(language + normalized_lemma + pos)
    source_presence JSON NOT NULL,             -- Array of source IDs asserting presence
    frequency_summary JSON,                    -- {zipf, raw_count, tier}
    status TEXT NOT NULL CHECK(status IN ("CANONICAL", "PROVISIONAL", "DEPRECATED"))
);

CREATE INDEX IF NOT EXISTS idx_lexemes_lemma ON lexemes(lemma);
CREATE INDEX IF NOT EXISTS idx_lexemes_normalized_lemma ON lexemes(normalized_lemma);
CREATE INDEX IF NOT EXISTS idx_lexemes_pos ON lexemes(pos);

CREATE TABLE IF NOT EXISTS synsets (
    id TEXT PRIMARY KEY,                       -- Deterministic UUIDv5
    source TEXT NOT NULL,
    source_synset_id TEXT UNIQUE NOT NULL,     -- e.g. "oewn-02084071-v"
    pos TEXT NOT NULL CHECK(pos IN ("NOUN", "VERB", "ADJECTIVE", "ADVERB", "ADJECTIVE_SATELLITE")),
    gloss TEXT NOT NULL,
    domain TEXT,
    members JSON NOT NULL                      -- Array of member sense UUIDs
);

CREATE INDEX IF NOT EXISTS idx_synsets_source_id ON synsets(source_synset_id);

CREATE TABLE IF NOT EXISTS senses (
    id TEXT PRIMARY KEY,                       -- Deterministic UUIDv5
    lexeme_id TEXT NOT NULL REFERENCES lexemes(id) ON DELETE CASCADE,
    synset_id TEXT REFERENCES synsets(id) ON DELETE SET NULL,
    definition TEXT NOT NULL,
    usage_examples JSON,
    domain TEXT,
    register TEXT,
    source TEXT NOT NULL,
    source_sense_id TEXT,
    confidence REAL NOT NULL CHECK(confidence >= 0.0 AND confidence <= 1.0)
);

CREATE INDEX IF NOT EXISTS idx_senses_lexeme ON senses(lexeme_id);
CREATE INDEX IF NOT EXISTS idx_senses_synset ON senses(synset_id);

CREATE TABLE IF NOT EXISTS morphemes (
    id TEXT PRIMARY KEY,                       -- Deterministic UUIDv5
    shape TEXT NOT NULL,
    type TEXT NOT NULL CHECK(type IN (
        "PREFIX", "SUFFIX", "ROOT", "STEM", "BASE", 
        "INFLECTIONAL_AFFIX", "DERIVATIONAL_AFFIX", "CLITIC", "OTHER"
    )),
    status TEXT NOT NULL CHECK(status IN ("ATTESTED", "UNCERTAIN"))
);

CREATE INDEX IF NOT EXISTS idx_morphemes_shape ON morphemes(shape);

CREATE TABLE IF NOT EXISTS morphological_structures (
    id TEXT PRIMARY KEY,
    target_type TEXT NOT NULL CHECK(target_type IN ("LEXEME", "FORM")),
    target_id TEXT NOT NULL,                   -- References lexemes(id) or forms(id)
    structure_type TEXT NOT NULL CHECK(structure_type IN ("PREFIXATION", "SUFFIXATION", "COMPOUNDING", "CONVERSION", "COMPLEX")),
    components JSON NOT NULL,                  -- Constituent morpheme tree
    source TEXT NOT NULL,
    evidence TEXT NOT NULL CHECK(evidence IN ("EXPLICIT", "VALIDATED_RULE", "INFERRED")),
    confidence REAL NOT NULL CHECK(confidence >= 0.0 AND confidence <= 1.0)
);

CREATE INDEX IF NOT EXISTS idx_morph_target ON morphological_structures(target_type, target_id);

CREATE TABLE IF NOT EXISTS etymons (
    id TEXT PRIMARY KEY,
    lemma TEXT NOT NULL,
    language TEXT NOT NULL,                    -- Historical code: "ang", "enm", "lat", etc.
    period TEXT,
    transcription TEXT,
    source TEXT NOT NULL,
    evidence TEXT NOT NULL CHECK(evidence IN ("EXPLICIT", "ATTESTED", "UNCERTAIN")),
    confidence REAL NOT NULL CHECK(confidence >= 0.0 AND confidence <= 1.0)
);

CREATE TABLE IF NOT EXISTS constructions (
    id TEXT PRIMARY KEY,
    name TEXT UNIQUE NOT NULL,
    polarity TEXT NOT NULL CHECK(polarity IN ("POSITIVE", "NEGATIVE")),
    sentence_force TEXT NOT NULL CHECK(sentence_force IN ("ASSERTION", "QUESTION", "COMMAND", "EXCLAMATION")),
    tense TEXT,
    aspect TEXT,
    mood TEXT,
    voice TEXT,
    auxiliary_chain JSON,
    negation_strategy TEXT
);

-- ---------------------------------------------------------------------
-- 3. Core Relations Table (Edges) (ONTOLOGY.md §2, PRD §4.9)
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS relations (
    id TEXT PRIMARY KEY,                       -- Deterministic UUIDv5
    subject_type TEXT NOT NULL CHECK(subject_type IN ("LEXEME", "FORM", "SENSE", "SYNSET", "MORPHOLOGICAL_STRUCTURE")),
    subject_id TEXT NOT NULL,
    relation_type TEXT NOT NULL CHECK(relation_type IN (
        "HAS_FORM", "HAS_SENSE", "MEMBER_OF_SYNSET", "INFLECTS_TO",
        "DERIVED_FROM", "MORPHOLOGICALLY_RELATED", "VARIANT_OF",
        "SYNONYM_OF", "ANTONYM_OF", "HYPERNYM_OF", "HYPONYM_OF",
        "MERONYM_OF", "HOLONYM_OF", "ETYMOLOGICALLY_FROM",
        "CONTAINS_MORPHEME", "REALIZES"
    )),
    object_type TEXT NOT NULL CHECK(object_type IN ("LEXEME", "FORM", "SENSE", "SYNSET", "MORPHEME", "ETYMON", "CONSTRUCTION")),
    object_id TEXT NOT NULL,
    evidence_type TEXT NOT NULL CHECK(evidence_type IN ("EXPLICIT", "GENERATED", "ATTESTED", "INFERRED", "UNCERTAIN")),
    confidence REAL NOT NULL CHECK(confidence >= 0.0 AND confidence <= 1.0),
    resolution_status TEXT NOT NULL CHECK(resolution_status IN ("RESOLVED", "CONFLICTING", "SUPPRESSED"))
);

CREATE INDEX IF NOT EXISTS idx_relations_subject ON relations(subject_type, subject_id);
CREATE INDEX IF NOT EXISTS idx_relations_object ON relations(object_type, object_id);
CREATE INDEX IF NOT EXISTS idx_relations_type ON relations(relation_type);

-- ---------------------------------------------------------------------
-- 4. Claims Attribution Bridge Table (PRD §28 "Why Connected?")
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS relation_claims (
    relation_id TEXT NOT NULL REFERENCES relations(id) ON DELETE CASCADE,
    claim_id TEXT NOT NULL REFERENCES claims(id) ON DELETE CASCADE,
    PRIMARY KEY (relation_id, claim_id)
);

-- ---------------------------------------------------------------------
-- 5. Full-Text Search Indices (FTS5) (PRD §24, §41)
-- ---------------------------------------------------------------------
CREATE VIRTUAL TABLE IF NOT EXISTS fts_lexemes USING fts5(
    lemma,
    normalized_lemma,
    tokenize="unicode61"
);

CREATE VIRTUAL TABLE IF NOT EXISTS fts_senses USING fts5(
    definition,
    tokenize="unicode61"
);
