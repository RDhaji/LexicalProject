# PRD — English Lexical & Morphological Explorer
Version: 1.0.0
Status: LOCKED
Authority: Level 1 Root Specification
Target: Private, one-user Progressive Web App (PWA)
Primary language: English
Primary goal: Build a robust, explainable semantic + morphological knowledge graph for practical exploration of English words.

---

## 1. Product Summary

Build a private, local-first PWA that lets one user explore how English words are formed, inflected, derived, semantically related, historically related, used across parts of speech, ranked by usage frequency, and connected through explicit, evidence-backed relationships.

The application is a practical linguistic explorer, not merely a dictionary.

The system must prefer linguistic correctness, explainability, provenance, reproducibility, and extensibility over aggressive compression or maximal automatic inference.

### Core Product Principle

> A string is not a linguistic relationship.

The system must never infer a lexical relationship simply because one word is a substring, prefix, suffix, or spelling variant of another. Every graph edge must be explicit, generated under a documented rule, or inferred with a visible confidence/evidence status.

---

## 2. Inviolable Governance Principles

1. **Hierarchy Authority:** `PRD.md` -> `ONTOLOGY.md` -> `ARCHITECTURE.md` -> `AI_ENGINEERING_RULES.md` -> Implementation.
2. **Lexeme and Form Separation:** Abstract lemmas and grammatical surface realizations never share tables, schemas, or node types.
3. **Claims-Based Epistemic Ledger:** All resolved relationships must trace back to immutable source claims. Disagreements between sources are preserved, not silently averaged or dropped.
4. **Prohibition of Heuristic Substrings:** String overlaps never generate graph edges (e.g., car ≠ carpet, art ≠ article).
5. **Stemmer Inversion Ban:** Algorithmic stemmers (Porter, Snowball, Krovetz) must never be inverted into generative grammars.
6. **User Partition Safety:** Rebuilding the distribution graph must never drop, alter, or lock user data.
7. **Vertical-Slice Requirement:** All pipeline modifications must be validated against the fixture dataset (`run`, `fast`, `happy`, `go`, `good`, `bad`, `bank`) before executing on full-scale raw dumps.

---

## 3. Epistemic Classification System

Every relationship edge belongs to exactly one class:
- `EXPLICIT`: Directly asserted by an authoritative source.
- `GENERATED`: Produced deterministically by an approved formal morphological rule.
- `ATTESTED`: Validated by corpus presence or dictionary record.
- `INFERRED`: Produced via controlled logical inference under validation gates.
- `UNCERTAIN`: Conflicted or lacking primary corroboration.

---

## 4. Goals

### 4.1 Primary Goals
1. Create a high-quality English lexical knowledge graph.
2. Distinguish lexemes, forms, senses, synsets, morphemes, etymons, and constructions.
3. Represent both explicit source relationships and controlled inferred relationships.
4. Show inflectional forms (person, number, tense, aspect, mood, voice, degree).
5. Show derivational families.
6. Show morphological composition (prefixes, suffixes, stems, roots/morphemes).
7. Show definitions, synonyms, antonyms, hypernyms, hyponyms, semantic hierarchy, etymology, and IPA/pronunciation.
8. Support comparative and superlative forms.
9. Represent negation, assertion, questions, passive constructions, auxiliaries, tense/aspect combinations as grammar/construction objects.
10. Preserve provenance for facts and relationships.
11. Make source updates reproducible.
12. Compile a query-efficient local SQLite database for the PWA.
13. Make the system explain why two items are connected.
14. Minimize future schema refactors.

### 4.2 Secondary Goals
- Fast lookup (<50ms exact match).
- Offline-first operation via embedded SQLite (sql.js / WebAssembly).
- Search suggestions/autocomplete (<100ms).
- Interactive family/relationship graphs (<250ms traversal).
- User notes/favorites/bookmarks isolated in a user partition.
- Future extensibility for new corpora without core schema refactors.

---

## 5. Non-Goals for V1

