# ADR-002: Claims + Resolved Graph Separation
Status: APPROVED
Date: 2026-09-04

Bifurcate persistence into `claims` (immutable ledger of raw source assertions) and `relations` (resolved canonical graph edges) linked via `relation_claims`.
