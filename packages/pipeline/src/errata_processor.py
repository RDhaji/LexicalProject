import sqlite3
import json
from typing import NamedTuple, Optional

class ErrataItem(NamedTuple):
    id: str
    target_entity_id: str
    target_lemma: str
    conflict_type: str
    source_a_claim: str
    source_b_claim: Optional[str]
    epistemic_class: str
    metadata: Optional[str]

def process_pending_errata(db_path: str) -> int:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT id, target_entity_id, target_lemma, conflict_type, source_a_claim, source_b_claim, epistemic_class, metadata
        FROM errata_queue
        WHERE status = 'PENDING'
    """)
    items = [ErrataItem(*row) for row in cursor.fetchall()]
    
    for item in items:
        # Invariant 3: Preserve both claims; classify relation as UNCERTAIN
        # Invariant 1: edges table adheres strictly to 5 epistemic classes without metadata column
        cursor.execute("""
            UPDATE edges 
            SET epistemic_class = 'UNCERTAIN'
            WHERE source_id = ? OR target_id = ?
        """, (item.target_entity_id, item.target_entity_id))
        
        meta = json.loads(item.metadata) if item.metadata else {}
        meta["conflict_record"] = {
            "source_a": item.source_a_claim,
            "source_b": item.source_b_claim,
            "resolved_as": "UNATTESTED" if item.conflict_type == "MISSING_ETYMOLOGY" else "CONFLICT_PRESERVED"
        }
        
        resolved_status = "RESOLVED_UNATTESTED" if item.conflict_type == "MISSING_ETYMOLOGY" else "RESOLVED_CONFLICT_PRESERVED"
        cursor.execute("""
            UPDATE errata_queue 
            SET status = ?,
                epistemic_class = 'UNCERTAIN',
                metadata = ?,
                resolved_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (resolved_status, json.dumps(meta), item.id))
        
    conn.commit()
    processed_count = len(items)
    conn.close()
    return processed_count

if __name__ == "__main__":
    db_file = "/Users/rd/Desktop/LexicalProject/data/lexical_graph.db"
    count = process_pending_errata(db_file)
    print(f"Processed {count} errata records.")
