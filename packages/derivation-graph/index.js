const crypto = require("crypto");

const NAMESPACE_OID = "6ba7b812-9dad-11d1-80b4-00c04fd430c8";
function generateUUID(name) {
  return crypto.createHash("sha1").update(NAMESPACE_OID + name).digest("hex").replace(
    /(.{8})(.{4})(.{4})(.{4})(.{12})/,
    "$1-$2-5$3-$4-$5"
  ).slice(0, 36);
}

function normalizeString(str) {
  return (str || "").normalize("NFC").trim().toLowerCase();
}

/**
 * DerivationGraphBuilder: Builds explicit derivational edges and morpheme links.
 * Prohibits heuristic string parsing (PRD §13, ADR-005).
 */
class DerivationGraphBuilder {
  /**
   * Registers a discrete affix or base morpheme node.
   */
  static async registerMorpheme(db, shape, type, status = "ATTESTED") {
    const run = (q, p = []) => new Promise((resolve, reject) => {
      db.run(q, p, function (err) {
        if (err) reject(err);
        else resolve(this);
      });
    });

    const morphemeId = generateUUID("morpheme:" + normalizeString(shape) + ":" + type);
    await run(
      `INSERT OR IGNORE INTO morphemes (id, shape, type, status)
       VALUES (?, ?, ?, ?)`,
      [morphemeId, shape, type, status]
    );
    return morphemeId;
  }

  /**
   * Records an explicit derivational link between two lexemes with provenance.
   */
  static async linkDerivation(db, sourceLexemeId, targetLexemeId, claimId = null, confidence = 1.0) {
    const run = (q, p = []) => new Promise((resolve, reject) => {
      db.run(q, p, function (err) {
        if (err) reject(err);
        else resolve(this);
      });
    });

    const relId = generateUUID("rel:derived:" + targetLexemeId + ":" + sourceLexemeId);
    await run(
      `INSERT OR REPLACE INTO relations (id, subject_type, subject_id, relation_type, object_type, object_id, evidence_type, confidence, resolution_status)
       VALUES (?, "LEXEME", ?, "DERIVED_FROM", "LEXEME", ?, "EXPLICIT", ?, "RESOLVED")`,
      [relId, targetLexemeId, sourceLexemeId, confidence]
    );

    if (claimId) {
      await run(
        `INSERT OR IGNORE INTO relation_claims (relation_id, claim_id) VALUES (?, ?)`,
        [relId, claimId]
      );
    }
    return relId;
  }

  /**
   * Attaches an affix morpheme directly to a morphological structure or lexeme.
   */
  static async attachAffix(db, structureId, morphemeId, slotOrder) {
    const run = (q, p = []) => new Promise((resolve, reject) => {
      db.run(q, p, function (err) {
        if (err) reject(err);
        else resolve(this);
      });
    });

    const relId = generateUUID("rel:contains_morpheme:" + structureId + ":" + morphemeId + ":" + slotOrder);
    await run(
      `INSERT OR REPLACE INTO relations (id, subject_type, subject_id, relation_type, object_type, object_id, evidence_type, confidence, resolution_status)
       VALUES (?, "MORPHOLOGICAL_STRUCTURE", ?, "CONTAINS_MORPHEME", "MORPHEME", ?, "EXPLICIT", 1.0, "RESOLVED")`,
      [relId, structureId, morphemeId]
    );
    return relId;
  }

  /**
   * Traverses derivational family tree for a given lexeme up to bounded depth.
   */
  static async getDerivationalFamily(db, lexemeId, maxDepth = 3) {
    const all = (q, p = []) => new Promise((resolve, reject) => {
      db.all(q, p, (err, rows) => {
        if (err) reject(err);
        else resolve(rows);
      });
    });

    return await all(
      `WITH RECURSIVE deriv_tree(id, lemma, pos, depth, path) AS (
         SELECT l.id, l.lemma, l.pos, 0, l.id
         FROM lexemes l
         WHERE l.id = ?
         
         UNION
         
         SELECT l2.id, l2.lemma, l2.pos, dt.depth + 1, dt.path || "," || l2.id
         FROM relations r
         JOIN lexemes l2 ON (r.subject_id = l2.id OR r.object_id = l2.id)
         JOIN deriv_tree dt ON (dt.id = r.subject_id OR dt.id = r.object_id)
         WHERE r.relation_type = "DERIVED_FROM"
           AND l2.id != dt.id
           AND dt.depth < ?
           AND instr(dt.path, l2.id) = 0
       )
       SELECT DISTINCT id, lemma, pos, depth FROM deriv_tree ORDER BY depth ASC`,
      [lexemeId, maxDepth]
    );
  }
}

module.exports = { DerivationGraphBuilder, generateUUID, normalizeString };
