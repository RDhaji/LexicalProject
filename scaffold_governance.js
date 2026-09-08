const fs = require('fs');
const path = require('path');

const rootDir = '/Users/rd/Desktop/LexicalProject';
const adrDir = path.join(rootDir, 'adr');

fs.mkdirSync(adrDir, { recursive: true });

// Check and lock Level 1 Root Authority PRD.md
const prdPath = path.join(rootDir, 'PRD.md');
if (fs.existsSync(prdPath)) {
  console.log('[LOCKED & PRESERVED] PRD.md confirmed as Level 1 Root Authority.');
} else {
  fs.writeFileSync(prdPath, `# Product Requirements Document (PRD)
Version: 1.0.0
Status: LOCKED
Authority: Level 1 Root Authority

## 1. Core Mission & Linguistic Philosophy
A word is not a flat string. A lemma is not an inflected form. A sense is not an entire lexeme. Lexical Explorer is an offline-first, local-first knowledge engine providing deterministic linguistic truth, complete epistemic provenance, and graph-navigable morphology, syntax, and semantics for the English lexicon.

## 2. Inviolable Governance Principles
1. Hierarchy Authority: PRD.md -> ONTOLOGY.md -> ARCHITECTURE.md -> AI_ENGINEERING_RULES.md -> implementation.
2. Lexeme and Form Separation: Abstract lemmas and surface realizations never share tables, schemas, or node types.
3. Claims-Based Epistemic Provenance: Every resolved relationship must trace back to immutable source claims.
4. Prohibition of Heuristic Substrings: String overlaps (e.g., "car" in "carpet", "in-" in "internet") never generate linguistic relationships.
5. Prohibition of Stemmer Inversion: Algorithmic stemmers (Porter, Snowball, Krovetz) must never be inverted into generative grammars.
6. User Partition Safety: The user workspace database must remain completely decoupled from distribution graph builds.
`, 'utf8');
  console.log('[INITIALIZED] PRD.md');
}

const docs = {};

