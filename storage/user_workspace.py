"""
User Workspace Persistence Layer with Complete Schema Synchronization & Alias Mapping
Compliance: PRD.md Section 39, ARCHITECTURE.md Section 2, ADR-006
"""

import os
import sqlite3
import sys
import uuid
from datetime import datetime, timezone

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
WORKSPACE_DB_PATH = os.path.join(PROJECT_ROOT, "data", "user_workspace.db")

def get_workspace_conn() -> sqlite3.Connection:
    os.makedirs(os.path.dirname(WORKSPACE_DB_PATH), exist_ok=True)
    conn = sqlite3.connect(WORKSPACE_DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON;")
    init_workspace_schema(conn)
    return conn

def sync_table_columns(cursor: sqlite3.Cursor, table_name: str, required_cols: dict):
    cursor.execute(f"PRAGMA table_info({table_name});")
    existing_cols = {row[1] for row in cursor.fetchall()}
    for col_name, col_type in required_cols.items():
        if col_name not in existing_cols:
            cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN {col_name} {col_type};")

def init_workspace_schema(conn: sqlite3.Connection):
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_bookmarks (
            id TEXT PRIMARY KEY,
            entity_id TEXT NOT NULL,
            entity_type TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_notes (
            id TEXT PRIMARY KEY,
            entity_id TEXT NOT NULL,
            entity_type TEXT NOT NULL,
            note_text TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
    """)

    sync_table_columns(cursor, "user_bookmarks", {
        "entity_id": "TEXT NOT NULL DEFAULT ''",
        "entity_type": "TEXT NOT NULL DEFAULT 'LEXEME'",
        "created_at": "TEXT NOT NULL DEFAULT ''"
    })
    sync_table_columns(cursor, "user_notes", {
        "entity_id": "TEXT NOT NULL DEFAULT ''",
        "entity_type": "TEXT NOT NULL DEFAULT 'LEXEME'",
        "note_text": "TEXT NOT NULL DEFAULT ''",
        "updated_at": "TEXT NOT NULL DEFAULT ''"
    })

    cursor.execute("PRAGMA table_info(user_notes);")
    note_cols = {row[1] for row in cursor.fetchall()}
    if "entity_id" in note_cols:
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_un_entity ON user_notes(entity_id);")
    if "target_entity_id" in note_cols:
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_un_target ON user_notes(target_entity_id);")

    cursor.execute("CREATE INDEX IF NOT EXISTS idx_ub_entity ON user_bookmarks(entity_id);")
    conn.commit()

def add_bookmark(entity_id: str, entity_type: str) -> str:
    conn = get_workspace_conn()
    cursor = conn.cursor()
    b_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()

    cursor.execute("PRAGMA table_info(user_bookmarks);")
    cols = {row[1] for row in cursor.fetchall()}
    
    insert_dict = {
        "id": b_id,
        "entity_id": entity_id,
        "entity_type": entity_type,
        "created_at": now
    }
    if "target_entity_id" in cols:
        insert_dict["target_entity_id"] = entity_id
    if "target_entity_type" in cols:
        insert_dict["target_entity_type"] = entity_type
    if "target_id" in cols:
        insert_dict["target_id"] = entity_id
    if "target_type" in cols:
        insert_dict["target_type"] = entity_type
    if "target_label" in cols:
        insert_dict["target_label"] = entity_id

    active_keys = [k for k in insert_dict if k in cols]
    col_names = ", ".join(active_keys)
    placeholders = ", ".join(["?"] * len(active_keys))
    values = [insert_dict[k] for k in active_keys]

    cursor.execute(f"INSERT INTO user_bookmarks ({col_names}) VALUES ({placeholders})", values)
    conn.commit()
    conn.close()
    return b_id

def add_note(entity_id: str, entity_type: str, note_text: str) -> str:
    conn = get_workspace_conn()
    cursor = conn.cursor()
    n_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()

    cursor.execute("PRAGMA table_info(user_notes);")
    cols = {row[1] for row in cursor.fetchall()}

    insert_dict = {
        "id": n_id,
        "entity_id": entity_id,
        "entity_type": entity_type,
        "note_text": note_text,
        "updated_at": now,
        "target_id": entity_id,
        "target_type": entity_type,
        "note_title": "Note",
        "note_body": note_text,
        "created_at": now
    }
    if "target_entity_id" in cols:
        insert_dict["target_entity_id"] = entity_id
    if "target_entity_type" in cols:
        insert_dict["target_entity_type"] = entity_type
    if "target_id" in cols:
        insert_dict["target_id"] = entity_id
    if "target_type" in cols:
        insert_dict["target_type"] = entity_type
    if "target_label" in cols:
        insert_dict["target_label"] = entity_id
    if "note_content" in cols:
        insert_dict["note_content"] = note_text

    active_keys = [k for k in insert_dict if k in cols]
    col_names = ", ".join(active_keys)
    placeholders = ", ".join(["?"] * len(active_keys))
    values = [insert_dict[k] for k in active_keys]

    cursor.execute(f"INSERT INTO user_notes ({col_names}) VALUES ({placeholders})", values)
    conn.commit()
    conn.close()
    return n_id
