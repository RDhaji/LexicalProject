# ADR-009: Integration of Secondary Lexical Sources (VerbNet, FrameNet, Frequency Distributions)

## Status
PROPOSED (Awaiting User Sign-Off under Escalation Trigger 1 & 2)

## Context
To enrich graph depth beyond core Princeton WordNet and Wiktionary relations, secondary semantic layers (VerbNet classes/thematic roles, FrameNet semantic frames, and corpus frequency metadata) must be integrated without compromising provenance or structural boundaries.

## Decision
1. Introduce entity types:
   - `SEMANTIC_FRAME` (FrameNet frame representations).
   - `VERB_CLASS` (VerbNet hierarchical classes and thematic roles).
2. Introduce relations:
   - `EVOKES` (`LEXEME` -> `SEMANTIC_FRAME`).
   - `MEMBER_OF_CLASS` (`LEXEME` -> `VERB_CLASS`).
3. Add frequency metadata attributes to `LEXEME` (`frequency_zipf`, `corpus_source`) with explicit provenance. Missing frequency values must remain `NULL`.
4. Invariant Enforcement:
   - Invariant 1: No schema or ontology changes applied prior to approved ADR sign-off.
   - Invariant 2 & 3: Conflicting frame assignments between sources preserved as `UNCERTAIN` / `CONFLICTING`. Unmapped fixtures marked `UNATTESTED`.
   - Invariant 4: No lemma-to-frame matching via substring, string overlap, or edit distance.
   - Invariant 7: All new entities and edges reside strictly in `lexical_graph.db`; zero foreign keys in `user_workspace.db`.

## Consequences
- Requires updating `ONTOLOGY.md` and executing DDL migration on `lexical_graph.db` upon approval.
- Preserves full provenance and zero cross-DB schema coupling.