// =============================================================================
// ONTOLOGY.md
// =============================================================================
docs['ONTOLOGY.md'] = `# Lexical Ontology Specification
Version: 1.0.0
Status: LOCKED
Downstream From: PRD.md (Sections 4, 5, 6, 9, 10, 11, 12, 13, 14, 15, 16, 17)

## 1. Core Ontological Entities (Nodes)
All entities maintain deterministic UUIDv5 identifiers generated from an authoritative namespace (OID: \`6ba7b812-9dad-11d1-80b4-00c04fd430c8\`) and their natural key.

### 1.1 Lexeme
Represents an abstract lexical entry uniquely distinguished by its canonical lemma, grammatical POS, and language.
- \`id\`: UUID (Primary Key)
- \`lemma\`: TEXT (Original attested orthography)
- \`normalized_lemma\`: TEXT (NFC-normalized, case-folded, whitespace-trimmed)
- \`language\`: TEXT (ISO 639-3: "eng")
- \`pos\`: ENUM("NOUN", "VERB", "ADJECTIVE", "ADVERB", "PRONOUN", "DETERMINER", "PREPOSITION", "CONJUNCTION", "INTERJECTION", "AUXILIARY", "NUMERAL", "PARTICLE", "OTHER")
- \`lexeme_key\`: TEXT (Unique deterministic natural key: language + normalized_lemma + pos)
- \`source_presence\`: JSON (Array of authoritative sources asserting this lexeme)
- \`frequency_summary\`: JSON (Frequency tier, Zipf score, raw corpus count)
- \`status\`: ENUM("CANONICAL", "PROVISIONAL", "DEPRECATED")

### 1.2 Form
A surface realization of a Lexeme under specific grammatical features. A Form never instantiates an independent Lexeme.
- \`id\`: UUID (Primary Key)
- \`surface\`: TEXT (Attested surface string)
- \`normalized_surface\`: TEXT (NFC-normalized, case-folded)
- \`script\`: TEXT (Default "Latn")
- \`language\`: TEXT (Default "eng")
- \`phonemic_ipa\`: TEXT
- \`phonetic_ipa\`: TEXT
- \`features_json\`: JSON (UniMorph feature bundle: person, number, tense, aspect, mood, voice, degree)
- \`form_type\`: ENUM("BASE", "INFLECTED", "IRREGULAR", "SUPPLETIVE", "ANALYTIC")
- \`source\`: TEXT (Originating dataset identifier)
- \`evidence\`: ENUM("EXPLICIT", "GENERATED", "ATTESTED")
- \`confidence\`: REAL (0.00 to 1.00)

### 1.3 Sense
A discrete semantic meaning bound to exactly one Lexeme.
- \`id\`: UUID (Primary Key)
- \`lexeme_id\`: UUID (Foreign Key -> Lexeme.id)
- \`definition\`: TEXT (Semantic gloss)
- \`usage_examples\`: JSON (Attested usage citations)
- \`domain\`: TEXT (Semantic field or domain category)
- \`register\`: TEXT (Sociolinguistic register)
- \`source\`: TEXT (Authoritative source identifier)
- \`source_sense_id\`: TEXT (Original source key, e.g., OEWN sense key)
- \`confidence\`: REAL (0.00 to 1.00)

### 1.4 Synset
An abstract semantic concept node grouping cognitive synonyms.
- \`id\`: UUID (Primary Key)
- \`source\`: TEXT (e.g., "OEWN_2025")
- \`source_synset_id\`: TEXT (e.g., "oewn-02084071-v")
- \`gloss\`: TEXT (Concept definition and illustrative citations)
- \`domain\`: TEXT (Lexicographer file classification)
- \`members\`: JSON (Sense identifiers belonging to this synset)

### 1.5 Morpheme
A minimal meaningful morphological building block.
- \`id\`: UUID (Primary Key)
- \`shape\`: TEXT (Surface morpheme string: "un-", "-ness", "ceive")
- \`type\`: ENUM("PREFIX", "SUFFIX", "ROOT", "STEM", "BASE", "INFLECTIONAL_AFFIX", "DERIVATIONAL_AFFIX", "CLITIC", "OTHER")
- \`status\`: ENUM("ATTESTED", "UNCERTAIN")

### 1.6 MorphologicalStructure
Hierarchical constituent tree defining the internal structural composition of a word.
- \`id\`: UUID (Primary Key)
- \`target_type\`: ENUM("LEXEME", "FORM")
- \`target_id\`: UUID (Reference to Lexeme.id or Form.id)
- \`structure_type\`: ENUM("PREFIXATION", "SUFFIXATION", "COMPOUNDING", "CONVERSION", "COMPLEX")
- \`components\`: JSON (Constituent Morpheme IDs and nested structural nodes)
- \`source\`: TEXT
- \`evidence\`: ENUM("EXPLICIT", "VALIDATED_RULE", "INFERRED")
- \`confidence\`: REAL (0.00 to 1.00)

### 1.7 Etymon
Historical ancestral or donor lexical entry.
- \`id\`: UUID (Primary Key)
- \`lemma\`: TEXT (Historical form or reconstructed root)
- \`language\`: TEXT (ISO 639-3 or historical code: "ang", "enm", "fro", "lat", "ine-pro")
- \`period\`: TEXT (Attested century or chronological era)
- \`transcription\`: TEXT (Phonetic or transliterated representation)
- \`source\`: TEXT
- \`evidence\`: ENUM("EXPLICIT", "ATTESTED", "UNCERTAIN")
- \`confidence\`: REAL (0.00 to 1.00)

### 1.8 Construction
Grammatical patterns, phrasal frames, negation, and multiword aspectual structures.
- \`id\`: UUID (Primary Key)
- \`name\`: TEXT (e.g., "do_negation", "present_perfect_progressive")
- \`polarity\`: ENUM("POSITIVE", "NEGATIVE")
- \`sentence_force\`: ENUM("ASSERTION", "QUESTION", "COMMAND", "EXCLAMATION")
- \`tense\`: TEXT
- \`aspect\`: TEXT
- \`mood\`: TEXT
- \`voice\`: TEXT
- \`auxiliary_chain\`: JSON (Ordered auxiliary sequence)
- \`negation_strategy\`: TEXT (e.g., "dummy_do_insertion")

---

## 2. Ontological Relations (Edges)

Relations are explicitly directed, typed, and require evidence metadata.

| Relation Type | Source Entity | Target Entity | Epistemic Invariant |
|---|---|---|---|
| \`HAS_FORM\` | \`Lexeme\` | \`Form\` | Surface inflectional realization |
| \`HAS_SENSE\` | \`Lexeme\` | \`Sense\` | Strict 1-to-N parent-child boundary |
| \`MEMBER_OF_SYNSET\` | \`Sense\` | \`Synset\` | Conceptual grouping |
| \`INFLECTS_TO\` | \`Form\` | \`Form\` | Base form to inflected form mapping |
| \`DERIVED_FROM\` | \`Lexeme\` | \`Lexeme\` | Derivational process; references morphological rule |
| \`MORPHOLOGICALLY_RELATED\`| \`Lexeme\` | \`Lexeme\` | Morphological family membership |
| \`VARIANT_OF\` | \`Form\` / \`Lexeme\`| \`Form\` / \`Lexeme\`| Orthographic variation |
| \`SYNONYM_OF\` | \`Sense\` | \`Sense\` | Synset membership or explicit near-synonym claim |
| \`ANTONYM_OF\` | \`Sense\` | \`Sense\` | Direct lexical antonym link |
| \`HYPERNYM_OF\` | \`Synset\` | \`Synset\` | Conceptual taxonomic parent |
| \`HYPONYM_OF\` | \`Synset\` | \`Synset\` | Conceptual taxonomic child |
| \`MERONYM_OF\` | \`Synset\` | \`Synset\` | Conceptual part-of link |
| \`HOLONYM_OF\` | \`Synset\` | \`Synset\` | Conceptual container/whole link |
| \`ETYMOLOGICALLY_FROM\` | \`Lexeme\` | \`Etymon\` | Historical linguistic descent |
| \`CONTAINS_MORPHEME\` | \`MorphologicalStructure\` | \`Morpheme\` | Constituent composition |
| \`REALIZES\` | \`Form\` | \`Construction\` | Structural realization of an analytic frame |

---

## 3. Epistemic Classification Rules
Every relation and claim must carry an immutable epistemic class:
- \`EXPLICIT\`: Directly asserted in an authoritative source.
- \`GENERATED\`: Produced deterministically by an approved inflection or derivation rule.
- \`ATTESTED\`: Generated form verified against corpus or authoritative dictionary.
- \`INFERRED\`: Derived through controlled inference with structural validation.
- \`UNCERTAIN\`: Inconclusive, disputed, or conflicting source evidence.
`;

