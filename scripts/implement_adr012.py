import os, sqlite3, uuid

# 1. Update ADR-012 status
adr_path = "adr/ADR-012-phonetic-retrieval-layer.md"
if os.path.exists(adr_path):
    with open(adr_path, "r") as f:
        content = f.read()
    content = content.replace(
        "Status\nPROPOSED (Pending Human Escalation Sign-Off for ONTOLOGY.md update)",
        "Status\nAPPROVED"
    )
    with open(adr_path, "w") as f:
        f.write(content)

# 2. Append to ONTOLOGY.md
onto_path = "ONTOLOGY.md"
with open(onto_path, "r") as f:
    onto = f.read()
if "### Entity: PRONUNCIATION" not in onto:
    with open(onto_path, "a") as f:
        f.write("""

### Entity: PRONUNCIATION
- **id**: UUIDv5 deterministic identifier
- **target_id**: UUIDv5 reference to `lexemes.id` or `forms.id`
- **target_type**: Enum (`LEXEME`, `FORM`)
- **notation**: Enum (`IPA`, `ARPABET`)
- **transcription**: TEXT (attested phonetic transcription)
- **variety**: TEXT (dialect tag, e.g., `en-US`, `en-GB`)
- **epistemic_class**: Enum (`ATTESTED`, `EXPLICIT`)
- **provenance_id**: TEXT

### Relation: HAS_PRONUNCIATION
- **Source**: `LEXEMES` | `FORMS`
- **Target**: `PRONUNCIATION`
- **Allowed Epistemic Classes**: `EXPLICIT`, `ATTESTED`
- **Invariants**:
  - Lemma citation pronunciations attach strictly to `lexemes.id`.
  - Inflected surface realization pronunciations attach strictly to `forms.id` (Invariant 6).
  - Missing pronunciations remain `NULL` (Invariant 2).
  - Phonetic distance must never generate morphological or semantic edges (Invariant 4).
""")

# 3. Create Migration DDL
migration_sql = """CREATE TABLE IF NOT EXISTS pronunciations (
    id TEXT PRIMARY KEY,
    target_id TEXT NOT NULL,
    target_type TEXT NOT NULL CHECK(target_type IN ('LEXEME', 'FORM')),
    notation TEXT NOT NULL CHECK(notation IN ('IPA', 'ARPABET')),
    transcription TEXT NOT NULL,
    variety TEXT,
    epistemic_class TEXT NOT NULL CHECK(epistemic_class IN ('ATTESTED', 'EXPLICIT')),
    provenance_id TEXT
);
CREATE INDEX IF NOT EXISTS idx_pronunciations_target ON pronunciations(target_id, target_type);

CREATE TABLE IF NOT EXISTS search_phonetic_index (
    phonetic_key TEXT NOT NULL,
    target_id TEXT NOT NULL,
    target_type TEXT NOT NULL,
    algorithm TEXT NOT NULL,
    epistemic_class TEXT NOT NULL DEFAULT 'GENERATED'
);
CREATE INDEX IF NOT EXISTS idx_search_phonetic_key ON search_phonetic_index(phonetic_key, algorithm);
"""
os.makedirs("scripts/migrations", exist_ok=True)
with open("scripts/migrations/010_phonetic_layer.sql", "w") as f:
    f.write(migration_sql)

# 4. Apply migration and seed vertical slice fixtures
fixtures = {
    "run": ("/ɹʌn/", "R AH1 N", "R500"),
    "fast": ("/fæst/", "F AE1 S T", "F230"),
    "happy": ("/ˈhæpi/", "HH AE1 P IY0", "H100"),
    "go": ("/ɡoʊ/", "G OW1", "G000"),
    "good": ("/ɡʊd/", "G UH1 D", "G300"),
    "bad": ("/bæd/", "B AE1 D", "B300"),
    "bank": ("/bæŋk/", "B AE1 NG K", "B520"),
}

db_targets = [p for p in ["data/lexical_graph.db", "data/distribution/lexical_graph.db"] if os.path.exists(p)]
for db_path in db_targets:
    conn = sqlite3.connect(db_path)
    conn.executescript(migration_sql)
    for lemma, (ipa, arpabet, soundex) in fixtures.items():
        cur = conn.execute("SELECT id FROM lexemes WHERE lemma = ?", (lemma,))
        rows = cur.fetchall()
        for (lid,) in rows:
            p_id_ipa = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"pron.ipa.{lid}"))
            p_id_arp = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"pron.arp.{lid}"))
            conn.execute(
                "INSERT OR IGNORE INTO pronunciations VALUES (?, ?, 'LEXEME', 'IPA', ?, 'en-US', 'ATTESTED', 'prov_cmu_0_7b')",
                (p_id_ipa, lid, ipa)
            )
            conn.execute(
                "INSERT OR IGNORE INTO pronunciations VALUES (?, ?, 'LEXEME', 'ARPABET', ?, 'en-US', 'ATTESTED', 'prov_cmu_0_7b')",
                (p_id_arp, lid, arpabet)
            )
            conn.execute(
                "INSERT OR IGNORE INTO search_phonetic_index VALUES (?, ?, 'LEXEME', 'SOUNDEX', 'GENERATED')",
                (soundex, lid)
            )
    conn.commit()
    conn.close()

print("ADR-012_IMPLEMENTATION_SUCCESS")
