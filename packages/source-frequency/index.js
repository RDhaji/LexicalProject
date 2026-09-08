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
 * Derives the discrete frequency tier per PRD §50 documented thresholds.
 */
function computeFrequencyTier(zipf) {
  if (zipf >= 5.0) return "VERY_COMMON";
  if (zipf >= 4.0) return "COMMON";
  if (zipf >= 3.0) return "LESS_COMMON";
  return "RARE";
}

/**
 * Streams a SUBTLEX-US TSV file line-by-line, updating canonical lexeme frequency summaries.
 */
async function ingestFrequencyStream(db, tsvFilePath, sourceMetadata) {
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

  // Add covering index for frequency lookups if not existing
  await run(`CREATE INDEX IF NOT EXISTS idx_lexemes_freq_lookup ON lexemes(normalized_lemma)`);

  const fileStream = fs.createReadStream(tsvFilePath, { encoding: "utf8" });
  const rl = readline.createInterface({ input: fileStream, crlfDelay: Infinity });

  let headerProcessed = false;
  let wordIdx = 0;
  let countIdx = 1;
  let lg10Idx = 4;

  for await (const line of rl) {
    if (!line || !line.trim()) continue;

    const parts = line.split("\t").map(p => p.trim());
    if (!headerProcessed) {
      // Inspect header positions dynamically
      parts.forEach((col, idx) => {
        const c = col.toUpperCase();
        if (c === "WORD") wordIdx = idx;
        else if (c === "FREQCOUNT") countIdx = idx;
        else if (c === "LG10WF") lg10Idx = idx;
      });
      headerProcessed = true;
      continue;
    }

    const rawWord = parts[wordIdx];
    if (!rawWord) continue;

    const normalizedWord = normalizeString(rawWord);
    const rawCount = parseInt(parts[countIdx], 10) || 0;
    const lg10wf = parseFloat(parts[lg10Idx]) || 0.0;
    const zipf = parseFloat((lg10wf + 3.0).toFixed(2));
    const tier = computeFrequencyTier(zipf);

    const freqSummary = {
      raw_count: rawCount,
      zipf_score: zipf,
      tier: tier,
      corpus: sourceMetadata.id
    };

    // 1. Record Claim for the frequency entry
    const claimId = generateUUID("claim:freq:" + normalizedWord);
    await run(
      `INSERT OR IGNORE INTO claims (id, source_id, source_version, subject_type, subject_source_id, predicate, raw_payload, evidence_type, confidence)
       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)`,
      [
        claimId,
        sourceMetadata.id,
        sourceMetadata.version,
        "WORD_FORM",
        normalizedWord,
        "HAS_FREQUENCY",
        JSON.stringify(freqSummary),
        "EXPLICIT",
        1.0
      ]
    );

    // 2. Attach frequency summary to all matching canonical lexemes
    await run(
      `UPDATE lexemes 
       SET frequency_summary = ? 
       WHERE normalized_lemma = ?`,
      [JSON.stringify(freqSummary), normalizedWord]
    );
  }
}

module.exports = { ingestFrequencyStream, computeFrequencyTier, generateUUID, normalizeString };