// =============================================================================
// ARCHITECTURE.md
// =============================================================================
docs['ARCHITECTURE.md'] = `# System Architecture Document
Version: 1.0.0
Status: LOCKED
Downstream From: PRD.md, ONTOLOGY.md

## 1. System Topology
The platform operates as an offline-first, local-first Progressive Web App (PWA) backed by an embedded SQLite relational database compiled via an offline batch pipeline.

\`\`\`
┌────────────────────────────────────────────────────────┐
│                   Progressive Web App                  │
│  (UI Shell / Word Page / Morph Graph / Why-Connected)  │
└───────────────────────────┬────────────────────────────┘
                            │ Indexed SQL Traversal
┌───────────────────────────▼────────────────────────────┐
│              Client Storage Subsystem (WASM)           │
│                                                        │
│  [ lexical_graph.db ] (Read-Only Graph Distribution)  │
│    - lexemes, forms, senses, synsets                   │
│    - relations, claims, sources, frequency             │
│                                                        │
│  [ user_workspace.db ] (Persistent User Partition)     │
│    - notes, favorites, bookmarks, custom tags          │
│    - linked strictly via immutable UUID references     │
└───────────────────────────▲────────────────────────────┘
                            │ Atomic Compilation
┌───────────────────────────┴────────────────────────────┐
│               Data Ingestion & Build Pipeline          │
│  [OEWN]   [Wiktionary JSONL]   [UniMorph]   [SUBTLEX] │
│     │              │                │           │     │
│     ▼              ▼                ▼           ▼     │
│  Streaming Snapshot Parsers -> Normalization           │
│                            ↓                           │
│  Staged Claims -> Entity Resolver -> Morphology Engine │
│                            ↓                           │
│  Inference Engine -> Quality Gates -> SQLite Compiler  │
└────────────────────────────────────────────────────────┘
\`\`\`

## 2. Partitioning & Data Isolation Invariant (PRD Section 39, ADR-006)
1. **Distribution Isolation:** Rebuilding \`lexical_graph.db\` never drops, locks, or alters \`user_workspace.db\`.
2. **Zero Foreign Keys:** \`user_workspace.db\` maintains zero SQLite foreign keys into \`lexical_graph.db\`.

## 3. The Claims vs. Relations Subsystem (ADR-002)
- **Claims Table (\`claims\`):** Immutable ledger preserving raw assertions directly extracted from specific source versions.
- **Relations Table (\`relations\`):** Resolved canonical graph edges exposed to the application. Every relation maps directly back to supporting claims. Disputed claims are preserved and marked with an \`UNCERTAIN\` or \`CONFLICTING\` status.

## 4. Query & Traversal Engine Bounds
- Local exact match and prefix lookup powered by SQLite covering indices on \`normalized_surface\` and \`normalized_lemma\`.
- Interactive graph expansions bounded to depth $D \\le 3$ for interactive UI latency targets (<250 ms).
- Full-text search over definitions and usage notes supported via SQLite FTS5.
`;

