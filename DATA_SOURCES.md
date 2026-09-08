# Authoritative Data Sources Specification
Version: 1.0.0
Status: LOCKED
Downstream From: PRD.md

| Source Identifier | Version Baseline | Artifact Format | Primary Authority Scope | License Type |
|---|---|---|---|---|
| `OEWN_2025` | 2025 Stable | JSON / WN-LMF | Synsets, Semantic Hierarchy, Derivational Links | WordNet / CC BY 4.0 |
| `WIKTIONARY_KAIKKI_20260805` | 2026-08-05 Dump | Streaming JSONL | POS, Definitions, IPA, Etymology, Attestations | CC BY-SA 4.0 / GFDL |
| `UNIMORPH_ENG` | Master / Stable | TSV Tables | Inflectional Realizations, Grammatical Bundles | CC BY-SA 4.0 |
| `SUBTLEX_US_R1` | Release 1.0 | TSV Table | Word & Lemma Usage Frequency Ranks | Research / Educational |
| `CELEX2` | Optional Local | Restricted TSV | Morphology & Syntax Validation (NON-REDISTRIBUTABLE)| LDC License Agreement |

All ingestion operates strictly on local raw dumps with verified SHA-256 signatures stored in `data/sources/manifest.json`.
