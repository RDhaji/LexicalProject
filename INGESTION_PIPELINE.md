# Ingestion Pipeline Specification
Version: 1.0.0
Status: LOCKED
Downstream From: PRD.md

## 1. Pipeline Execution Stages
1. **Stage 0:** Manifest Preflight & Checksums (SHA-256 validation against `manifest.json`).
2. **Stage 1:** Streaming Source Parsers into `staging_claims.db`.
3. **Stage 2:** Canonical Normalization (NFC, case-folding, POS canonicalization).
4. **Stage 3:** Entity Resolution & Attestation Gate (Deterministic UUIDv5 assignment).
5. **Stage 4:** Morphology Build & Separation (Strict isolation of `HAS_FORM` vs `DERIVED_FROM`).
6. **Stage 5:** Controlled Inference Engine (Restricted derivation candidate generation).
7. **Stage 6:** Claim Resolution & Conflict Marking (Preserve competing assertions).
8. **Stage 7:** Quality Gates A-G.
9. **Stage 8:** SQLite Compilation & Indexing (`lexical_graph.db` with FTS5).

## 2. Mandatory Quality Gates
- **Gate A (Source Integrity):** Manifest SHA-256 match; zero unhandled parse errors.
- **Gate B (Ontology Integrity):** Zero foreign key orphans; no unmapped POS tags.
- **Gate C (Morphology Baseline):** Benchmark words pass (`go -> went`, `mouse -> mice`, `run -> running`, `fast -> faster -> fastest`).
- **Gate D (False-Positive Regression):** Traps verified disconnected (`go ≠ goal`, `ride ≠ riddance`, `art ≠ article`, `car ≠ carpet`).
- **Gate E (Provenance Completeness):** 100% of visible non-derived relations trace to a supporting claim.
- **Gate F (Search Integrity):** Exact search <50ms; autocomplete <100ms.
- **Gate G (Performance Bounds):** All graph queries ($D \le 3$) execute in $<250$ms.
