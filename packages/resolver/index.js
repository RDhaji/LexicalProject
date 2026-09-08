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
 * Resolves a staged candidate into a canonical Lexeme entity.
 * Guarantees that homographs of differing POS remain independent.
 */
async function resolveLexeme(db, candidate) {
  const run = (query, params = []) => new Promise((resolve, reject) => {
    db.run(query, params, function (err) {
      if (err) reject(err);
      else resolve(this);
    });
  });

  const get = (query, params = []) => new Promise((resolve, reject) => {
    db.get(query, params, (err, row) => {
      if (err) reject(err);
      else resolve(row);
    });
  });

  const normalizedLemma = normalizeString(candidate.lemma);
  const pos = candidate.pos.toUpperCase();
  const homographId = candidate.homograph_disambiguator ? ":" + candidate.homograph_disambiguator : "";
  const lexemeKey = "eng:" + normalizedLemma + ":" + pos + homographId;
  const lexemeId = generateUUID("lexeme:" + lexemeKey);
  const sourceId = candidate.source_id;

  // Verify whether canonical lexeme already exists
  const existing = await get("SELECT id, source_presence FROM lexemes WHERE id = ?", [lexemeId]);

  if (existing) {
    // Append source presence if not present
    let sources = [];
    try {
      sources = JSON.parse(existing.source_presence || "[]");
    } catch (e) {
      sources = [];
    }

    if (sourceId && !sources.includes(sourceId)) {
      sources.push(sourceId);
      await run("UPDATE lexemes SET source_presence = ? WHERE id = ?", [JSON.stringify(sources), lexemeId]);
    }
    return { id: lexemeId, lexeme_key: lexemeKey, status: "EXISTING" };
  }

  // Ensure Base Form exists
  const baseFormId = generateUUID("form:" + normalizedLemma);
  await run(
    `INSERT OR IGNORE INTO forms (id, surface, normalized_surface, form_type, source, evidence, confidence)
     VALUES (?, ?, ?, ?, ?, ?, ?)`,
    [baseFormId, candidate.lemma, normalizedLemma, "BASE", sourceId || "INTERNAL", "EXPLICIT", 1.0]
  );

  // Insert Canonical Lexeme
  const initialSources = sourceId ? [sourceId] : [];
  await run(
    `INSERT INTO lexemes (id, lemma, normalized_lemma, language, pos, lemma_form_id, lexeme_key, source_presence, status)
     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)`,
    [
      lexemeId,
      candidate.lemma,
      normalizedLemma,
      "eng",
      pos,
      baseFormId,
      lexemeKey,
      JSON.stringify(initialSources),
      candidate.status || "CANONICAL"
    ]
  );

  // Link Lexeme to Base Form via HAS_FORM
  const relFormId = generateUUID("rel:has_form:" + lexemeId + ":" + baseFormId);
  await run(
    `INSERT OR IGNORE INTO relations (id, subject_type, subject_id, relation_type, object_type, object_id, evidence_type, confidence, resolution_status)
     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)`,
    [relFormId, "LEXEME", lexemeId, "HAS_FORM", "FORM", baseFormId, "EXPLICIT", 1.0, "RESOLVED"]
  );

  return { id: lexemeId, lexeme_key: lexemeKey, status: "CREATED" };
}

/**
 * Resolves raw claims into canonical cross-source alignments without loss of source provenance.
 */
async function resolveSourceClaims(db) {
  const run = (query, params = []) => new Promise((resolve, reject) => {
    db.run(query, params, function (err) {
      if (err) reject(err);
      else resolve(this);
    });
  });

  const all = (query, params = []) => new Promise((resolve, reject) => {
    db.all(query, params, (err, rows) => {
      if (err) reject(err);
      else resolve(rows);
    });
  });

  // Identify competing derivation claims for identical subject-object pairs
  const derivClaims = await all(
    `SELECT subject_source_id, object_source_id, COUNT(DISTINCT source_id) as source_count
     FROM claims 
     WHERE predicate = "DERIVED_FROM"
     GROUP BY subject_source_id, object_source_id`
  );

  for (const group of derivClaims) {
    if (group.source_count > 1) {
      // Multiple sources agree on derivation: mark confidence HIGH (1.0)
      await run(
        `UPDATE relations 
         SET confidence = 1.0, resolution_status = "RESOLVED"
         WHERE subject_id IN (SELECT id FROM lexemes WHERE lemma = ?)
           AND object_id IN (SELECT id FROM lexemes WHERE lemma = ?)
           AND relation_type = "DERIVED_FROM"`,
        [group.subject_source_id, group.object_source_id]
      );
    }
  }
}

module.exports = { resolveLexeme, resolveSourceClaims, generateUUID, normalizeString };
