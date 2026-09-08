# System Architecture Document
Version: 1.0.0
Status: LOCKED
Downstream From: PRD.md, ONTOLOGY.md

## 1. System Topology
The platform operates as an offline-first, local-first Progressive Web App (PWA) backed by an embedded SQLite relational database compiled via an offline batch pipeline.
- `lexical_graph.db`: Read-only graph distribution containing canonical entities, relations, claims, sources, and frequency metadata.
- `user_workspace.db`: Persistent user partition storing notes, favorites, bookmarks, and custom tags. Links to lexical entities exclusively via immutable UUIDs (zero cross-database foreign keys).

## 2. Partitioning & Data Isolation Invariant (PRD §39, §63, ADR-006)
1. **Distribution Isolation:** Rebuilding `lexical_graph.db` never drops, locks, or alters `user_workspace.db`.
2. **Zero Foreign Keys:** `user_workspace.db` maintains zero SQLite foreign keys into `lexical_graph.db`.
3. **Schema Lifecycle Independence:** Migrations on the user workspace partition proceed independently of distribution updates.

## 3. The Claims vs. Relations Subsystem (ADR-002)
- **Claims Table (`claims`):** Immutable ledger preserving raw assertions directly extracted from specific source versions.
- **Relations Table (`relations`):** Resolved canonical graph edges exposed to the application.
- **Relation Claims Table (`relation_claims`):** Join table linking `relation_id` to `claim_id` with composite PK and cascading foreign keys.

## 4. Query & Traversal Engine Bounds
- Local exact match and prefix lookup powered by covering indices on `normalized_surface` and `normalized_lemma`.
- Interactive graph expansions bounded to depth $D \le 3$ (<250ms SLA).
- Full-text search supported via SQLite FTS5.
