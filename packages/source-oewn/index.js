const crypto = require("crypto");

/**
 * Deterministic UUIDv5 generator for lexical entities.
 */
const NAMESPACE_OID = "6ba7b812-9dad-11d1-80b4-00c04fd430c8";
function generateUUID(name) {
  return crypto.createHash("sha1").update(NAMESPACE_OID + name).digest("hex").replace(
    /(.{8})(.{4})(.{4})(.{4})(.{12})/,
    "$1-$2-5$3-$4-$5"
  ).slice(0, 36);
}

/**
 * Normalizes string inputs: NFC, case-folded, whitespace-trimmed.
 */
function normalizeString(str) {
  return str.normalize("NFC").trim().toLowerCase();
}

/**
 * Maps OEWN POS character to canonical POS enum.
 */
function mapPos(oewnPos) {
  switch (oewnPos) {
    case "n": return "NOUN";
    case "v": return "VERB";
    case "a":
    case "s": return "ADJECTIVE";
    case "r": return "ADVERB";
    default: return "OTHER";
  }
}

/**
 * Parses an OEWN JSON dataset and loads it into the canonical SQLite database.
 */
async function ingestOEWN(db, rawData, sourceMetadata) {
  const run = (query, params = []) => new Promise((resolve, reject) => {
    db.run(query, params, function (err) {
      if (err) reject(err);
      else resolve(this);
    });
  });

  // 1. Ensure Source Metadata Exists
  await run(
    `INSERT OR IGNORE INTO sources (id, name, version, release_date, downloaded_at, sha256, license, attribution_url)
     VALUES (?, ?, ?, ?, ?, ?, ?, ?)`,
    [
      sourceMetadata.id,
      sourceMetadata.name,
      sourceMetadata.version,
      sourceMetadata.release_date,
      sourceMetadata.downloaded_at,
      sourceMetadata.sha256,
      sourceMetadata.license,
      sourceMetadata.attribution_url
    ]
  );

  // 2. Ingest Synsets
  for (const [synsetId, sData] of Object.entries(rawData.synsets || {})) {
    const canonicalSynsetId = generateUUID("synset:" + synsetId);
    const pos = mapPos(sData.partOfSpeech);
    const gloss = sData.definition ? sData.definition[0] : "";
    const domain = sData.lex_domain || null;

    // Record Synset Claim
    const claimId = generateUUID("claim:synset:" + synsetId);
    await run(
      `INSERT OR IGNORE INTO claims (id, source_id, source_version, subject_type, subject_source_id, predicate, raw_payload, evidence_type, confidence)
       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)`,
      [claimId, sourceMetadata.id, sourceMetadata.version, "SYNSET", synsetId, "EXISTS", JSON.stringify(sData), "EXPLICIT", 1.0]
    );

    // Insert Canonical Synset Node
    await run(
      `INSERT OR REPLACE INTO synsets (id, source, source_synset_id, pos, gloss, domain, members)
       VALUES (?, ?, ?, ?, ?, ?, ?)`,
      [canonicalSynsetId, sourceMetadata.id, synsetId, pos, gloss, domain, JSON.stringify(sData.members || [])]
    );
  }

  // 3. Ingest Entries (Lexemes, Senses, Forms)
  for (const [lemma, entries] of Object.entries(rawData.entries || {})) {
    const normalizedLemma = normalizeString(lemma);

    for (const entry of entries) {
      const canonicalPos = mapPos(entry.partOfSpeech);
      const lexemeKey = "eng:" + normalizedLemma + ":" + canonicalPos;
      const lexemeId = generateUUID("lexeme:" + lexemeKey);

      // Ingest Base Form
      const baseFormId = generateUUID("form:" + normalizedLemma);
      await run(
        `INSERT OR IGNORE INTO forms (id, surface, normalized_surface, form_type, source, evidence, confidence)
         VALUES (?, ?, ?, ?, ?, ?, ?)`,
        [baseFormId, lemma, normalizedLemma, "BASE", sourceMetadata.id, "EXPLICIT", 1.0]
      );

      // Ingest Lexeme
      await run(
        `INSERT OR IGNORE INTO lexemes (id, lemma, normalized_lemma, language, pos, lemma_form_id, lexeme_key, source_presence, status)
         VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)`,
        [lexemeId, lemma, normalizedLemma, "eng", canonicalPos, baseFormId, lexemeKey, JSON.stringify([sourceMetadata.id]), "CANONICAL"]
      );

      // Link Lexeme to Base Form
      const relFormId = generateUUID("rel:has_form:" + lexemeId + ":" + baseFormId);
      await run(
        `INSERT OR IGNORE INTO relations (id, subject_type, subject_id, relation_type, object_type, object_id, evidence_type, confidence, resolution_status)
         VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)`,
        [relFormId, "LEXEME", lexemeId, "HAS_FORM", "FORM", baseFormId, "EXPLICIT", 1.0, "RESOLVED"]
      );

      // Ingest Senses
      for (const senseData of entry.senses || []) {
        const senseId = generateUUID("sense:" + senseData.id);
        const synsetUuid = generateUUID("synset:" + senseData.synset);

        await run(
          `INSERT OR IGNORE INTO senses (id, lexeme_id, synset_id, definition, domain, source, source_sense_id, confidence)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)`,
          [senseId, lexemeId, synsetUuid, senseData.definition || "", senseData.domain || null, sourceMetadata.id, senseData.id, 1.0]
        );

        // Relate Sense to Synset
        const relMemberId = generateUUID("rel:member_of:" + senseId + ":" + synsetUuid);
        await run(
          `INSERT OR IGNORE INTO relations (id, subject_type, subject_id, relation_type, object_type, object_id, evidence_type, confidence, resolution_status)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)`,
          [relMemberId, "SENSE", senseId, "MEMBER_OF_SYNSET", "SYNSET", synsetUuid, "EXPLICIT", 1.0, "RESOLVED"]
        );

        // Ingest Derivational Links (OEWN pointer "+") strictly as DERIVED_FROM between Lexemes
        for (const deriv of senseData.derivation || []) {
          const targetLexemeKey = "eng:" + normalizeString(deriv.target_lemma) + ":" + mapPos(deriv.target_pos);
          const targetLexemeId = generateUUID("lexeme:" + targetLexemeKey);

          const derivClaimId = generateUUID("claim:derivation:" + senseData.id + ":" + deriv.target_lemma);
          await run(
            `INSERT OR IGNORE INTO claims (id, source_id, source_version, subject_type, subject_source_id, predicate, object_type, object_source_id, raw_payload, evidence_type, confidence)
             VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`,
            [derivClaimId, sourceMetadata.id, sourceMetadata.version, "LEXEME", lemma, "DERIVED_FROM", "LEXEME", deriv.target_lemma, JSON.stringify(deriv), "EXPLICIT", 1.0]
          );

          const relDerivId = generateUUID("rel:derived:" + lexemeId + ":" + targetLexemeId);
          await run(
            `INSERT OR IGNORE INTO relations (id, subject_type, subject_id, relation_type, object_type, object_id, evidence_type, confidence, resolution_status)
             VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)`,
            [relDerivId, "LEXEME", lexemeId, "DERIVED_FROM", "LEXEME", targetLexemeId, "EXPLICIT", 1.0, "RESOLVED"]
          );

          await run(
            `INSERT OR IGNORE INTO relation_claims (relation_id, claim_id) VALUES (?, ?)`,
            [relDerivId, derivClaimId]
          );
        }
      }
    }
  }

  // 4. Ingest Conceptual Relations between Synsets (Hypernyms, Hyponyms)
  for (const [synsetId, sData] of Object.entries(rawData.synsets || {})) {
    const sourceSynsetUuid = generateUUID("synset:" + synsetId);

    for (const hypernymId of sData.hypernyms || []) {
      const targetSynsetUuid = generateUUID("synset:" + hypernymId);
      const relId = generateUUID("rel:hypernym:" + sourceSynsetUuid + ":" + targetSynsetUuid);

      await run(
        `INSERT OR IGNORE INTO relations (id, subject_type, subject_id, relation_type, object_type, object_id, evidence_type, confidence, resolution_status)
         VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)`,
        [relId, "SYNSET", sourceSynsetUuid, "HYPERNYM_OF", "SYNSET", targetSynsetUuid, "EXPLICIT", 1.0, "RESOLVED"]
      );
    }
  }
}

module.exports = { ingestOEWN, generateUUID, normalizeString, mapPos };
