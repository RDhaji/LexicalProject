CREATE TABLE IF NOT EXISTS errata_queue (
    id TEXT PRIMARY KEY,
    target_entity_id TEXT NOT NULL,
    target_lemma TEXT NOT NULL,
    conflict_type TEXT NOT NULL CHECK (conflict_type IN ('UNRESOLVED_CLAIM', 'MISSING_ETYMOLOGY', 'AMBIGUOUS_POS', 'DUPLICATE_EDGE')),
    source_a_claim TEXT NOT NULL,
    source_b_claim TEXT,
    epistemic_class TEXT NOT NULL DEFAULT 'UNCERTAIN' CHECK (epistemic_class IN ('EXPLICIT', 'GENERATED', 'ATTESTED', 'INFERRED', 'UNCERTAIN', 'CONFLICTING')),
    metadata TEXT DEFAULT '{}',
    status TEXT NOT NULL DEFAULT 'PENDING' CHECK (status IN ('PENDING', 'RESOLVED_CONFLICT_PRESERVED', 'RESOLVED_UNATTESTED', 'SKIPPED')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    resolved_at TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_errata_queue_lemma ON errata_queue(target_lemma);
CREATE INDEX IF NOT EXISTS idx_errata_queue_status ON errata_queue(status);
