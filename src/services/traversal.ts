import { DatabaseClient } from '../db/client';
import { Lexeme, Form, Sense, Relation, Claim, GraphTraversalResult } from '../types/lexical';

export class TraversalService {
  private client: DatabaseClient;

  constructor(client: DatabaseClient) {
    this.client = client;
  }

  /**
   * Exact match lookup via covering index on forms.normalized_surface
   */
  public lookupExact(surface: string): { form: Form; lexeme: Lexeme; senses: Sense[] }[] {
    const normalized = surface.trim().toLowerCase();
    
    const query = `
      SELECT 
        f.id AS form_id, f.surface, f.normalized_surface, f.script, f.language AS form_lang,
        f.phonemic_ipa, f.phonetic_ipa, f.features_json, f.form_type, f.source AS form_source,
        f.evidence AS form_evidence, f.confidence AS form_conf,
        l.id AS lexeme_id, l.lemma, l.normalized_lemma, l.language AS lexeme_lang,
        l.pos, l.lexeme_key, l.source_presence, l.frequency_summary, l.status
      FROM forms f
      JOIN relations r ON r.object_id = f.id AND r.relation_type = 'HAS_FORM'
      JOIN lexemes l ON l.id = r.subject_id
      WHERE f.normalized_surface = ?
    `;

    const rows = this.client.graphDb.prepare(query).all(normalized) as any[];

    const senseStmt = this.client.graphDb.prepare(`
      SELECT id, lexeme_id, synset_id, definition, usage_examples, domain, register, source, source_sense_id, confidence
      FROM senses 
      WHERE lexeme_id = ?
    `);

    return rows.map(row => {
      const senseRows = senseStmt.all(row.lexeme_id) as any[];

      return {
        form: {
          id: row.form_id,
          surface: row.surface,
          normalized_surface: row.normalized_surface,
          script: row.script,
          language: row.form_lang,
          phonemic_ipa: row.phonemic_ipa,
          phonetic_ipa: row.phonetic_ipa,
          features_json: JSON.parse(row.features_json || '{}'),
          form_type: row.form_type,
          source: row.form_source,
          evidence: row.form_evidence,
          confidence: row.form_conf
        },
        lexeme: {
          id: row.lexeme_id,
          lemma: row.lemma,
          normalized_lemma: row.normalized_lemma,
          language: row.lexeme_lang,
          pos: row.pos,
          lexeme_key: row.lexeme_key,
          source_presence: JSON.parse(row.source_presence || '[]'),
          frequency_summary: JSON.parse(row.frequency_summary || '{}'),
          status: row.status
        },
        senses: senseRows.map(s => ({
          ...s,
          usage_examples: JSON.parse(s.usage_examples || '[]')
        }))
      };
    });
  }

  /**
   * Autocomplete prefix lookup backed by index on normalized_surface
   */
  public lookupPrefix(prefix: string, limit = 10): { surface: string; lemma: string; pos: string }[] {
    const normalized = prefix.trim().toLowerCase();
    const query = `
      SELECT DISTINCT f.surface, l.lemma, l.pos
      FROM forms f
      JOIN relations r ON r.object_id = f.id AND r.relation_type = 'HAS_FORM'
      JOIN lexemes l ON l.id = r.subject_id
      WHERE f.normalized_surface >= ? AND f.normalized_surface < ? || '{'
      LIMIT ?
    `;
    return this.client.graphDb.prepare(query).all(normalized, normalized, limit) as any[];
  }

  /**
   * Bounded morphological graph expansion strictly constrained to depth D <= 3
   */
  public traverseMorphology(lexemeId: string, maxDepth = 2): GraphTraversalResult {
    const depth = Math.min(Math.max(maxDepth, 1), 3);
    const visitedNodes = new Map<string, Lexeme>();
    const collectedEdges: Relation[] = [];

    const rootLexeme = this.client.graphDb.prepare(
      'SELECT * FROM lexemes WHERE id = ?'
    ).get(lexemeId) as any;

    if (!rootLexeme) return { nodes: [], edges: [] };

    visitedNodes.set(rootLexeme.id, {
      ...rootLexeme,
      source_presence: JSON.parse(rootLexeme.source_presence || '[]'),
      frequency_summary: JSON.parse(rootLexeme.frequency_summary || '{}')
    });

    let currentLevelIds = [lexemeId];

    for (let d = 0; d < depth; d++) {
      if (currentLevelIds.length === 0) break;

      const placeholders = currentLevelIds.map(() => '?').join(',');
      const edges = this.client.graphDb.prepare(`
        SELECT id, subject_type, subject_id, relation_type, object_type, object_id, evidence_type, confidence, resolution_status
        FROM relations
        WHERE (subject_id IN (${placeholders}) OR object_id IN (${placeholders}))
          AND relation_type IN ('DERIVED_FROM', 'MORPHOLOGICALLY_RELATED')
      `).all(...currentLevelIds, ...currentLevelIds) as Relation[];

      const nextLevelIds: string[] = [];

      for (const edge of edges) {
        collectedEdges.push(edge);
        const neighborId = currentLevelIds.includes(edge.subject_id) ? edge.object_id : edge.subject_id;

        if (!visitedNodes.has(neighborId)) {
          const neighborLexeme = this.client.graphDb.prepare(
            'SELECT * FROM lexemes WHERE id = ?'
          ).get(neighborId) as any;

          if (neighborLexeme) {
            visitedNodes.set(neighborId, {
              ...neighborLexeme,
              source_presence: JSON.parse(neighborLexeme.source_presence || '[]'),
              frequency_summary: JSON.parse(neighborLexeme.frequency_summary || '{}')
            });
            nextLevelIds.push(neighborId);
          }
        }
      }

      currentLevelIds = nextLevelIds;
    }

    return {
      nodes: Array.from(visitedNodes.values()),
      edges: collectedEdges
    };
  }

  /**
   * Provenance explainability engine: traces visible edges to supporting raw claims
   */
  public explainConnection(subjectId: string, objectId: string): Claim[] {
    const query = `
      SELECT c.id, c.source_id, c.subject_type, c.subject_id, c.predicate,
             c.object_type, c.object_id, c.evidence_type, c.confidence AS extraction_confidence
      FROM relations r
      JOIN relation_claims rc ON rc.relation_id = r.id
      JOIN claims c ON c.id = rc.claim_id
      WHERE (r.subject_id = ? AND r.object_id = ?)
         OR (r.subject_id = ? AND r.object_id = ?)
    `;

    const rows = this.client.graphDb.prepare(query).all(subjectId, objectId, objectId, subjectId) as any[];
    return rows.map(r => ({
      ...r,
      raw_assertion: {}
    }));
  }
}
