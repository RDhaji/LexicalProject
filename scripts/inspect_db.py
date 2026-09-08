import os, sqlite3

db_path = "data/lexical_graph.db" if os.path.exists("data/lexical_graph.db") else "lexical_graph.db"
if not os.path.exists(db_path):
    import glob
    matches = glob.glob("**/lexical_graph.db", recursive=True)
    db_path = matches[0] if matches else db_path

print(f"Target DB: {db_path}")
conn = sqlite3.connect(db_path)
for name, sql in conn.execute("SELECT name, sql FROM sqlite_master WHERE type='table' ORDER BY name"):
    print(f"\n--- {name} ---\n{sql}")
