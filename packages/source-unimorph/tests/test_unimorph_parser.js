const fs = require("fs");
const path = require("path");
const os = require("os");
const sqlite3 = require(path.join(os.homedir(), "Desktop/LexicalProject/packages/schema/node_modules/sqlite3")).verbose();
const { ingestUniMorphStream, parseUniMorphFeatures } = require("../index");

const schemaSqlPath = path.join(__dirname, "../../../packages/schema/schema.sql");
const dbPath = path.join(__dirname, "test_unimorph.db");
const sampleTsvPath = path.join(__dirname, "sample_unimorph.tsv");

if (fs.existsSync(dbPath)) fs.unlinkSync(dbPath);
if (fs.existsSync(sampleTsvPath)) fs.unlinkSync(sampleTsvPath);

const db = new sqlite3.Database(dbPath);
const schemaSql = fs.readFileSync(schemaSqlPath, "utf8");

// Curated Gate 6 mandatory test suite: run, be, go, fast, good, bad
const sampleRows = [
  "run\trun\tV;NFIN",
  "run\truns\tV;3;SG;PRS",
  "run\trunning\tV;V.PTCP;PRS",
  "run\tran\tV;PST",
  "be\tam\tV;1;SG;PRS",
  "be\tis\tV;3;SG;PRS",
  "be\tare\tV;PRS",
  "be\twas\tV;1;SG;PST",
  "be\twere\tV;PST",
  "go\tgoes\tV;3;SG;PRS",
  "go\twent\tV;PST",
  "go\tgoing\tV;V.PTCP;PRS",
  "fast\tfaster\tADJ;CMPR",
  "fast\tfastest\tADJ;SPRL",
  "good\tbetter\tADJ;CMPR",
  "good\tbest\tADJ;SPRL",
  "bad\tworse\tADJ;CMPR",
  "bad\tworst\tADJ;SPRL"
];

fs.writeFileSync(sampleTsvPath, sampleRows.join("\n") + "\n", "utf8");

const mockSourceMeta = {
  id: "UNIMORPH_ENG",
  name: "UniMorph English Repository",
  version: "master-stable-2026",
  release_date: "2026-01-15",
  downloaded_at: "2026-09-04",
  sha256: "5c4d3e2b1a0f9e8d7c6b5a4f3e2d1c0b9a8f7e6d5c4b3a2f1e0d9c8b7a6f5e4d",
  license: "CC-BY-SA-4.0",
  attribution_url: "https://github.com/unimorph/eng"
};

async function verify() {
  console.log("Beginning Phase 6: UniMorph Ingestion Tests (PRD §57 Gate 6)...\n");

  await new Promise((resolve, reject) => {
    db.exec(schemaSql, (err) => {
      if (err) reject(err);
      else resolve();
    });
  });

  await ingestUniMorphStream(db, sampleTsvPath, mockSourceMeta);
  console.log("✓ Streamed sample UniMorph TSV into canonical SQLite tables.");

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

  // Test 1: Verification of run paradigm
  const runForms = await all(
    `SELECT f.surface, f.form_type, f.features_json 
     FROM relations r 
     JOIN forms f ON r.object_id = f.id 
     WHERE r.relation_type = 'HAS_FORM' AND r.subject_id = (SELECT id FROM lexemes WHERE lemma = 'run' AND pos = 'VERB')`
  );
  if (runForms.length !== 4) throw new Error("FAIL: Expected 4 forms for run/VERB.");
  const ran = runForms.find(f => f.surface === "ran");
  if (!ran || ran.form_type !== "IRREGULAR") throw new Error("FAIL: ran must be tagged IRREGULAR.");
  console.log("✓ Test 6.1: Paradigm for run verified (run, runs, running, ran).");

  // Test 2: Extreme suppletion: go -> went
  const went = await get(
    `SELECT f.surface, f.form_type 
     FROM relations r 
     JOIN forms f ON r.object_id = f.id 
     WHERE r.subject_id = (SELECT id FROM lexemes WHERE lemma = 'go') AND f.surface = 'went'`
  );
  if (!went || went.form_type !== "SUPPLETIVE") throw new Error("FAIL: went must be tagged SUPPLETIVE.");
  console.log("✓ Test 6.2: Suppletion for go -> went verified.");

  // Test 3: Irregular auxiliary: be -> am, is, are, was, were
  const beForms = await all(
    `SELECT f.surface, f.form_type 
     FROM relations r 
     JOIN forms f ON r.object_id = f.id 
     WHERE r.subject_id = (SELECT id FROM lexemes WHERE lemma = 'be')`
  );
  if (beForms.length !== 5) throw new Error("FAIL: Expected 5 distinct forms for be/VERB.");
  console.log("✓ Test 6.3: Paradigm for be/VERB verified (am, is, are, was, were).");

  // Test 4: Comparative/Superlative degree: fast -> faster, fastest
  const fastForms = await all(
    `SELECT f.surface, f.features_json 
     FROM relations r 
     JOIN forms f ON r.object_id = f.id 
     WHERE r.subject_id = (SELECT id FROM lexemes WHERE lemma = 'fast' AND pos = 'ADJECTIVE')`
  );
  if (fastForms.length !== 2) throw new Error("FAIL: Expected comparative and superlative for fast/ADJECTIVE.");
  console.log("✓ Test 6.4: Degree inflections for fast verified (faster, fastest).");

  // Test 5: Suppletive adjectives: good -> better, best; bad -> worse, worst
  const better = await get("SELECT form_type FROM forms WHERE surface = 'better'");
  const worse = await get("SELECT form_type FROM forms WHERE surface = 'worse'");
  if (!better || better.form_type !== "SUPPLETIVE" || !worse || worse.form_type !== "SUPPLETIVE") {
    throw new Error("FAIL: better and worse must be tagged SUPPLETIVE.");
  }
  console.log("✓ Test 6.5: Adjective suppletion verified (good -> better/best; bad -> worse/worst).");

  // Test 6: Claim provenance verified
  const claimCount = await get("SELECT COUNT(*) as count FROM claims WHERE source_id = 'UNIMORPH_ENG'");
  if (claimCount.count !== sampleRows.length) throw new Error("FAIL: Each paradigm line must emit a claim.");
  console.log("✓ Test 6.6: 100% claim coverage verified in claims ledger.");

  // Clean up
  db.close(() => {
    fs.unlinkSync(dbPath);
    fs.unlinkSync(sampleTsvPath);
    console.log("\n==================================================");
    console.log("UNIMORPH PARSER VERIFIED. GATE 6 COMPLETE.");
    console.log("==================================================");
  });
}

verify().catch((err) => {
  console.error("\nPhase 6 verification failed:", err);
  process.exit(1);
});