// =============================================================================
// DATA_SOURCES.md
// =============================================================================
docs['DATA_SOURCES.md'] = `# Authoritative Data Sources Specification
Version: 1.0.0
Status: LOCKED
Downstream From: PRD.md (Sections 7, 8, 30, 46, 68)

## 1. Approved Primary Sources

| Source Identifier | Version Baseline | Artifact Format | Primary Authority Scope | License Type |
|---|---|---|---|---|
| \`OEWN_2025\` | 2025 Stable | JSON / WN-LMF | Synsets, Semantic Hierarchy, Derivational Links | WordNet License / CC BY 4.0 |
| \`WIKTIONARY_KAIKKI_20260805\` | 2026-08-05 Dump | Streaming JSONL | POS, Definitions, IPA, Etymology, Attestations | CC BY-SA 4.0 / GFDL |
| \`UNIMORPH_ENG\` | Master / Stable | TSV Tables | Inflectional Realizations, Grammatical Bundles | CC BY-SA 4.0 |
| \`SUBTLEX_US_R1\` | Release 1.0 | TSV Table | Word & Lemma Usage Frequency Ranks | Research / Educational Free |
| \`CELEX2\` | Optional Local | Restricted TSV | Morphology & Syntax Validation (NON-REDISTRIBUTABLE)| LDC License Agreement |

## 2. Ingestion & Snapshotting Rules
1. **Manifest Verification:** Every source artifact must match its SHA-256 hash in \`data/sources/manifest.json\` before parsing begins.
2. **Streaming Execution:** The Kaikki Wiktionary JSONL export (~22.9 GB uncompressed) must be parsed via a streaming line-by-line processor. Whole-file memory loading is prohibited.
3. **Attribution & Licensing:** Every build must emit a verified \`SOURCE_ATTRIBUTION.md\` documenting licenses, modifications, and redistribution restrictions.
`;

// =============================================================================
// INGESTION_PIPELINE.md
// =============================================================================
docs['INGESTION_PIPELINE.md'] = `# Ingestion Pipeline Specification
Version: 1.0.0
Status: LOCKED
Downstream From: PRD.md (Sections 29, 34, 35, 46, 57)

## 1. Pipeline Execution Stages

\`\`\`
[Stage 0: Manifest Preflight & Checksums]
  Verify local archive presence and SHA-256 signatures against manifest.json.
        ↓
[Stage 1: Streaming Source Parsers]
  Extract raw lines/records; populate staging_claims tables without heuristic mutations.
        ↓
[Stage 2: Canonical Normalization]
  Execute NFC normalization, case-folding, POS mapping, and feature bundle canonicalization.
        ↓
[Stage 3: Entity Resolution]
  Map source entries to deterministic UUIDv5 canonical Lexemes, Forms, Senses, and Synsets.
        ↓
[Stage 4: Morphology Build & Separation]
  Separate inflectional realizations from derivational processes into distinct structures.
        ↓
[Stage 5: Controlled Inference Engine]
  Generate candidate edges; execute attestation and existence checks.
        ↓
[Stage 6: Claim Resolution & Conflict Marking]
  Evaluate competing claims; mark unresolved conflicts; compile resolved relations.
        ↓
[Stage 7: Quality Gates A–G]
  Halt compilation on integrity failure or false-positive regression detection.
        ↓
[Stage 8: SQLite Compilation & Indexing]
  Materialize final database tables, B-Trees, and FTS5 search structures.
\`\`\`

## 2. Mandatory Pipeline Quality Gates
- **Gate A (Source Integrity):** All files match manifest SHA-256; zero unhandled parse errors.
- **Gate B (Ontology Integrity):** Zero foreign key orphans; no unmapped POS tags.
- **Gate C (Morphology Baseline):** Benchmark words pass verification (\`go -> went\`, \`mouse -> mice\`, \`run -> running\`, \`fast -> faster -> fastest\`).
- **Gate D (False-Positive Regression):** Traps verified disconnected (\`go ≠ goal\`, \`ride ≠ riddance\`, \`art ≠ article\`, \`car ≠ carpet\`).
- **Gate E (Provenance Completeness):** 100% of visible non-derived relations trace to a supporting claim.
`;

