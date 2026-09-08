// Strictly typed ontological interfaces mapping ONTOLOGY.md and compiled SQLite schema

export type PosType = 
  | 'NOUN' | 'VERB' | 'ADJECTIVE' | 'ADVERB' | 'PRONOUN' 
  | 'DETERMINER' | 'PREPOSITION' | 'CONJUNCTION' | 'INTERJECTION' 
  | 'AUXILIARY' | 'NUMERAL' | 'PARTICLE' | 'OTHER';

export type EpistemicClass = 
  | 'EXPLICIT' | 'GENERATED' | 'ATTESTED' | 'INFERRED' | 'UNCERTAIN';

export interface Lexeme {
  id: string;
  lemma: string;
  normalized_lemma: string;
  language: string;
  pos: PosType;
  lexeme_key: string;
  source_presence: string[];
  frequency_summary: {
    zipf?: number;
    per_million?: number;
    raw_count?: number;
  };
  status: 'CANONICAL' | 'PROVISIONAL' | 'DEPRECATED';
}

export interface Form {
  id: string;
  surface: string;
  normalized_surface: string;
  script: string;
  language: string;
  phonemic_ipa: string | null;
  phonetic_ipa: string | null;
  features_json: Record<string, string>;
  form_type: 'BASE' | 'INFLECTED' | 'IRREGULAR' | 'SUPPLETIVE' | 'ANALYTIC';
  source: string;
  evidence: EpistemicClass;
  confidence: number;
}

export interface Sense {
  id: string;
  lexeme_id: string;
  synset_id: string | null;
  definition: string;
  usage_examples: string[];
  domain: string | null;
  register: string | null;
  source: string;
  source_sense_id: string | null;
  confidence: number;
}

export interface Relation {
  id: string;
  subject_type: string;
  subject_id: string;
  relation_type: string;
  object_type: string;
  object_id: string;
  evidence_type: EpistemicClass;
  confidence: number;
  resolution_status: string;
}

export interface Claim {
  id: string;
  source_id: string;
  subject_type: string;
  subject_id: string;
  predicate: string;
  object_type: string;
  object_id: string;
  raw_assertion: Record<string, any>;
  evidence_type: EpistemicClass;
  extraction_confidence: number;
}

export interface GraphTraversalResult {
  nodes: Lexeme[];
  edges: Relation[];
}
