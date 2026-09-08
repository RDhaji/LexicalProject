# ADR-006: Local Compiled SQLite Database for PWA
Status: APPROVED
Date: 2026-09-04

Compile the resolved knowledge graph into an embedded SQLite database (`lexical_graph.db`) for local PWA execution using `sql.js` (WebAssembly), physically isolated from `user_workspace.db` (zero foreign keys).