// =============================================================================
// MORPHOLOGY.md
// =============================================================================
docs['MORPHOLOGY.md'] = `# Morphology Engine & Separation Specification
Version: 1.0.0
Status: LOCKED
Downstream From: PRD.md (Sections 4.2, 4.5, 4.6, 6, 12, 13, 14, 21, 22, 51, ADR-003, ADR-005)

## 1. The Core Morphology Invariant
**Inflection and Derivation are formally distinct linguistic subsystems and must NEVER share relational types, entity representations, or database tables.**

\`\`\`
               ┌─────────────────────────────────────────┐
               │           Lexeme: run [VERB]            │
               └────────────┬───────────────┬────────────┘
                            │               │
       [Inflectional Realization]     [Derivational Process]
       (Edge: HAS_FORM)               (Edge: DERIVED_FROM)
                            │               │
                            ▼               ▼
               ┌──────────────────┐   ┌─────────────────────────┐
               │  Form: "running" │   │   Lexeme: runner [NOUN] │
               │  [PARTICIPLE]    │   └─────────────┬───────────┘
               └──────────────────┘                 │
                                          [Inflectional Realization]
                                                    │
                                                    ▼
                                      ┌─────────────────────────┐
                                      │  Form: "runners" [PL]   │
                                      └─────────────────────────┘
\`\`\`

## 2. Inflectional Model
- Governed by UniMorph paradigms and verified inflectional tables.
- Inflections map a \`Lexeme\` to a surface \`Form\` (edge: \`HAS_FORM\`).
- Forms express grammatical feature bundles: \`person\`, \`number\`, \`tense\`, \`aspect\`, \`mood\`, \`voice\`, \`degree\`.
- An inflected form never instantiates a new \`Lexeme\`.

## 3. Derivational Model
- Derivations link a base \`Lexeme\` to a derived \`Lexeme\` (edge: \`DERIVED_FROM\`).
- Must document the morphological process (prefixation, suffixation, compounding, conversion).
- Every derivational edge requires an attested source claim or validated rule confirmation.

## 4. Strict Heuristic Prohibition
1. **No Substring Matching:** A string prefix or suffix overlap (e.g., "in-" in "internet", "car" in "carpet") must never generate a relationship.
2. **No Stemmer Inversion:** Generic algorithmic stemmers (Porter, Snowball, Krovetz) must NEVER be inverted to manufacture roots or morphological families.
`;

// =============================================================================
// AI_ENGINEERING_RULES.md
// =============================================================================
docs['AI_ENGINEERING_RULES.md'] = `# AI Engineering Rules & Governance Protocols
Version: 1.0.0
Status: LOCKED
Downstream From: PRD.md (Sections 52, 56, 57)

## 1. Absolute Invariants
1. **Hierarchy Authority:** Never write code or propose schemas that contradict upstream specifications (\`PRD.md\` -> \`ONTOLOGY.md\` -> \`ARCHITECTURE.md\` -> \`AI_ENGINEERING_RULES.md\` -> implementation).
2. **Ontology Protection:** Do not modify \`ONTOLOGY.md\` without an explicit, approved Architecture Decision Record (ADR).
3. **Zero Fact Invention:** Do not synthesize or hallucinate linguistic facts, etymologies, IPA strings, or definitions. Absence of data must be recorded as \`NULL\` or \`UNATTESTED\`.
4. **No Silent Merging:** Never overwrite contradictory source claims. Preserve both claims and mark the relation \`UNCERTAIN\` or \`CONFLICTING\`.
5. **Morphological Separation:** Never conflate surface forms with lexemes, or inflection with derivation.
6. **User Partition Safety:** Never modify, drop, or migrate \`user_workspace.db\` during source database rebuilds.
7. **Test Gates:** Never weaken assertions, delete tests, or skip Quality Gates to pass a build.
8. **Architectural Purity:** Never introduce hacks in presentation code to solve data or morphological flaws.

## 2. Mandatory Escalation Gates
Execution MUST HALT and request human engineering direction when:
1. A proposed change alters an entity or relation definition in \`ONTOLOGY.md\`.
2. A source dataset license is ambiguous, non-commercial, or conflicts with distribution goals.
3. Two authoritative sources materially conflict with no documented resolution rule.
4. A relation cannot be categorized definitively under the 5 epistemic classes.
5. A proposed database migration requires dropping non-reconstructible data.
6. A performance optimization proposal sacrifices provenance or explainability.
7. A linguistic rule produces a false-positive rate > 0.1% on a regression test suite.
8. An ingestion run causes an unexpected graph node or edge variance > 15%.
`;

