# Lexical Ontology Specification
Version: 1.0.0
Status: LOCKED
Downstream From: PRD.md

## 1. Core Entities (Nodes)
All entities maintain deterministic UUIDv5 identifiers generated from namespace OID `6ba7b812-9dad-11d1-80b4-00c04fd430c8` and their natural key.

### 1.1 Lexeme
- `id`: UUIDv5 (Primary Key)
- `lemma`: TEXT (Attested orthography)
- `normalized_lemma`: TEXT (NFC-normalized, case-folded)
- `language`: TEXT (ISO 639-3: "eng")
- `pos`: ENUM("NOUN", "VERB", "ADJECTIVE", "ADVERB", "PRONOUN", "DETERMINER", "PREPOSITION", "CONJUNCTION", "INTERJECTION", "AUXILIARY", "NUMERAL", "PARTICLE", "OTHER")
- `lexeme_key`: TEXT UNIQUE (`language:normalized_lemma:pos`)
- `source_presence`: JSON
- `frequency_summary`: JSON
- `status`: ENUM("CANONICAL", "PROVISIONAL", "DEPRECATED")

### 1.2 Form
- `id`: UUIDv5 (Primary Key)
- `lexeme_id`: UUIDv5 (Foreign Key -> Lexeme.id)
- `surface`: TEXT (Attested surface string)
- `normalized_surface`: TEXT (NFC-normalized, case-folded)
- `features_json`: JSON (UniMorph feature bundle: person, number, tense, aspect, mood, voice, degree)
- `form_type`: ENUM("BASE", "INFLECTED", "IRREGULAR", "SUPPLETIVE", "ANALYTIC")
- `source`: TEXT
- `evidence`: ENUM("EXPLICIT", "GENERATED", "ATTESTED")
- `confidence`: REAL (0.00 to 1.00)

### 1.3 Sense
- `id`: UUIDv5 (Primary Key)
- `lexeme_id`: UUIDv5 (Foreign Key -> Lexeme.id)
- `synset_id`: UUIDv5 (Foreign Key -> Synset.id, NULLable)
- `definition`: TEXT
- `usage_examples`: JSON
- `domain`: TEXT
- `register`: TEXT
- `source`: TEXT
- `source_sense_id`: TEXT
- `confidence`: REAL (0.00 to 1.00)

### 1.4 Synset
- `id`: UUIDv5 (Primary Key)
- `source`: TEXT (e.g., "OEWN_2025")
- `source_synset_id`: TEXT
- `pos`: TEXT
- `gloss`: TEXT
- `domain`: TEXT
- `members`: JSON

### 1.5 Morpheme
- `id`: UUIDv5 (Primary Key)
- `shape`: TEXT ("un-", "-ness", "ceive")
- `type`: ENUM("PREFIX", "SUFFIX", "ROOT", "STEM", "BASE", "INFLECTIONAL_AFFIX", "DERIVATIONAL_AFFIX", "CLITIC", "OTHER")
- `status`: ENUM("ATTESTED", "UNCERTAIN")

### 1.6 MorphologicalStructure
- `id`: UUIDv5 (Primary Key)
- `target_type`: ENUM("LEXEME", "FORM")
- `target_id`: UUIDv5
- `structure_type`: ENUM("PREFIXATION", "SUFFIXATION", "COMPOUNDING", "CONVERSION", "COMPLEX")
- `components`: JSON
- `source`: TEXT
- `evidence`: ENUM("EXPLICIT", "VALIDATED_RULE", "INFERRED")
- `confidence`: REAL (0.00 to 1.00)

### 1.7 Etymon
- `id`: UUIDv5 (Primary Key)
- `lemma`: TEXT
- `language`: TEXT (ISO 639-3 or historical code: "ang", "lat")
- `period`: TEXT
- `transcription`: TEXT
- `source`: TEXT
- `evidence`: ENUM("EXPLICIT", "ATTESTED", "UNCERTAIN")
- `confidence`: REAL (0.00 to 1.00)

