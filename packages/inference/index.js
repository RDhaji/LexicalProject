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
 * Validated Affix Rules for Candidate Generation (PRD §21, §22)
 */
const INFERENCE_RULES = [
  {
    name: "PREFIX_RE_VERB",
    affix: "re-",
    affix_type: "PREFIX",
    source_pos: "VERB",
    target_pos: "VERB",
    pattern: /^re([a-z]+)$/,
    min_stem_len: 3
  },
  {
    name: "PREFIX_UN_ADJ",
    affix: "un-",
    affix_type: "PREFIX",
    source_pos: "ADJECTIVE",
    target_pos: "ADJECTIVE",
    pattern: /^un([a-z]+)$/,
    min_stem_len: 3
  },
  {
    name: "SUFFIX_ABLE_VERB_TO_ADJ",
    affix: "-able",
    affix_type: "SUFFIX",
    source_pos: "VERB",
    target_pos: "ADJECTIVE",
    pattern: /^([a-z]+)able$/,
    min_stem_len: 3
  }
];

class ControlledInferenceEngine {
  /**
   * Evaluates candidate morphological connections between attested lexemes.
   * Enforces 5-stage validation pipeline (PRD §21).
   */
  static async inferDerivations(db) {
    const run = (q, p = []) => new Promise((resolve, reject) => {
      db.run(q, p, function (err) {
        if (err) reject(err);
        else resolve(this);
      });
    });

    const get = (q, p = []) => new Promise((resolve, reject) => {
      db.get(q, p, (err, row) => {
        if (err) reject(err);
        else resolve(row);
      });
    });

    const all = (q, p = []) => new Promise((resolve, reject) => {
      db.all(q, p, (err, rows) => {
        if (err) reject(err);
        else resolve(rows);
      });
    });

    const allLexemes = await all("SELECT id, lemma, normalized_lemma, pos FROM lexemes");
    const lexemeMap = new Map();
    for (const l of allLexemes) {
      lexemeMap.set(l.normalized_lemma + ":" + l.pos, l);
    }

    const inferredResults = [];

    for (const candidate of allLexemes) {
      for (const rule of INFERENCE_RULES) {
        if (candidate.pos !== rule.target_pos) continue;

        const match = candidate.normalized_lemma.match(rule.pattern);
        if (!match) continue;

        const potentialBaseStem = match[1];
        if (potentialBaseStem.length < rule.min_stem_len) continue;

        // Stage 2: Lexical Existence Validation (Base must exist as an attested lexeme)
        let baseLexeme = lexemeMap.get(potentialBaseStem + ":" + rule.source_pos);

        // Orthographic alternation recovery: silent-e drop (e.g. usable -> use)
        if (!baseLexeme && rule.affix_type === "SUFFIX") {
          baseLexeme = lexemeMap.get(potentialBaseStem + "e:" + rule.source_pos);
        }

        if (!baseLexeme) continue; // Base is not an attested lexical entry; reject candidate

        // Stage 3 & 4: Conflict and Duplication Check
        // If an explicit edge already exists, never overwrite or emit inferred duplicate
        const existingRel = await get(
          `SELECT id, evidence_type FROM relations 
           WHERE subject_id = ? AND object_id = ? AND relation_type = "DERIVED_FROM"`,
          [candidate.id, baseLexeme.id]
        );

        if (existingRel) continue;

        // Stage 5: Confidence Calculation and Inferred Edge Creation
        const confidence = 0.75; // Bounded medium confidence for structured rule inferences
        const relId = generateUUID("rel:inferred:" + candidate.id + ":" + baseLexeme.id);

        const explanation = {
          rule: rule.name,
          affix: rule.affix,
          base_lemma: baseLexeme.lemma,
          target_lemma: candidate.lemma,
          evidence_summary: "Target and base attested in lexical database; matches morphological rule " + rule.name
        };

        // Record explanation in claims table with INFERRED classification
        const claimId = generateUUID("claim:inferred:" + relId);
        await run(
          `INSERT OR REPLACE INTO claims (id, source_id, source_version, subject_type, subject_source_id, predicate, object_type, object_source_id, raw_payload, evidence_type, confidence)
           VALUES (?, "INFERENCE_ENGINE", "1.0", "LEXEME", ?, "DERIVED_FROM", "LEXEME", ?, ?, "INFERRED", ?)`,
          [claimId, candidate.lemma, baseLexeme.lemma, JSON.stringify(explanation), confidence]
        );

        // Insert inferred edge into relations table
        await run(
          `INSERT OR REPLACE INTO relations (id, subject_type, subject_id, relation_type, object_type, object_id, evidence_type, confidence, resolution_status)
           VALUES (?, "LEXEME", ?, "DERIVED_FROM", "LEXEME", ?, "INFERRED", ?, "RESOLVED")`,
          [relId, candidate.id, baseLexeme.id, confidence]
        );

        await run(
          `INSERT OR IGNORE INTO relation_claims (relation_id, claim_id) VALUES (?, ?)`,
          [relId, claimId]
        );

        inferredResults.push({
          target: candidate.lemma,
          base: baseLexeme.lemma,
          rule: rule.name,
          confidence
        });
      }
    }

    return inferredResults;
  }
}

module.exports = { ControlledInferenceEngine, INFERENCE_RULES, generateUUID, normalizeString };