Do NOT attempt these in V1:
1. Full English syntactic parsing of arbitrary sentences.
2. Full sense-frequency estimation from raw corpora.
3. Automatic discovery of historically valid etymologies.
4. Perfect morphological analysis for every English word.
5. Automatically declaring every morphologically plausible word to be a valid lexical item.
6. Native-language expansion beyond English.
7. AI-generated definitions replacing source glosses.
8. Treating Wiktionary as infallible.
9. Treating WordNet/OEWN as a complete English lexicon.
10. Building a general-purpose NLP platform.

---

## 6. Performance Targets (SLAs)

- Exact search: <50ms after DB warm-up.
- Autocomplete: <100ms.
- Word page query set: <150ms.
- Bounded graph expansion ($D \le 3$): <250ms.
- First meaningful UI render: <2 seconds on desktop.

---

## 7. Linguistic Ontology Overview

Entity classes must remain strictly isolated:
- **Lexeme:** Abstract lexical entry tied to a specific POS (`language:normalized_lemma:pos`).
- **Form:** Grammatical surface realization with UniMorph feature bundles (`HAS_FORM`).
- **Sense:** Granular definition tied to a Lexeme.
- **Synset:** Semantic equivalence set from OEWN/WordNet.
- **Morpheme:** Component affix, root, or stem (`CONTAINS_MORPHEME`).
- **MorphologicalStructure:** Structural derivation/compounding tree.
- **Etymon:** Historical ancestor node (`ETYMOLOGICALLY_FROM`).
- **Construction:** Decoupled syntactic pattern, polarity, and auxiliary chain (`REALIZES`).

---

## 8. Authoritative Data Sources

- **OEWN 2025:** Synsets, semantic taxonomy, derivational links (CC BY 4.0).
- **Wiktionary (Wiktextract/Kaikki 2026-08-05):** POS, definitions, IPA, inflections, etymology (CC BY-SA 4.0 / GFDL; Streaming JSONL required).
- **UniMorph (eng):** Inflectional paradigms, grammatical feature bundles (CC BY-SA 4.0).
- **SUBTLEX-US R1:** Usage frequency ranks for ranking and autocomplete (Research/Educational).
- **CELEX2:** Optional local-only validation baseline (Restricted LDC License; not redistributable).

---

## 9. Quality Gates

- **Gate A (Source Integrity):** Manifest SHA-256 match; zero unhandled parse errors.
- **Gate B (Ontology Integrity):** Zero foreign key orphans; no unmapped POS tags.
- **Gate C (Morphology Baseline):** Benchmark words pass (`go -> went`, `mouse -> mice`, `run -> running`, `fast -> faster -> fastest`, `good -> better -> best`, `bad -> worse -> worst`).
- **Gate D (False-Positive Regression):** Traps verified disconnected (`go ≠ goal`, `ride ≠ riddance`, `art ≠ article`, `car ≠ carpet`).
- **Gate E (Provenance Completeness):** 100% of visible non-derived relations trace to a supporting claim.
- **Gate F (Search Integrity):** Exact search <50ms; autocomplete <100ms.
- **Gate G (Performance Bounds):** All graph queries ($D \le 3$) execute in $<250$ms.

---

## 10. Milestone Structure

- **M0:** Foundation & Fixture Verification (`run`, `fast`, `happy`, `go`, `good`, `bad`, `bank`)
- **M1:** Semantic Backbone (OEWN 2025 Parser & Synset Taxonomy)
- **M2:** Lexical Ingestion (Kaikki Streaming JSONL & UniMorph English)
- **M3:** Entity Resolution Engine (Deterministic UUIDv5 Resolver)
- **M4:** Morphology Core (Inflection vs Derivation Separation & Affixes)
- **M5:** Intelligence Layer & Quality Gates A-G Verification
- **M6:** SQLite Compilation & B-Tree Indexing (<250ms SLA)
- **M7:** Offline PWA Client & Workspace Sync Bridge
- **M8:** Adversarial Hardening & Negative Traps Suite
- **M9:** Final Packaging & Acceptance Release Sign-Off
