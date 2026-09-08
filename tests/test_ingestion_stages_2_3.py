import os
import sys
import unittest
import uuid
import json

# Ensure project root is present in sys.path regardless of execution context
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from ingestion.stages_2_3 import (
    normalize_text,
    canonicalize_pos,
    canonicalize_features,
    resolve_lexeme_id,
    resolve_form_id,
    resolve_sense_id,
    NAMESPACE_LEXICAL
)

class TestIngestionStages2And3(unittest.TestCase):

    def test_stage_2_unicode_nfc_and_casefold(self):
        decomposed = "re\u0301sume\u0301"
        precomposed = "\u00e9cole"
        self.assertEqual(normalize_text(decomposed), "résumé")
        self.assertEqual(normalize_text("  RUNNING  "), "running")
        self.assertEqual(normalize_text(precomposed), "école")

    def test_stage_2_pos_canonicalization(self):
        self.assertEqual(canonicalize_pos("noun"), "NOUN")
        self.assertEqual(canonicalize_pos("v"), "VERB")
        self.assertEqual(canonicalize_pos("ADJ"), "ADJECTIVE")
        self.assertEqual(canonicalize_pos("adverb"), "ADVERB")
        self.assertEqual(canonicalize_pos("unknown_pos"), "OTHER")

    def test_stage_2_features_canonicalization(self):
        f1 = {"number": "PL", "person": "3"}
        f2 = {"person": "3", "number": "PL"}
        self.assertEqual(canonicalize_features(f1), canonicalize_features(f2))

    def test_stage_3_deterministic_lexeme_resolution(self):
        id1, key1 = resolve_lexeme_id("Run", "verb")
        id2, key2 = resolve_lexeme_id("  run  ", "v")
        self.assertEqual(id1, id2)
        self.assertEqual(key1, "eng:run:VERB")
        self.assertEqual(id1, str(uuid.uuid5(NAMESPACE_LEXICAL, "eng:run:VERB")))

        id_noun, key_noun = resolve_lexeme_id("run", "noun")
        self.assertNotEqual(id1, id_noun)

    def test_stage_3_deterministic_form_resolution(self):
        feat_json = canonicalize_features({"tense": "PST", "aspect": "PRF"})
        f_id1, f_key1 = resolve_form_id("went", feat_json)
        f_id2, f_key2 = resolve_form_id("  WENT  ", feat_json)
        self.assertEqual(f_id1, f_id2)

        l_id, _ = resolve_lexeme_id("went", "verb")
        self.assertNotEqual(f_id1, l_id)

    def test_stage_3_deterministic_sense_resolution(self):
        _, lex_key = resolve_lexeme_id("bank", "noun")
        s_id1, s_key1 = resolve_sense_id(lex_key, "bank%1:17:00::")
        s_id2, s_key2 = resolve_sense_id(lex_key, "bank%1:17:00::")
        self.assertEqual(s_id1, s_id2)
        self.assertIn("eng:bank:NOUN:sense:bank%1:17:00::", s_key1)

if __name__ == "__main__":
    unittest.main()
