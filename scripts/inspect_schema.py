import sqlite3, os

db = "lexical_graph.db" if os.path.exists("lexical_graph.db") else "data/lexical_graph.db"
conn = sqlite3.connect(db)
cursor = conn.cursor()

tables = cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'").fetchall()
for (tbl,) in tables:
    cols = [col[1] for col in cursor.execute(f"PRAGMA table_info({tbl})").fetchall()]
    count = cursor.execute(f"SELECT count(*) FROM {tbl}").fetchone()[0]
    print(f"Table: {tbl} ({count} rows) -> Columns: {cols}")
