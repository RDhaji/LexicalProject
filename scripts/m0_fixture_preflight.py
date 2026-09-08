import sqlite3
import json

FIXTURES = ["run", "fast", "happy", "go", "good", "bad", "bank"]

def run_preflight():
    conn = sqlite3.connect("data/staging/staging_claims.db")
    cur = conn.cursor()
    
    missing_kaikki = []
    missing_unimorph = []
    missing_synsets = []
    
    for f in FIXTURES:
        cur.execute("SELECT COUNT(*) FROM raw_lexical_entries WHERE lemma = ?;", (f,))
        if cur.fetchone()[0] == 0:
            missing_kaikki.append(f)
            
        cur.execute("SELECT COUNT(*) FROM raw_inflections WHERE lemma = ?;", (f,))
        if cur.fetchone()[0] == 0:
            missing_unimorph.append(f)
            
        cur.execute("SELECT COUNT(*) FROM synsets WHERE members LIKE ?;", (f'%"{f}"%',))
        if cur.fetchone()[0] == 0:
            missing_synsets.append(f)

    conn.close()

    print(f"M0 Audit: Kaikki missing: {missing_kaikki}")
    print(f"M0 Audit: UniMorph missing: {missing_unimorph}")
    print(f"M0 Audit: Synsets missing: {missing_synsets}")
    
    if missing_kaikki or missing_unimorph or missing_synsets:
        print("FAIL | Fixture dataset scaffolding incomplete across staging sources.")
    else:
        print("PASS | All 7 fixture lemmas present across all staging sources.")

if __name__ == "__main__":
    run_preflight()
