import unicodedata
import uuid
import hashlib
import json
from typing import Dict, Any, Optional, Tuple

NAMESPACE_LEXICAL = uuid.UUID("6ba7b812-9dad-11d1-80b4-00c04fd430c8")

VALID_POS = {
    "NOUN", "VERB", "ADJECTIVE", "ADVERB", "PRONOUN", "DETERMINER",
    "PREPOSITION", "CONJUNCTION", "INTERJECTION", "AUXILIARY", "NUMERAL",
    "PARTICLE", "OTHER"
}

POS_MAP = {
    "n": "NOUN", "noun": "NOUN",
    "v": "VERB", "verb": "VERB",
    "a": "ADJECTIVE", "adj": "ADJECTIVE", "adjective": "ADJECTIVE",
    "r": "ADVERB", "adv": "ADVERB", "adverb": "ADVERB",
    "pron": "PRONOUN", "pronoun": "PRONOUN",
    "det": "DETERMINER", "determiner": "DETERMINER",
    "prep": "PREPOSITION", "preposition": "PREPOSITION",
    "conj": "CONJUNCTION", "conjunction": "CONJUNCTION",
    "intj": "INTERJECTION", "interjection": "INTERJECTION"
}

def normalize_text(text: str) -> str:
    if not text:
        return ""
    nfc = unicodedata.normalize("NFC", text.strip())
    return nfc.lower()

def canonicalize_pos(raw_pos: str) -> str:
    raw_lower = raw_pos.strip().lower()
    return POS_MAP.get(raw_lower, "OTHER")

def canonicalize_features(raw_features: Dict[str, Any]) -> str:
    if not raw_features:
        return "{}"
    sorted_features = {k: sorted(v) if isinstance(v, list) else v for k, v in sorted(raw_features.items())}
    return json.dumps(sorted_features, separators=(",", ":"))

def resolve_lexeme_id(lemma: str, pos: str, lang: str = "eng") -> Tuple[str, str]:
    norm_lemma = normalize_text(lemma)
    can_pos = canonicalize_pos(pos)
    natural_key = f"{lang}:{norm_lemma}:{can_pos}"
    entity_id = str(uuid.uuid5(NAMESPACE_LEXICAL, natural_key))
    return entity_id, natural_key

def resolve_form_id(surface: str, features_json: str, lang: str = "eng") -> Tuple[str, str]:
    norm_surface = normalize_text(surface)
    feat_hash = hashlib.sha256(features_json.encode("utf-8")).hexdigest()[:12]
    natural_key = f"{lang}:{norm_surface}:{feat_hash}"
    entity_id = str(uuid.uuid5(NAMESPACE_LEXICAL, natural_key))
    return entity_id, natural_key

def resolve_sense_id(lexeme_key: str, source_sense_id: str) -> Tuple[str, str]:
    natural_key = f"{lexeme_key}:sense:{source_sense_id}"
    entity_id = str(uuid.uuid5(NAMESPACE_LEXICAL, natural_key))
    return entity_id, natural_key
