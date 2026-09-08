class LexicalQueryService {
  constructor(db) {
    this.db = db;
  }

  _all(query, params = []) {
    return new Promise((resolve, reject) => {
      this.db.all(query, params, (err, rows) => {
        if (err) reject(err);
        else resolve(rows || []);
      });
    });
  }

  _get(query, params = []) {
    return new Promise((resolve, reject) => {
      this.db.get(query, params, (err, row) => {
        if (err) reject(err);
        else resolve(row || null);
      });
    });
  }

  async searchPrefix(prefix, limit = 20) {
    const norm = (prefix || '').normalize('NFC').trim().toLowerCase();
    if (!norm) return [];

    return await this._all(
      `SELECT l.id, l.lemma, l.pos, l.frequency_summary
       FROM lexemes l
       WHERE l.normalized_lemma LIKE ? || '%'
       ORDER BY 
         CASE 
           WHEN json_extract(l.frequency_summary, '$.tier') = 'VERY_COMMON' THEN 1
           WHEN json_extract(l.frequency_summary, '$.tier') = 'COMMON' THEN 2
           WHEN json_extract(l.frequency_summary, '$.tier') = 'LESS_COMMON' THEN 3
           ELSE 4
         END ASC,
         LENGTH(l.lemma) ASC
       LIMIT ?`,
      [norm, limit]
    );
  }

  async searchFts(term, limit = 20) {
    const cleanTerm = (term || '').replace(/[^a-zA-Z0-9_*]/g, '').trim();
    if (!cleanTerm) return [];
    return await this._all(
      `SELECT fts.target_id, fts.target_type, fts.term, fts.gloss, l.pos, l.frequency_summary
       FROM lexicon_fts fts
       LEFT JOIN lexemes l ON l.id = fts.target_id
       WHERE lexicon_fts MATCH ?
       LIMIT ?`,
      [cleanTerm, limit]
    );
  }

  async traverseNeighborhood(lexemeId, maxDepth = 3) {
    const depth = Math.min(Math.max(1, maxDepth), 3);
    return await this._all(
      `WITH RECURSIVE traversal(node_id, depth, path) AS (
          SELECT id, 0, id FROM lexemes WHERE id = ?
          UNION ALL
          SELECT 
              CASE WHEN r.subject_id = t.node_id THEN r.object_id ELSE r.subject_id END,
              t.depth + 1,
              t.path || '->' || CASE WHEN r.subject_id = t.node_id THEN r.object_id ELSE r.subject_id END
          FROM traversal t
          JOIN relations r ON (r.subject_id = t.node_id OR r.object_id = t.node_id)
          WHERE t.depth < ?
            AND r.relation_type IN ('DERIVED_FROM', 'HYPERNYM', 'SIMILAR', 'ALSO', 'HAS_FORM')
            AND instr(t.path, CASE WHEN r.subject_id = t.node_id THEN r.object_id ELSE r.subject_id END) = 0
      )
      SELECT t.node_id, t.depth, l.lemma, l.pos, r.relation_type, r.evidence_type
      FROM traversal t
      LEFT JOIN lexemes l ON l.id = t.node_id
      LEFT JOIN relations r ON (r.subject_id = t.node_id OR r.object_id = t.node_id)
      LIMIT 200`,
      [lexemeId, depth]
    );
  }

  async getWordDetails(lexemeId) {
    const lexeme = await this._get('SELECT * FROM lexemes WHERE id = ?', [lexemeId]);
    if (!lexeme) return null;

    const baseForm = await this._get(
      `SELECT f.* FROM forms f JOIN relations r ON r.object_id = f.id 
       WHERE r.subject_id = ? AND r.relation_type = 'HAS_FORM' AND f.form_type = 'BASE'`,
      [lexemeId]
    );

    const senses = await this._all(
      `SELECT s.*, syn.gloss as synset_gloss, syn.domain as synset_domain
       FROM senses s
       LEFT JOIN synsets syn ON s.synset_id = syn.id
       WHERE s.lexeme_id = ?`,
      [lexemeId]
    );

    const inflectedForms = await this._all(
      `SELECT f.id, f.surface, f.form_type, f.features_json, r.evidence_type
       FROM relations r
       JOIN forms f ON r.object_id = f.id
       WHERE r.subject_id = ? AND r.relation_type = 'HAS_FORM' AND f.form_type != 'BASE'`,
      [lexemeId]
    );

    const derivationalLinks = await this._all(
      `SELECT r.id as relation_id, r.evidence_type, r.confidence, "RESOLVED" as resolution_status,
              l.id as relative_id, l.lemma as relative_lemma, l.pos as relative_pos,
              CASE WHEN r.subject_id = ? THEN 'DERIVED_TARGET' ELSE 'DERIVED_BASE' END as direction
       FROM relations r
       JOIN lexemes l ON (l.id = CASE WHEN r.subject_id = ? THEN r.object_id ELSE r.subject_id END)
       WHERE (r.subject_id = ? OR r.object_id = ?) AND r.relation_type = 'DERIVED_FROM'`,
      [lexemeId, lexemeId, lexemeId, lexemeId]
    );

    return { lexeme, baseForm, senses, inflectedForms, derivationalLinks };
  }

  async explainConnection(relationId) {
    const relation = await this._get('SELECT * FROM relations WHERE id = ?', [relationId]);
    if (!relation) return null;

    const claims = await this._all(
      `SELECT c.id, c.source_id, c.source_version, c.claim_type, c.predicate,
              c.epistemic_class, c.confidence, c.payload_json
       FROM relation_claims rc
       JOIN claims c ON rc.claim_id = c.id
       WHERE rc.relation_id = ?`,
      [relationId]
    );

    return {
      relation,
      claims,
      isConflicting: relation.evidence_type === 'UNCERTAIN',
      isInferred: relation.evidence_type === 'INFERRED'
    };
  }
}

module.exports = { LexicalQueryService };
