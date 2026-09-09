# ADR-011: Secondary Source Ingestion Pipeline Refinement
**Status**: APPROVED
**Date**: 2026-09-09
**Context**: Refinement of secondary lexical ingestion pipelines (WIKTIONARY_KAIKKI_20260805, UNIMORPH_ENG) to tighten provenance tracking, enforce strict inflectional feature mapping, and eliminate parse ambiguities without violating Invariants 1-8.
**Decision**:
1. Limit ingested morphology strictly to attested paradigms present in source payloads; forbid generative extrapolation (Invariant 2, 5).
2. Retain separate claims for conflicting POS tags, glosses, or inflectional paradigms, marking divergent relations as UNCERTAIN or CONFLICTING with full source provenance (Invariant 3).
3. Enforce strict separation between Lexemes and Forms during stage 6 claim resolution: all inflection mappings must resolve exclusively to Form entities via HAS_FORM, preserving root Lexeme identity (Invariant 6).
4. Restrict all output to the locked schema of lexical_graph.db with zero cross-database references to user_workspace.db (Invariant 7).
5. Require passing the 7-fixture regression suite (`run`, `fast`, `happy`, `go`, `good`, `bad`, `bank`) before committing pipeline changes (Invariant 8).
**Consequences**: Guarantees deterministic provenance for secondary lexical entries, prevents schema/data drift, and preserves epistemic integrity across the graph.
