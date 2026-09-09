# ADR-013: Cross-Lingual Lexical Expansion (Spanish Pilot)

## Status
APPROVED

## Context
The lexical graph currently provides English canonical lexemes, inflections, and semantic relations. Cross-lingual alignment (beginning with a Spanish pilot) must be integrated without introducing false cognates, colliding lemma namespaces, or compromising epistemic traceability.

## Decision
1. **Cross-Lingual Relation**:
   - Introduce relation `TRANSLATION_OF` linking foreign lexical entries to canonical English lexemes.
   - Valid endpoints: Source `lexemes` <-> Target `lexemes_es` (or scoped language lexemes).
   - Valid epistemic classes: `EXPLICIT`, `ATTESTED`, `UNCERTAIN`.
2. **Lexical Partitioning**:
   - Introduce dedicated tables `lexemes_es` (`id`, `lemma`, `pos`, `created_at`) and `forms_es` (`id`, `form`, `created_at`) to eliminate orthographic collision with English lemmas (e.g., *red*, *pan*, *once*).
   - Link inflections strictly via `HAS_FORM` within the Spanish partition.
3. **Invariant Governance**:
   - **Invariant 2 & 3**: Unverified translation pairs remain NULL/UNATTESTED. Competing or polysemous senses across language boundaries without 1:1 mapping are classified as `UNCERTAIN`.
   - **Invariant 4 (No False Friends)**: Translations must be explicitly attested via authoritative bilingual sources (e.g., Apertium / OEWN ILI). Orthographic overlap or edit distance (e.g., *actual* ≠ *actual*, *éxito* ≠ *exit*) must NEVER generate edges.
   - **Invariant 6 (Form/Lexeme Separation)**: Cross-lingual relations exist exclusively at the Lexeme tier. Forms never instantiate cross-lingual edges.
   - **Invariant 7 (Workspace Isolation)**: Zero foreign keys in `user_workspace.db`.

## Consequences
- Requires updating `ONTOLOGY.md` to define `TRANSLATION_OF` relation (Escalation Trigger 1).
- Requires migration `scripts/migrations/011_cross_lingual_layer.sql`.
- Fixture verification across the 7 vertical slices:
  - `run` -> `correr`
  - `fast` -> `rápido`
  - `happy` -> `feliz`
  - `go` -> `ir`
  - `good` -> `bueno`
  - `bad` -> `malo`
  - `bank` -> `banco`
