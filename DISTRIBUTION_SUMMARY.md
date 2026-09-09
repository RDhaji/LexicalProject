# Final System Distribution Summary

## Release Artifacts
- **Version**: 1.0.0
- **Production Database**: `dist/data/lexical_graph.db`
- **SHA-256**: `764c1f2b9c59b7ee56cd10b98de12059a61c4d70c023e13c4948084883aefa65`
- **Byte Size**: 1219399680 bytes

## Graph Topologies & Projections
- **Canonical English Lexemes**: 1,832,881
- **Inflected Forms**: 1,177,331
- **Synsets**: 107,537
- **Morphological Edges**: 2,233,655
- **Semantic Edges**: 114,616
- **Phonetic Pronunciations (ADR-012)**: 90
- **Spanish Pilot Lexemes (ADR-013)**: 7

## Verified Invariant Governance
- Invariants 1-8: Formally attested and verified via automated test fixtures.
- Latency SLA: Sub-millisecond lookup latency validated (<0.95ms vs 250ms SLA).
- Streaming Protocol: HTTP-206 byte-range partial content stream validated.
- Workspace Isolation: Invariant 7 adhered to with zero foreign keys to lexical_graph.db.
