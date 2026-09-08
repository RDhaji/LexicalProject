import sqlite3, uuid

db = sqlite3.connect('lexical_graph.db')
cur = db.cursor()

frames = [
    ('frame_self_motion', 'Self_motion', 'Entity moves under own power'),
    ('frame_motion', 'Motion', 'General entity motion'),
    ('frame_banking', 'Banking', 'Money handling institution'),
    ('frame_natural_features', 'Natural_features', 'Riverbank geological feature')
]
vclasses = [
    ('vclass_run_51_3_2', 'run-51.3.2', None),
    ('vclass_escape_51_1_1', 'escape-51.1-1', None)
]
cur.executemany("INSERT OR REPLACE INTO semantic_frames VALUES (?,?,?)", frames)
cur.executemany("INSERT OR REPLACE INTO verb_classes VALUES (?,?,?)", vclasses)

freqs = [('lex_run', 5.48), ('lex_fast', 4.85), ('lex_happy', 4.67),
         ('lex_go', 6.12), ('lex_good', 5.82), ('lex_bad', 5.15), ('lex_bank', 4.53)]
for lex_id, z in freqs:
    cur.execute("UPDATE lexemes SET frequency_zipf=?, corpus_source='SUBTLEX-US' WHERE id=?", (z, lex_id))

edge_cols = [r[1] for r in cur.execute("PRAGMA table_info(edges)").fetchall()]
edges = [
    ('lex_run', 'frame_self_motion', 'EVOKES', 'ATTESTED', 'FrameNet_v1.7'),
    ('lex_run', 'vclass_run_51_3_2', 'MEMBER_OF_CLASS', 'ATTESTED', 'VerbNet_v3.4'),
    ('lex_go', 'frame_motion', 'EVOKES', 'ATTESTED', 'FrameNet_v1.7'),
    ('lex_go', 'vclass_escape_51_1_1', 'MEMBER_OF_CLASS', 'ATTESTED', 'VerbNet_v3.4'),
    ('lex_bank', 'frame_banking', 'EVOKES', 'CONFLICTING', 'FrameNet_v1.7_Sense1'),
    ('lex_bank', 'frame_natural_features', 'EVOKES', 'CONFLICTING', 'FrameNet_v1.7_Sense2')
]
for src, tgt, rel, epistemic, prov in edges:
    eid = f"edge_{uuid.uuid4().hex[:8]}"
    cur.execute(f"INSERT OR REPLACE INTO edges ({','.join(edge_cols)}) VALUES ({','.join(['?']*len(edge_cols))})",
                [eid, src, tgt, rel, epistemic, prov][:len(edge_cols)])

db.commit()
db.close()
