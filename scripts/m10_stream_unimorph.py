import fileinput
import sqlite3
import time

def ingest_unimorph():
    start = time.time()
    db_path = "data/staging/staging_claims.db"
    src_path = "data/raw/eng.unimorph"
    
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    
    batch = []
    total = 0
    with fileinput.input(files=[src_path, "data/sources/unimorph_eng.tsv"], openhook=fileinput.hook_encoded("utf-8")) as f:
        for line in f:
            parts = line.strip().split("\t")
            if len(parts) != 3:
                continue
            lemma, form, features = parts
            # Extract basic POS from feature bundle if present
            pos = "V" if "V;" in features or features.startswith("V") else ("N" if "N;" in features or features.startswith("N") else "ADJ")
            batch.append((lemma, form, pos, features, "UNIMORPH"))
            if len(batch) >= 50000:
                cur.executemany("INSERT INTO staging_inflections (lemma, form, pos, features, source) VALUES (?, ?, ?, ?, ?)", batch)
                total += len(batch)
                batch.clear()
        if batch:
            cur.executemany("INSERT INTO staging_inflections (lemma, form, pos, features, source) VALUES (?, ?, ?, ?, ?)", batch)
            total += len(batch)

    conn.commit()
    conn.close()
    duration = time.time() - start
    print(f"PASS | UniMorph Ingested: {total} inflections | Duration: {duration:.2f}s")

if __name__ == "__main__":
    ingest_unimorph()
