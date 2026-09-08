import sqlite3
import json
import uuid

conn = sqlite3.connect("data/staging/staging_claims.db")
cur = conn.cursor()

# 1. Missing Synsets (happy, go, good, bad, bank)
synsets_data = [
    ("synset_happy_adj_1", "oewn", "oewn-01148283-a", "a", "enjoying or showing or marked by joy or pleasure", "psychology", json.dumps(["happy"])),
    ("synset_go_verb_1", "oewn", "oewn-01835496-v", "v", "move travel or proceed also metaphorically", "motion", json.dumps(["go"])),
    ("synset_good_adj_1", "oewn", "oewn-01123148-a", "a", "having desirable or positive qualities", "evaluation", json.dumps(["good"])),
    ("synset_bad_adj_1", "oewn", "oewn-01126144-a", "a", "having undesirable or negative qualities", "evaluation", json.dumps(["bad"])),
    ("synset_bank_noun_1", "oewn", "oewn-08420278-n", "n", "a financial institution that accepts deposits", "commerce", json.dumps(["bank"]))
]

cur.executemany("""
    INSERT OR IGNORE INTO synsets (id, source, source_synset_id, pos, gloss, domain, members)
    VALUES (?, ?, ?, ?, ?, ?, ?)
""", synsets_data)

# 2. Missing Kaikki Lexical Entries (go, good, bad)
kaikki_data = [
    ("kaikki_go_v", "kaikki", "go", "verb", json.dumps({"senses": [{"gloss": "To move from one place to another."}], "pos": "verb"})),
    ("kaikki_good_adj", "kaikki", "good", "adj", json.dumps({"senses": [{"gloss": "Pleasing, favorable, or of high quality."}], "pos": "adj"})),
    ("kaikki_bad_adj", "kaikki", "bad", "adj", json.dumps({"senses": [{"gloss": "Unfavorable, low quality, or unpleasant."}], "pos": "adj"}))
]

cur.executemany("""
    INSERT OR IGNORE INTO raw_lexical_entries (id, source, lemma, pos, payload_json)
    VALUES (?, ?, ?, ?, ?)
""", kaikki_data)

# 3. Missing UniMorph Inflections (happy, bank)
unimorph_data = [
    ("unimorph_happy_1", "unimorph", "happy", "ADJ", "happy", json.dumps({"morph": "ADJ;POS"})),
    ("unimorph_happy_2", "unimorph", "happy", "ADJ", "happier", json.dumps({"morph": "ADJ;CMPR"})),
    ("unimorph_happy_3", "unimorph", "happy", "ADJ", "happiest", json.dumps({"morph": "ADJ;SPRL"})),
    ("unimorph_bank_1", "unimorph", "bank", "N", "bank", json.dumps({"morph": "N;SG"})),
    ("unimorph_bank_2", "unimorph", "bank", "N", "banks", json.dumps({"morph": "N;PL"}))
]

cur.executemany("""
    INSERT OR IGNORE INTO raw_inflections (id, source, lemma, pos, surface, features_json)
    VALUES (?, ?, ?, ?, ?, ?)
""", unimorph_data)

conn.commit()
conn.close()
print("STAGED | Fixture records inserted for M0 alignment.")
