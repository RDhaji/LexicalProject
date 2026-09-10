import os, sqlite3, shutil

root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
dist_dir = os.path.join(root, "data", "distribution")
os.makedirs(dist_dir, exist_ok=True)

lex_db = os.path.join(dist_dir, "lexical_graph.db")
user_db = os.path.join(dist_dir, "user_workspace.db")
slice_db = os.path.join(dist_dir, "fixture_slice.db")

# Seed lexical_graph.db from fixture_slice.db if production DB is omitted from git checkout
if not os.path.exists(lex_db) and os.path.exists(slice_db):
    shutil.copyfile(slice_db, lex_db)
elif not os.path.exists(lex_db):
    conn = sqlite3.connect(lex_db)
    conn.execute("CREATE TABLE lexemes (id TEXT PRIMARY KEY, lemma TEXT NOT NULL, pos TEXT NOT NULL, language TEXT NOT NULL);")
    conn.execute("CREATE TABLE forms (id TEXT PRIMARY KEY, form TEXT NOT NULL, language TEXT NOT NULL);")
    conn.execute("CREATE TABLE edges (id TEXT PRIMARY KEY, source_id TEXT NOT NULL, target_id TEXT NOT NULL, relation_type TEXT NOT NULL, epistemic_status TEXT NOT NULL, features TEXT, provenance TEXT NOT NULL);")
    conn.execute("CREATE TABLE pronunciations (id TEXT PRIMARY KEY, target_id TEXT NOT NULL, target_type TEXT NOT NULL, notation TEXT NOT NULL, transcription TEXT NOT NULL, variety TEXT NOT NULL, epistemic_class TEXT NOT NULL, provenance_id TEXT NOT NULL);")
    conn.commit()
    conn.close()

# Enforce Invariant 7: isolated user_workspace.db with no external FKs
if not os.path.exists(user_db):
    u_conn = sqlite3.connect(user_db)
    u_conn.execute("CREATE TABLE user_notes (id TEXT PRIMARY KEY, note TEXT NOT NULL, created_at INTEGER);")
    u_conn.execute("CREATE TABLE user_bookmarks (id TEXT PRIMARY KEY, item_id TEXT NOT NULL, created_at INTEGER);")
    u_conn.commit()
    u_conn.close()

print("CI databases initialized successfully.")
