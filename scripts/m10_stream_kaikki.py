import json
import sqlite3
import time

def ingest_kaikki():
    start = time.time()
    db_path = "data/staging/staging_claims.db"
    jsonl_path = "data/raw/kaikki.org-dictionary-English.jsonl"
    
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    
    batch = []
    total = 0
    t0 = time.time()
    
    print("INFO | Starting Kaikki 3.06GB JSONL streaming ingestion...")
    with open(jsonl_path, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            entry = json.loads(line)
            word = entry.get("word")
            pos = entry.get("pos")
            if not word or not pos:
                continue
                
            source_id = f"kaikki:{word}:{pos}"
            batch.append((source_id, word, pos, line.strip(), "KAIKKI"))
            
            if len(batch) >= 20000:
                cur.executemany("""
                    INSERT OR IGNORE INTO staging_lexical_entries 
                    (source_id, lemma, pos, raw_payload, source) 
                    VALUES (?, ?, ?, ?, ?)
                """, batch)
                total += len(batch)
                batch.clear()
                if total % 100000 == 0:
                    print(f"[{total:,} entries] Ingested ({time.time() - t0:.2f}s)")
                    t0 = time.time()

        if batch:
            cur.executemany("""
                INSERT OR IGNORE INTO staging_lexical_entries 
                (source_id, lemma, pos, raw_payload, source) 
                VALUES (?, ?, ?, ?, ?)
            """, batch)
            total += len(batch)

    conn.commit()
    cur.execute("SELECT COUNT(*) FROM staging_lexical_entries WHERE source = 'KAIKKI';")
    kaikki_count = cur.fetchone()[0]
    conn.close()
    
    duration = time.time() - start
    print(f"PASS | Kaikki Ingested: {kaikki_count} unique entries | Total Duration: {duration:.2f}s")

if __name__ == "__main__":
    ingest_kaikki()
