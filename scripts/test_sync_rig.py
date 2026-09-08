import sqlite3, sys, time

SCHEMA = """
CREATE TABLE IF NOT EXISTS workspace_items (
    id TEXT PRIMARY KEY, lemma_ref TEXT NOT NULL,
    data TEXT, updated_at INTEGER NOT NULL, deleted_at INTEGER
);
CREATE TABLE IF NOT EXISTS sync_revisions (
    client_id TEXT, item_id TEXT, rev_id INTEGER,
    PRIMARY KEY(client_id, item_id)
);
CREATE TABLE IF NOT EXISTS sync_tombstones (
    item_id TEXT PRIMARY KEY, deleted_at INTEGER NOT NULL, rev_id INTEGER NOT NULL
);
"""

def run_sync_rig():
    c_a, c_b = sqlite3.connect(":memory:"), sqlite3.connect(":memory:")
    for c in (c_a, c_b): c.executescript(SCHEMA)
    ts = int(time.time())

    # Client A creates item referencing fixture lemma 'run' (by scalar string, no FK)
    c_a.execute("INSERT INTO workspace_items VALUES ('i1', 'run', 'note-a', ?, NULL)", (ts,))
    c_a.execute("INSERT INTO sync_revisions VALUES ('dev-a', 'i1', 1)")

    # Client B receives item, then issues tombstone deletion at rev 2
    c_b.execute("INSERT INTO workspace_items VALUES ('i1', 'run', 'note-a', ?, NULL)", (ts,))
    c_b.execute("INSERT INTO sync_tombstones VALUES ('i1', ?, 2)", (ts + 10,))
    c_b.execute("UPDATE workspace_items SET deleted_at = ? WHERE id = 'i1'", (ts + 10,))

    # Emulate convergence sync B -> A
    tb = c_b.execute("SELECT item_id, deleted_at, rev_id FROM sync_tombstones WHERE item_id = 'i1'").fetchone()
    rev_a = c_a.execute("SELECT rev_id FROM sync_revisions WHERE item_id = 'i1'").fetchone()[0]
    if tb[2] > rev_a:
        c_a.execute("UPDATE workspace_items SET deleted_at = ? WHERE id = ?", (tb[1], tb[0]))

    # Verify convergence & Invariant 7 isolation
    assert c_a.execute("SELECT deleted_at FROM workspace_items WHERE id = 'i1'").fetchone()[0] is not None, "Tombstone failed"
    for c in (c_a, c_b):
        for tbl in ('workspace_items', 'sync_revisions', 'sync_tombstones'):
            assert not c.execute(f"PRAGMA foreign_key_list({tbl})").fetchall(), "Invariant 7 violation: Foreign key found"
    print("[SYNC RIG OK] Emulated multi-device sync, tombstone handling, and Invariant 7 verified.")

if __name__ == "__main__":
    run_sync_rig()
