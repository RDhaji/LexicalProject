# ADR-012: Attested Phonetic Retrieval and Search Indexing Layer

## Status
APPROVED

## Context
The current production query engine provides exact, prefix, and FTS5 full-text search over canonical lexemes and surface forms. Users querying based on phonetic approximation or auditory memory cannot locate entries when orthographic spelling diverges significantly from pronunciation. A phonological retrieval mechanism is required while strictly upholding epistemic provenance and graph invariants.

## Decision
1. **Attested Pronunciation Entity**:
   - Introduce `PRONUNCIATION` entity linked via relation `HAS_PRONUNCIATION` to target `FORMS` (surface realization) or `LEXEMES` (lemma citation form).
   - Core attributes: `id` (UUIDv5), `target_id` (UUIDv5), `target_type` ('LEXEME' | 'FORM'), `notation` ('IPA' | 'ARPABET'), `transcription` (TEXT), `variety` (TEXT, e.g., 'en-US', 'en-GB'), `epistemic_class` ('ATTESTED' | 'EXPLICIT'), `provenance_id` (TEXT).
   - Unattested pronunciations MUST remain `NULL` (Invariant 2).
2. **Decoupled Phonetic Search Projection**:
   - Create auxiliary search index table `search_phonetic_index` (`phonetic_key`, `target_id`, `target_type`, `algorithm`).
   - Derived indexing algorithms: Double Metaphone and Soundex keys marked under epistemic class `GENERATED`.
3. **Invariant Governance**:
   - **Invariant 4 (No Heuristic Relationships)**: Phonetic indexing keys exist exclusively in `search_phonetic_index` for query projection. Phonetic similarity MUST NEVER generate graph edges (`DERIVED_FROM`, `RELATED_TO`, or cognate links).
   - **Invariant 6 (Form/Lexeme Separation)**: Pronunciations of inflected variants link strictly to `forms.id`. Lemma base pronunciations link to `lexemes.id`.
   - **Invariant 7 (Workspace Isolation)**: Schema additions reside entirely within `lexical_graph.db`. Zero foreign key references in `user_workspace.db`.

## Consequences
- Requires updating `ONTOLOGY.md` to define `PRONUNCIATION` entity and `HAS_PRONUNCIATION` edge (Escalation Trigger 1).
- Requires DDL migration `scripts/migrations/010_phonetic_layer.sql`.
- Fixture validation required across the 7 vertical slices (`run`, `fast`, `happy`, `go`, `good`, `bad`, `bank`).
