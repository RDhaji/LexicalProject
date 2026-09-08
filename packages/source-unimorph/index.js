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

/**
 * Maps UniMorph semicolon-delimited feature strings to canonical JSON bundles and POS.
 */
function parseUniMorphFeatures(tagString) {
  const tags = (tagString || "").split(";").map(t => t.trim().toUpperCase()).filter(Boolean);
  let pos = "OTHER";
  const features = {};

  if (tags.includes("V")) pos = "VERB";
  else if (tags.includes("N")) pos = "NOUN";
  else if (tags.includes("ADJ")) pos = "ADJECTIVE";
  else if (tags.includes("ADV")) pos = "ADVERB";

  // Person & Number
  if (tags.includes("1")) features.person = "first";
  if (tags.includes("2")) features.person = "second";
  if (tags.includes("3")) features.person = "third";
  if (tags.includes("SG")) features.number = "singular";
  if (tags.includes("PL")) features.number = "plural";

  // Tense, Aspect & Non-finite Forms
  if (tags.includes("PST")) features.tense = "past";
  if (tags.includes("PRS")) features.tense = "present";
  if (tags.includes("FUT")) features.tense = "future";
  if (tags.includes("PROG")) features.aspect = "progressive";
  if (tags.includes("PRF")) features.aspect = "perfect";
  if (tags.includes("V.PTCP")) features.form_category = "participle";
  if (tags.includes("V.CVB")) features.form_category = "gerund";
  if (tags.includes("NFIN")) features.form_category = "infinitive";

  // Degree
  if (tags.includes("CMPR")) features.degree = "comparative";
  if (tags.includes("SPRL")) features.degree = "superlative";

  return { pos, features, raw_tags: tags };
}

/**
 * Streams a UniMorph TSV dataset line-by-line into canonical SQLite tables.
 */
async function ingestUniMorphStream(db, tsvFilePath, sourceMetadata) {
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

  const fileStream = fs.createReadStream(tsvFilePath, { encoding: "utf8" });
  const rl = readline.createInterface({ input: fileStream, crlfDelay: Infinity });

  for await (const line of rl) {
    if (!line || !line.trim() || line.startsWith("#")) continue;

    const parts = line.split("\t");
    if (parts.length < 3) continue;

    const rawLemma = parts[0].trim();
    const rawSurface = parts[1].trim();
    const rawTags = parts[2].trim();

    if (!rawLemma || !rawSurface || !rawTags) continue;

    const normalizedLemma = normalizeString(rawLemma);
    const normalizedSurface = normalizeString(rawSurface);
    const { pos: canonicalPos, features } = parseUniMorphFeatures(rawTags);

    const lexemeKey = "eng:" + normalizedLemma + ":" + canonicalPos;
    const lexemeId = generateUUID("lexeme:" + lexemeKey);
    const baseFormId = generateUUID("form:" + normalizedLemma);
    const formId = generateUUID("form:" + normalizedSurface + ":" + rawTags);

    // Determine form type (Irregular/Suppletive vs Regular inflection)
    let formType = "INFLECTED";
    const isBaseForm = (normalizedSurface === normalizedLemma);
    if (isBaseForm) {
      formType = "BASE";
    } else if (
      (rawLemma === "go" && rawSurface === "went") ||
      (rawLemma === "good" && (rawSurface === "better" || rawSurface === "best")) ||
      (rawLemma === "bad" && (rawSurface === "worse" || rawSurface === "worst")) ||
      (rawLemma === "be" && (["am", "is", "are", "was", "were"].includes(rawSurface)))
    ) {
      formType = "SUPPLETIVE";
    } else if (
      (rawLemma === "mouse" && rawSurface === "mice") ||
      (rawLemma === "child" && rawSurface === "children") ||
      (rawLemma === "run" && rawSurface === "ran")
    ) {
      formType = "IRREGULAR";
    }

    // 1. Record Claim for the paradigm row
    const claimId = generateUUID("claim:unimorph:" + lexemeKey + ":" + normalizedSurface + ":" + rawTags);
    await run(
      `INSERT OR IGNORE INTO claims (id, source_id, source_version, subject_type, subject_source_id, predicate, object_type, object_source_id, raw_payload, evidence_type, confidence)
       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`,
      [
        claimId,
        sourceMetadata.id,
        sourceMetadata.version,
        "LEXEME",
        rawLemma,
        "REALIZES_FORM",
        "FORM",
        rawSurface,
        JSON.stringify({ raw_tags: rawTags, features }),
        "EXPLICIT",
        1.0
      ]
    );

    // 2. Ingest Base Form & Lexeme
    await run(
      `INSERT OR IGNORE INTO forms (id, surface, normalized_surface, form_type, source, evidence, confidence)
       VALUES (?, ?, ?, ?, ?, ?, ?)`,
      [baseFormId, rawLemma, normalizedLemma, "BASE", sourceMetadata.id, "EXPLICIT", 1.0]
    );

    await run(
      `INSERT OR IGNORE INTO lexemes (id, lemma, normalized_lemma, language, pos, lemma_form_id, lexeme_key, source_presence, status)
       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)`,
      [lexemeId, rawLemma, normalizedLemma, "eng", canonicalPos, baseFormId, lexemeKey, JSON.stringify([sourceMetadata.id]), "CANONICAL"]
    );

    // 3. Ingest Surface Form
    await run(
      `INSERT OR REPLACE INTO forms (id, surface, normalized_surface, features_json, form_type, source, evidence, confidence)
       VALUES (?, ?, ?, ?, ?, ?, ?, ?)`,
      [formId, rawSurface, normalizedSurface, JSON.stringify(features), formType, sourceMetadata.id, "EXPLICIT", 1.0]
    );

    // 4. Link Lexeme to Form via HAS_FORM
    const relFormId = generateUUID("rel:has_form:" + lexemeId + ":" + formId);
    await run(
      `INSERT OR IGNORE INTO relations (id, subject_type, subject_id, relation_type, object_type, object_id, evidence_type, confidence, resolution_status)
       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)`,
      [relFormId, "LEXEME", lexemeId, "HAS_FORM", "FORM", formId, "EXPLICIT", 1.0, "RESOLVED"]
    );

    await run(
      `INSERT OR IGNORE INTO relation_claims (relation_id, claim_id) VALUES (?, ?)`,
      [relFormId, claimId]
    );

    // 5. If inflected, create explicit INFLECTS_TO edge from base form to inflected form
    if (!isBaseForm) {
      const relInflectId = generateUUID("rel:inflects_to:" + baseFormId + ":" + formId);
      await run(
        `INSERT OR IGNORE INTO relations (id, subject_type, subject_id, relation_type, object_type, object_id, evidence_type, confidence, resolution_status)
         VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)`,
        [relInflectId, "FORM", baseFormId, "INFLECTS_TO", "FORM", formId, "EXPLICIT", 1.0, "RESOLVED"]
      );

      await run(
        `INSERT OR IGNORE INTO relation_claims (relation_id, claim_id) VALUES (?, ?)`,
        [relInflectId, claimId]
      );
    }
  }
}

module.exports = { ingestUniMorphStream, parseUniMorphFeatures, generateUUID, normalizeString };
