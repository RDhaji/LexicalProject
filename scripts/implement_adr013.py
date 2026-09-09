import os
import sqlite3
import time
import uuid

migration_sql = """CREATE TABLE IF NOT EXISTS lexemes_es (
    id TEXT PRIMARY KEY,
    lemma TEXT NOT NULL UNIQUE,
    pos TEXT,
    created_at INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS forms_es (
    id TEXT PRIMARY KEY,
    form TEXT NOT NULL,
    created_at INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_lexemes_es_lemma ON lexemes_es(lemma);
CREATE INDEX IF NOT EXISTS idx_forms_es_form ON forms_es(form);
"""
os.makedirs("scripts/migrations", exist_ok=True)
with open("scripts/migrations/011_cross_lingual_layer.sql", "w") as f:
    f.write(migration_sql)

fixtures_es = {
    "run": ("correr", "VERB", "ATTESTED"),
    "fast": ("rápido", "ADJ", "ATTESTED"),
    "happy": ("feliz", "ADJ", "ATTESTED"),
    "go": ("ir", "VERB", "ATTESTED"),
    "good": ("bueno", "ADJ", "ATTESTED"),
    "bad": ("malo", "ADJ", "ATTESTED"),
    "bank": ("banco", "NOUN", "UNCERTAIN")
}

now = int(time.time())
for db_path in [p for p in ["data/lexical_graph.db", "data/distribution/lexical_graph.db"] if os.path.exists(p)]:
    conn = sqlite3.connect(db_path)
    conn.executescript(migration_sql)
    cols = {r[1] for r in conn.execute("PRAGMA table_info(edges)").fetchall()}
    status_col = "epistemic_status" if "epistemic_status" in cols else "epistemic_class"

    for en_lemma, (es_lemma, es_pos, ep_class) in fixtures_es.items():
        es_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"lex.es.{es_lemma}"))
        conn.execute(
            "INSERT OR IGNORE INTO lexemes_es (id, lemma, pos, created_at) VALUES (?, ?, ?, ?)",
            (es_id, es_lemma, es_pos, now)
        )
        for (en_id,) in conn.execute("SELECT id FROM lexemes WHERE lemma = ?", (en_lemma,)).fetchall():
            edge_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"edge.trans.{en_id}.{es_id}"))
            d = {
                "id": edge_id,
                "source_id": en_id,
                "target_id": es_id,
                "relation_type": "TRANSLATION_OF",
                status_col: ep_class,
                "provenance": "prov_apertium_dict" if "provenance" in cols else None,
                "features": "{}" if "features" in cols else None,
                "created_at": now if "created_at" in cols else None,
                "source_type": "LEXEME" if "source_type" in cols else None,
                "target_type": "LEXEME" if "target_type" in cols else None
            }
            d = {k: v for k, v in d.items() if k in cols and v is not None}
            col_names = ", ".join(d.keys())
            placeholders = ", ".join("?" for _ in d)
            conn.execute(
                f"INSERT OR IGNORE INTO edges ({col_names}) VALUES ({placeholders})",
                list(d.values())
            )
    conn.commit()
    conn.close()

print("ADR-013_SUCCESS")
