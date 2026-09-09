# ADR-010: Gated Evolution Protocol & Invariant Baseline Verification
**Status**: APPROVED
**Date**: 2026-09-08
**Context**: Transition from steady-state maintenance to evolutionary expansion governed strictly by PRD.md -> ONTOLOGY.md -> ARCHITECTURE.md -> AI_ENGINEERING_RULES.md.
**Decision**:
1. Limit recognized entities and relations strictly to the locked ONTOLOGY.md schema (Core Entities 1.1-1.8, Secondary Extensions, and Relations listed in Section 2).
2. Restrict all data ingestion to authoritative sources (OEWN_2025, WIKTIONARY_KAIKKI_20260805, UNIMORPH_ENG, SUBTLEX_US_R1) with full license compliance. CELEX2 remains restricted reference-only.
3. Enforce the closed 5-class epistemic enum (EXPLICIT, GENERATED, ATTESTED, INFERRED, UNCERTAIN) per PRD.md, where UNCERTAIN denotes that evidence is ambiguous, insufficient, or lacks the corroboration required for a stronger epistemic classification. UUID generation is treated strictly as an identity mechanism, and conflict metadata is handled separately via CONFLICTING status/tags and is never used as an epistemic class.
4. Schema migrations remain gated by ADR verification; zero DDL changes without passing Gates A through G and Invariants 1-8.
**Consequences**: Eliminates epistemic drift, maintains deterministic identity, and preserves full cross-DB isolation (Invariant 7).
