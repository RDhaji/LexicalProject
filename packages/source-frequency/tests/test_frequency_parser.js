const fs = require("fs");
const path = require("path");
const os = require("os");
const sqlite3 = require(path.join(os.homedir(), "Desktop/LexicalProject/packages/schema/node_modules/sqlite3")).verbose();
const { ingestFrequencyStream, computeFrequencyTier } = require("../index");

const schemaSqlPath = path.join(__dirname, "../../../packages/schema/schema.sql");
const dbPath = path.join(__dirname, "test_frequency.db");
const sampleTsvPath = path.join(__dirname, "sample_subtlex.tsv");

if (fs.existsSync(dbPath)) fs.unlinkSync(dbPath);
if (fs.existsSync(sampleTsvPath)) fs.unlinkSync(sampleTsvPath);

const db = new sqlite3.Database(dbPath);
const schemaSql = fs.readFileSync(schemaSqlPath, "utf8");

// Mock SUBTLEX-US TSV format
const sampleRows = [
  "Word\tFREQcount\tCDcount\tSUBTLWF\tLg10WF\tSUBTLCD\tLg10CD",
  "run\t28941\t8120\t567.47\t4.4615\t97.23\t3.9096",
  "fast\t10542\t5210\t206.71\t4.0229\t62.39\t3.7168",
  "happy\t14210\t6420\t278.63\t4.1526\t76.88\t3.8075",
  "unhappiness\t82\t74\t1.61\t1.9138\t0.89\t1.8692"
];

fs.writeFileSync(sampleTsvPath, sampleRows.join("\n") + "\n", "utf8");

const mockSourceMeta = {
  id: "SUBTLEX_US_R1",
  name: "SUBTLEX-US Frequency Norms",
  version: "1.0",
  release_date: "2009-09-01",
  downloaded_at: "2026-09-04",
  sha256: "8f7e6d5c4b3a2f1e0d9c8b7a6f5e4d3c2b1a0f9e8d7c6b5a4f3e2d1c0b9a8f7e",
  license: "Research / Educational Free",
  attribution_url: "https://www.ugent.be/pp/experimentele-psychologie/en/research/documents/subtlexus"
};

async function verify() {
  console.log("Beginning Phase 7: Frequency Integration Tests (PRD §57 Gate 7)...\n");

  await new Promise((resolve, reject) => {
    db.exec(schemaSql, (err) => {
      if (err) reject(err);
      else resolve();
    });
  });

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

  // Seed sample canonical lexemes to test update mapping
  await run(
    `INSERT INTO lexemes (id, lemma, normalized_lemma, pos, lexeme_key, source_presence, status)
     VALUES ("lex-run-v", "run", "run", "VERB", "eng:run:VERB", "[]", "CANONICAL")`
  );
  await run(
    `INSERT INTO lexemes (id, lemma, normalized_lemma, pos, lexeme_key, source_presence, status)
     VALUES ("lex-fast-adj", "fast", "fast", "ADJECTIVE", "eng:fast:ADJECTIVE", "[]", "CANONICAL")`
  );
  await run(
    `INSERT INTO lexemes (id, lemma, normalized_lemma, pos, lexeme_key, source_presence, status)
     VALUES ("lex-unhappiness-n", "unhappiness", "unhappiness", "NOUN", "eng:unhappiness:NOUN", "[]", "CANONICAL")`
  );

  // Ingest Frequency Stream
  await ingestFrequencyStream(db, sampleTsvPath, mockSourceMeta);
  console.log("✓ Streamed sample SUBTLEX-US TSV and annotated canonical lexemes.");

  // Test 1: Tier Calculation unit verification
  if (computeFrequencyTier(5.2) !== "VERY_COMMON" ||
      computeFrequencyTier(4.5) !== "COMMON" ||
      computeFrequencyTier(3.5) !== "LESS_COMMON" ||
      computeFrequencyTier(2.1) !== "RARE") {
    throw new Error("FAIL: Frequency tier thresholds do not match PRD §50 specification.");
  }
  console.log("✓ Test 7.1: Frequency tier calculation logic verified against PRD §50.");

  // Test 2: High-frequency lexeme (run: Zipf ~7.46 -> VERY_COMMON)
  const runLex = await get("SELECT frequency_summary FROM lexemes WHERE id = 'lex-run-v'");
  const runSummary = JSON.parse(runLex.frequency_summary);
  if (!runSummary || runSummary.tier !== "VERY_COMMON" || runSummary.zipf_score < 7.0) {
    throw new Error("FAIL: Frequency summary for run/VERB not recorded accurately.");
  }
  console.log("✓ Test 7.2: High-frequency lemma (run) correctly annotated with Zipf score and tier.");

  // Test 3: Low-frequency lexeme (unhappiness: Zipf ~4.91 -> COMMON)
  const unhapLex = await get("SELECT frequency_summary FROM lexemes WHERE id = 'lex-unhappiness-n'");
  const unhapSummary = JSON.parse(unhapLex.frequency_summary);
  if (!unhapSummary || unhapSummary.tier !== "COMMON") {
    throw new Error("FAIL: Frequency summary for unhappiness not recorded accurately.");
  }
  console.log("✓ Test 7.3: Lower frequency lemma (unhappiness) annotated accurately.");

  // Test 4: Sense Pollution Invariant (PRD §7.4, §50)
  // Ensure NO frequency column or attribute exists or is written into the senses table
  const senseColumns = await new Promise((resolve, reject) => {
    db.all("PRAGMA table_info(senses)", (err, rows) => {
      if (err) reject(err);
      else resolve(rows.map(r => r.name));
    });
  });
  if (senseColumns.includes("frequency") || senseColumns.includes("frequency_summary")) {
    throw new Error("CRITICAL FAIL: Senses table contains frequency field! Violates PRD §7.4 invariant.");
  }
  console.log("✓ Test 7.4: Sense purity verified (no frequency data pollutes semantic senses).");

  // Test 5: Ledger Provenance Verification
  const claimCount = await get("SELECT COUNT(*) as count FROM claims WHERE source_id = 'SUBTLEX_US_R1'");
  if (claimCount.count !== (sampleRows.length - 1)) {
    throw new Error("FAIL: Every processed frequency row must register an explicit claim.");
  }
  console.log("✓ Test 7.5: 100% frequency claims recorded in claims ledger.");

  // Clean up
  db.close(() => {
    fs.unlinkSync(dbPath);
    fs.unlinkSync(sampleTsvPath);
    console.log("\n==================================================");
    console.log("FREQUENCY INTEGRATION VERIFIED. GATE 7 COMPLETE.");
    console.log("==================================================");
  });
}

verify().catch((err) => {
  console.error("\nPhase 7 verification failed:", err);
  process.exit(1);
});
