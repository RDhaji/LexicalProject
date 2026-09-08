import sqlite3

conn = sqlite3.connect("data/staging/staging_claims.db")
cur = conn.cursor()

cur.execute("SELECT source, COUNT(*) FROM staging_lexical_entries GROUP BY source;")
entries = cur.fetchall()

cur.execute("SELECT source, COUNT(*) FROM staging_inflections GROUP BY source;")
inflections = cur.fetchall()

cur.execute("SELECT source, COUNT(*) FROM staging_semantic_relations GROUP BY source;")
semantics = cur.fetchall()

conn.close()

print("=== M10 STAGING CLAIMS AUDIT ===")
print("Entries:", entries)
print("Inflections:", inflections)
print("Semantics:", semantics)