// =============================================================================
// SOURCE_ATTRIBUTION.md
// =============================================================================
docs['SOURCE_ATTRIBUTION.md'] = `# Source Attribution & Licensing Ledger
Version: 1.0.0
Status: LOCKED
Downstream From: PRD.md (Section 8, Section 68)

## 1. Primary Datasets

### 1.1 Open English WordNet (OEWN)
- **Identifier:** OEWN_2025
- **Version:** 2025 Release
- **URL:** https://en-word.net/
- **License:** CC BY 4.0 / WordNet License
- **Attribution Text:**
  > Open English WordNet 2025, John P. McCrae, Michael Wayne Goodman, Francis Bond, et al.
- **Redistribution Policy:** Permitted with attribution; modified records must document derivation pipeline version.

### 1.2 Kaikki Wiktextract (English Wiktionary)
- **Identifier:** WIKTIONARY_KAIKKI_20260805
- **Version:** 2026-08-05 Snapshot
- **URL:** https://kaikki.org/dictionary/rawdata.html
- **License:** CC BY-SA 4.0 and GNU Free Documentation License (GFDL)
- **Attribution Text:**
  > English Wiktionary parsed via Wiktextract/Kaikki (2026-08-05). Original text by Wiktionary contributors.
- **Redistribution Policy:** ShareAlike rules apply to derived lexical entries. Commercial distribution must conform to CC BY-SA 4.0.

### 1.3 UniMorph English
- **Identifier:** UNIMORPH_ENG
- **Version:** Master Stable
- **URL:** https://github.com/unimorph/eng
- **License:** CC BY-SA 4.0
- **Attribution Text:**
  > The UniMorph project: Universal Morphological Annotations.
- **Redistribution Policy:** Permitted under CC BY-SA 4.0 terms.

### 1.4 SUBTLEX-US
- **Identifier:** SUBTLEX_US_R1
- **Version:** 1.0
- **URL:** https://www.ugent.be/pp/experimentele-psychologie/en/research/documents/subtlexus
- **License:** Free for academic, educational, and research applications.
- **Attribution Text:**
  > Brysbaert, M., & New, B. (2009). Moving beyond Kučera and Francis: A critical evaluation of current word frequency norms and the introduction of a new and improved word frequency measure for American English. Behavior Research Methods, 41(4), 977-990.
- **Redistribution Policy:** Frequency values embedded as static rank lookup tables.

## 2. Incompatible Material Exclusions (PRD §7.5)
- **CELEX2:** Not bundled. Subject to restricted Linguistic Data Consortium (LDC) agreement; used only in local validation environments when explicitly authorized.
`;

// =============================================================================
// ADRs (ADR-001 through ADR-007)
// =============================================================================
docs['adr/ADR-001-hybrid-graph.md'] = `# ADR-001: Hybrid Evidence-Layered Graph
Status: APPROVED
Date: 2026-09-04

### Context
No single lexical resource adequately covers English semantics, inflectional morphology, etymology, contemporary vocabulary, and corpus frequency.

### Decision
Adopt a hybrid multi-source ingestion model combining Open English WordNet (semantic backbone), Wiktionary/Kaikki (definitions, forms, etymology), UniMorph (inflection paradigms), and SUBTLEX-US (frequency rankings).

### Consequences
- Positive: Rich, multidimensional lexical graph with cross-source validation.
- Negative: Requires an entity resolution engine and explicit conflict management.
`;

