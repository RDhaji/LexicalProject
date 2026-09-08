const fs = require("fs");
const readline = require("readline");
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

function mapPos(rawPos) {
  switch ((rawPos || "").toLowerCase()) {
    case "noun": return "NOUN";
    case "verb": return "VERB";
    case "adj":
    case "adjective": return "ADJECTIVE";
    case "adv":
    case "adverb": return "ADVERB";
    case "pron":
    case "pronoun": return "PRONOUN";
    case "det":
    case "determiner": return "DETERMINER";
    case "prep":
    case "preposition": return "PREPOSITION";
    case "conj":
    case "conjunction": return "CONJUNCTION";
    case "intj":
    case "interjection": return "INTERJECTION";
    case "num":
    case "numeral": return "NUMERAL";
    case "part":
    case "particle": return "PARTICLE";
    default: return "OTHER";
  }
}

/**
 * Streams a Wiktextract JSONL file line-by-line directly into SQLite tables.
 */
async function ingestWiktionaryStream(db, jsonlFilePath, sourceMetadata) {
  const run = (query, params = []) => new Promise((resolve, reject) => {
    db.run(query, params, function (err) {
      if (err) reject(err);
      else resolve(this);
    });
  });

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

  const fileStream = fs.createReadStream(jsonlFilePath, { encoding: "utf8" });
  const rl = readline.createInterface({ input: fileStream, crlfDelay: Infinity });

  for await (const line of rl) {
    if (!line || !line.trim()) continue;

    let item;
    try {
      item = JSON.parse(line);
    } catch (e) {
      continue; // Skip malformed JSONL records
    }

    // Filter strictly for English entries
    if (item.lang_code !== "en" && item.lang !== "English") continue;

    const lemma = item.word;
    if (!lemma) continue;

    const normalizedLemma = normalizeString(lemma);
    const canonicalPos = mapPos(item.pos);
    const lexemeKey = "eng:" + normalizedLemma + ":" + canonicalPos;
    const lexemeId = generateUUID("lexeme:" + lexemeKey);

    // Extract IPA pronunciation if available
    let phonemicIpa = null;
    if (Array.isArray(item.sounds)) {
      for (const s of item.sounds) {
        if (s.ipa) {
          phonemicIpa = s.ipa;
          break;
        }
      }
    }

    // 1. Ingest Base Form
    const baseFormId = generateUUID("form:" + normalizedLemma);
    await run(
      `INSERT OR IGNORE INTO forms (id, surface, normalized_surface, phonemic_ipa, form_type, source, evidence, confidence)
       VALUES (?, ?, ?, ?, ?, ?, ?, ?)`,
      [baseFormId, lemma, normalizedLemma, phonemicIpa, "BASE", sourceMetadata.id, "EXPLICIT", 1.0]
    );

    // 2. Ingest Lexeme
    await run(
      `INSERT OR IGNORE INTO lexemes (id, lemma, normalized_lemma, language, pos, lemma_form_id, lexeme_key, source_presence, status)
       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)`,
      [lexemeId, lemma, normalizedLemma, "eng", canonicalPos, baseFormId, lexemeKey, JSON.stringify([sourceMetadata.id]), "CANONICAL"]
    );

    // 3. Link Lexeme to Base Form
    const relFormId = generateUUID("rel:has_form:" + lexemeId + ":" + baseFormId);
    await run(
      `INSERT OR IGNORE INTO relations (id, subject_type, subject_id, relation_type, object_type, object_id, evidence_type, confidence, resolution_status)
       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)`,
      [relFormId, "LEXEME", lexemeId, "HAS_FORM", "FORM", baseFormId, "EXPLICIT", 1.0, "RESOLVED"]
    );

    // 4. Ingest Senses and raw Claims
    if (Array.isArray(item.senses)) {
      let rank = 1;
      for (const sense of item.senses) {
        const gloss = Array.isArray(sense.glosses) ? sense.glosses.join("; ") : "";
        if (!gloss) continue;

        const senseId = generateUUID("sense:wikt:" + lexemeKey + ":" + (rank++));
        await run(
          `INSERT OR IGNORE INTO senses (id, lexeme_id, definition, source, confidence)
           VALUES (?, ?, ?, ?, ?)`,
          [senseId, lexemeId, gloss, sourceMetadata.id, 0.9]
        );

        // Store complete Wiktionary entry claim
        const claimId = generateUUID("claim:wikt:" + senseId);
        await run(
          `INSERT OR IGNORE INTO claims (id, source_id, source_version, subject_type, subject_source_id, predicate, raw_payload, evidence_type, confidence)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)`,
          [claimId, sourceMetadata.id, sourceMetadata.version, "SENSE", senseId, "HAS_DEFINITION", JSON.stringify(sense), "EXPLICIT", 0.9]
        );
      }
    }

    // 5. Ingest Inflected Surface Forms
    if (Array.isArray(item.forms)) {
      for (const f of item.forms) {
        const surfaceForm = f.form;
        if (!surfaceForm || surfaceForm.includes(" ")) continue; // Exclude multiword tokens

        const normSurface = normalizeString(surfaceForm);
        const formId = generateUUID("form:" + normSurface);
        const formClaimId = generateUUID("claim:form:" + lexemeKey + ":" + normSurface);

        await run(
          `INSERT OR IGNORE INTO claims (id, source_id, source_version, subject_type, subject_source_id, predicate, object_type, object_source_id, raw_payload, evidence_type, confidence)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`,
          [formClaimId, sourceMetadata.id, sourceMetadata.version, "LEXEME", lemma, "HAS_FORM", "FORM", surfaceForm, JSON.stringify(f), "EXPLICIT", 0.95]
        );

        await run(
          `INSERT OR IGNORE INTO forms (id, surface, normalized_surface, form_type, source, evidence, confidence)
           VALUES (?, ?, ?, ?, ?, ?, ?)`,
          [formId, surfaceForm, normSurface, "INFLECTED", sourceMetadata.id, "EXPLICIT", 0.95]
        );

        const relInflectId = generateUUID("rel:has_form:" + lexemeId + ":" + formId);
        await run(
          `INSERT OR IGNORE INTO relations (id, subject_type, subject_id, relation_type, object_type, object_id, evidence_type, confidence, resolution_status)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)`,
          [relInflectId, "LEXEME", lexemeId, "HAS_FORM", "FORM", formId, "EXPLICIT", 0.95, "RESOLVED"]
        );

        await run(
          `INSERT OR IGNORE INTO relation_claims (relation_id, claim_id) VALUES (?, ?)`,
          [relInflectId, formClaimId]
        );
      }
    }

    // 6. Ingest Derived Terms as DERIVED_FROM edges between Lexemes
    if (Array.isArray(item.derived)) {
      for (const d of item.derived) {
        const targetWord = d.word;
        if (!targetWord || targetWord.includes(" ")) continue;

        const normTarget = normalizeString(targetWord);
        // Default target POS to NOUN if unstated, subject to cross-source resolution
        const targetLexemeKey = "eng:" + normTarget + ":NOUN";
        const targetLexemeId = generateUUID("lexeme:" + targetLexemeKey);

        const derivClaimId = generateUUID("claim:deriv:" + lexemeKey + ":" + normTarget);
        await run(
          `INSERT OR IGNORE INTO claims (id, source_id, source_version, subject_type, subject_source_id, predicate, object_type, object_source_id, raw_payload, evidence_type, confidence)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`,
          [derivClaimId, sourceMetadata.id, sourceMetadata.version, "LEXEME", lemma, "DERIVED_FROM", "LEXEME", targetWord, JSON.stringify(d), "EXPLICIT", 0.85]
        );

        const relDerivId = generateUUID("rel:derived:" + targetLexemeId + ":" + lexemeId);
        await run(
          `INSERT OR IGNORE INTO relations (id, subject_type, subject_id, relation_type, object_type, object_id, evidence_type, confidence, resolution_status)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)`,
          [relDerivId, "LEXEME", targetLexemeId, "DERIVED_FROM", "LEXEME", lexemeId, "EXPLICIT", 0.85, "RESOLVED"]
        );

        await run(
          `INSERT OR IGNORE INTO relation_claims (relation_id, claim_id) VALUES (?, ?)`,
          [relDerivId, derivClaimId]
        );
      }
    }
  }
}

module.exports = { ingestWiktionaryStream, generateUUID, normalizeString, mapPos };
