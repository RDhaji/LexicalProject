# ADR-008: Decoupled Construction Layer Realization (`REALIZES` Edges)

## Status
APPROVED (Sign-off granted 2026-09-07T21:30:00Z)

## Context
Per ADR-004, constructional patterns must exist independently of concrete lexemes. Realizing these patterns requires a formal relation linking lexical units to abstract constructions without conflating forms, lexemes, or derivations (Invariant 6).

## Decision
1. Introduce entity type `CONSTRUCTION` to capture schematic pairings of form and meaning.
2. Introduce directed edge `REALIZES` (`LEXEME` | `FORM` -> `CONSTRUCTION`).
3. Enforce epistemic class partitioning (`EXPLICIT`, `GENERATED`, `ATTESTED`, `INFERRED`, `UNCERTAIN`).
4. Invariant adherence:
   - Invariant 4: No realization generation via substring, edit distance, or string overlap.
   - Invariant 6: `REALIZES` does not replace or mutate `HAS_FORM` (inflection) or `DERIVED_FROM` (derivation).
   - Invariant 7: All `CONSTRUCTION` nodes and `REALIZES` edges reside strictly in `lexical_graph.db`.

## Consequences
- Requires updating `ONTOLOGY.md` and `lexical_graph.db` DDL upon formal user approval.
- Preserves full provenance and zero cross-database foreign key contamination.