### 1.8 Construction
- `id`: UUIDv5 (Primary Key)
- `name`: TEXT
- `polarity`: ENUM("POSITIVE", "NEGATIVE")
- `sentence_force`: ENUM("ASSERTION", "QUESTION", "COMMAND", "EXCLAMATION")
- `tense`: TEXT
- `aspect`: TEXT
- `mood`: TEXT
- `voice`: TEXT
- `auxiliary_chain`: JSON
- `negation_strategy`: TEXT

## 2. Core Relations (Edges)
`HAS_FORM`, `HAS_SENSE`, `MEMBER_OF_SYNSET`, `INFLECTS_TO`, `DERIVED_FROM`, `MORPHOLOGICALLY_RELATED`, `VARIANT_OF`, `SYNONYM_OF`, `ANTONYM_OF`, `HYPERNYM_OF`, `HYPONYM_OF`, `MERONYM_OF`, `HOLONYM_OF`, `ETYMOLOGICALLY_FROM`, `CONTAINS_MORPHEME`, `REALIZES`.

## Entity: CONSTRUCTION
- Description: Abstract schematic pairing of form and meaning per ADR-004 and ADR-008.
- Attributes: id (TEXT, PK), name (TEXT), description (TEXT), created_at (INTEGER).

## Relation: REALIZES
- Source: LEXEME | FORM
- Target: CONSTRUCTION
- Invariants: Partitioned strictly across 5 epistemic classes (EXPLICIT, GENERATED, ATTESTED, INFERRED, UNCERTAIN). No substring or edit-distance generation (Invariant 4). Forms remain distinct from Lexemes (Invariant 6). Cross-DB isolation preserved (Invariant 7).

## Secondary Lexical Source Extensions (ADR-009)
### Entity Types
- `SEMANTIC_FRAME`: FrameNet semantic frame representation.
- `VERB_CLASS`: VerbNet hierarchical class and thematic role representation.

### Relation Types
- `EVOKES`: Directed relation from `LEXEME` to `SEMANTIC_FRAME` (Epistemic: ATTESTED / CONFLICTING).
- `MEMBER_OF_CLASS`: Directed relation from `LEXEME` to `VERB_CLASS` (Epistemic: ATTESTED).

### Lexeme Attributes
- `frequency_zipf`: Zipf scale frequency value (REAL, NULL if unattested).
- `corpus_source`: Provenance identifier for frequency metadata (TEXT, NULL if unattested).


### Entity: PRONUNCIATION
- **id**: UUIDv5 deterministic identifier
- **target_id**: UUIDv5 reference to `lexemes.id` or `forms.id`
- **target_type**: Enum (`LEXEME`, `FORM`)
- **notation**: Enum (`IPA`, `ARPABET`)
- **transcription**: TEXT (attested phonetic transcription)
- **variety**: TEXT (dialect tag, e.g., `en-US`, `en-GB`)
- **epistemic_class**: Enum (`ATTESTED`, `EXPLICIT`)
- **provenance_id**: TEXT

### Relation: HAS_PRONUNCIATION
- **Source**: `LEXEMES` | `FORMS`
- **Target**: `PRONUNCIATION`
- **Allowed Epistemic Classes**: `EXPLICIT`, `ATTESTED`
- **Invariants**:
  - Lemma citation pronunciations attach strictly to `lexemes.id`.
  - Inflected surface realization pronunciations attach strictly to `forms.id` (Invariant 6).
  - Missing pronunciations remain `NULL` (Invariant 2).
  - Phonetic distance must never generate morphological or semantic edges (Invariant 4).


### Relation: TRANSLATION_OF
- **Source**: `LEXEMES`
- **Target**: `LEXEMES`
- **Allowed Epistemic Classes**: `EXPLICIT`, `ATTESTED`, `UNCERTAIN`
- **Invariants**:
  - Cross-lingual edges connect Lexemes only; Forms never connect across languages (Invariant 6).
  - Attestation must come from curated bilingual dictionaries; string overlap strictly prohibited (Invariant 4).
  - Polysemous mismatches or contested alignments must be marked `UNCERTAIN` (Invariant 3).
  - Unaligned lexemes remain NULL (Invariant 2).