docs['adr/ADR-002-claims-resolution.md'] = `# ADR-002: Claims + Resolved Graph Separation
Status: APPROVED
Date: 2026-09-04

### Context
Authoritative sources frequently disagree on parts of speech, etymologies, and derivations. Overwriting sources into a single table causes permanent loss of provenance.

### Decision
Bifurcate persistence into a raw \`claims\` table preserving exact source statements and a \`relations\` table representing current resolved presentation edges.

### Consequences
- Positive: Total explainability; supports "Why Connected?"; allows non-destructive reruns of resolution rules.
- Negative: Higher storage footprint and double-stage build pipeline.
`;

docs['adr/ADR-003-lexeme-form.md'] = `# ADR-003: Lexeme and Form Separation
Status: APPROVED
Date: 2026-09-04

### Context
Treating inflected surface realizations (e.g., "ran", "faster") as lexemes pollutes semantic and morphological networks.

### Decision
Enforce strict separation between abstract \`Lexeme\` nodes and grammatical \`Form\` realizations. Inflectional variants map to lexemes via \`HAS_FORM\` edges carrying UniMorph feature bundles.

### Consequences
- Positive: True morphological precision; prevents exponential lemma explosion.
- Negative: Querying from surface strings requires an indexed join through the forms table.
`;

docs['adr/ADR-004-construction-layer.md'] = `# ADR-004: Dedicated Construction & Grammar Layer
Status: APPROVED
Date: 2026-09-04

### Context
Multiword patterns, analytic verb forms, questions, and negations (e.g., "does not run") cannot be modeled as simple surface forms of a single lexeme without distorting lexical truth.

### Decision
Implement a decoupled \`Construction\` entity layer modeling syntactic patterns, polarity, auxiliary chains, and sentence force independently from the lexical graph.

### Consequences
- Positive: Prevents synthetic multiword pollution in the lexeme store.
- Negative: Requires dedicated slot-matching templates for phrasal realizations.
`;

docs['adr/ADR-005-no-stemmer-inversion.md'] = `# ADR-005: Prohibition of Algorithmic Stemmer Inversion
Status: APPROVED
Date: 2026-09-04

### Context
Inverting heuristic algorithmic stemmers (Porter, Snowball, Krovetz) to generate morphological roots creates catastrophic false-positive relationships (e.g., "organization" -> "organ").

### Decision
Strictly forbid using stemmers as generative morphological engines. All morphological decompositions must terminate at attested morphemes verified by explicit source claims or validated rule engines.

### Consequences
- Positive: Zero heuristic morphological hallucinations.
- Negative: Unattested or rare words will show unanalyzed morphology rather than speculative breakdowns.
`;

docs['adr/ADR-006-local-compiled-database.md'] = `# ADR-006: Local Compiled SQLite Database for PWA
Status: APPROVED
Date: 2026-09-04

### Context
The application must operate offline-first for a single user without server dependencies or external graph database daemons.

### Decision
Compile the resolved knowledge graph into an embedded SQLite database (\`lexical_graph.db\`) for local PWA execution, maintaining a physically distinct \`user_workspace.db\` for user state.

### Consequences
- Positive: Zero runtime infrastructure; sub-50ms local query latency; complete offline independence.
- Negative: Batch builds must generate optimized B-Trees and FTS5 structures ahead of distribution.
`;

docs['adr/ADR-007-correctness-before-compression.md'] = `# ADR-007: Prioritization of Correctness Over Compression
Status: APPROVED
Date: 2026-09-04

### Context
Aggressive premature database compression risks stripping out provenance claims, confidence scores, and historical variants.

### Decision
Prioritize linguistic correctness, explicit provenance, and structural explainability over minimizing disk footprint. Accept a moderately larger local database to preserve total auditability.

### Consequences
- Positive: Uncompromised linguistic integrity; full adherence to the PRD root principle.
- Negative: Higher initial installation download size.
`;

// Write all specifications and ADRs
for (const [relPath, content] of Object.entries(docs)) {
  const targetPath = path.join(rootDir, relPath);
  fs.writeFileSync(targetPath, content.trim() + '\n', 'utf8');
  console.log('[LOCKED & CREATED] ' + relPath);
}

console.log('\n[SUCCESS] Governance specifications and ADR ledger deployed.');
