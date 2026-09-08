# AI Engineering Rules & Governance Protocols
Version: 1.0.0
Status: LOCKED
Downstream From: PRD.md

## 1. Absolute Invariants (DO NOT)
1. DO NOT modify `ONTOLOGY.md` without an approved Architecture Decision Record (ADR).
2. DO NOT invent linguistic facts, definitions, or etymologies. Missing data must be recorded as NULL or UNATTESTED.
3. DO NOT silently resolve or overwrite conflicting source claims. Preserve both claims and mark the relation UNCERTAIN or CONFLICTING.
4. DO NOT generate relationships based on string overlaps, substring matching, or edit distance (e.g., car ≠ carpet, art ≠ article).
5. DO NOT invert algorithmic stemmers (Porter, Snowball, Krovetz) into generative morphology engines.
6. DO NOT conflate Lexemes with Forms, or Inflection (HAS_FORM) with Derivation (DERIVED_FROM). Forms never instantiate Lexemes.
7. DO NOT place foreign keys in `user_workspace.db` referencing `lexical_graph.db`.
8. DO NOT bypass Quality Gates A through G or weaken test assertions.

## 2. Operational & Token Preservation Protocols
1. Zero Conversational Fluff: Start directly with actionable code or findings in sentence 1.
2. No In-Chat Script Dumping: Write scripts directly to disk files using concise shell execution commands.
3. Concise Execution Reporting: Output only pass/fail counts, execution duration, and key anomalies.
4. Vertical-Slice Priority: Always validate pipelines end-to-end on the small fixture dataset (`run`, `fast`, `happy`, `go`, `good`, `bad`, `bank`) before attempting full dataset ingests.

## 3. Mandatory Human Escalation Triggers
Execution MUST HALT and request user direction when:
1. A proposed change alters an entity or relation definition in `ONTOLOGY.md`.
2. A source dataset license is ambiguous or incompatible with redistribution.
3. Two authoritative sources materially conflict with no documented tie-breaking rule.
4. A relation cannot be definitively classified into the allowed epistemic classes (EXPLICIT, GENERATED, ATTESTED, INFERRED, UNCERTAIN, VALIDATED_RULE).
5. A proposed database migration would destroy non-reconstructible user data.
6. A performance optimization proposal sacrifices provenance or explainability.
7. A linguistic rule produces a false-positive rate > 0.1% on a regression suite.
8. An ingestion run causes an unexpected graph node or edge variance > 15%.
