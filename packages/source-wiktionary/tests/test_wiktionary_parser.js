const fs = require("fs");
const path = require("path");
const os = require("os");
const sqlite3 = require(path.join(os.homedir(), "Desktop/LexicalProject/packages/schema/node_modules/sqlite3")).verbose();
const { ingestWiktionaryStream } = require("../index");

const schemaSqlPath = path.join(__dirname, "../../../packages/schema/schema.sql");
const dbPath = path.join(__dirname, "test_wiktionary.db");
const sampleJsonlPath = path.join(__dirname, "sample_wiktextract.jsonl");

if (fs.existsSync(dbPath)) fs.unlinkSync(dbPath);
if (fs.existsSync(sampleJsonlPath)) fs.unlinkSync(sampleJsonlPath);

const db = new sqlite3.Database(dbPath);
const schemaSql = fs.readFileSync(schemaSqlPath, "utf8");

// Mock JSONL lines corresponding to authentic Wiktextract structures
const mockLines = [
  JSON.stringify({
    word: "run",
    lang: "English",
    lang_code: "en",
    pos: "verb",
    sounds: [{ ipa: "/rʌn/" }],
    senses: [
      { glosses: ["To move swiftly on foot."] },
      { glosses: ["To operate or function."] }
    ],
    forms: [
      { form: "runs", tags: ["present", "singular", "third-person"] },
      { form: "running", tags: ["participle", "present"] },
      { form: "ran", tags: ["past"] }
    ],
    derived: [
      { word: "runner" },
      { word: "runnable" }
    ]
  }),
  JSON.stringify({
    word: "correr",
    lang: "Spanish",
    lang_code: "es",
    pos: "verb",
    senses: [{ glosses: ["to run"] }]
  })
];

fs.writeFileSync(sampleJsonlPath, mockLines.join("\n") + "\n", "utf8");

const mockSourceMeta = {
  id: "WIKTIONARY_KAIKKI_20260805",
  name: "Kaikki Wiktextract",
  version: "2026-08-05",
  release_date: "2026-08-05",
  downloaded_at: "2026-09-04",
  sha256: "a3f5c8e2b1d0e9f4a7c5b3d1e8f2a4c6b8d0e2f4a6c8b0d2e4f6a8c0b2d4e6f8",
  license: "CC-BY-SA-4.0",
  attribution_url: "https://kaikki.org/dictionary/rawdata.html"
};

async function verify() {
  console.log("Beginning Phase 5: Wiktionary Streaming Parser Tests (PRD §57 Gate 5)...\n");

  await new Promise((resolve, reject) => {
    db.exec(schemaSql, (err) => {
      if (err) reject(err);
      else resolve();
    });
  });

  await ingestWiktionaryStream(db, sampleJsonlPath, mockSourceMeta);
  console.log("✓ Streamed and parsed JSONL sample into canonical SQLite tables.");

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

  // Test 1: Language Filtering (Spanish item "correr" must be ignored)
  const esLexeme = await get("SELECT * FROM lexemes WHERE lemma = 'correr'");
  if (esLexeme) throw new Error("FAIL: Non-English record was not filtered out.");
  console.log("✓ Test 5.1: Language filtering enforced (non-English entries dropped).");

  // Test 2: Pronunciation parsing
  const baseForm = await get("SELECT * FROM forms WHERE surface = 'run' AND phonemic_ipa IS NOT NULL");
  if (!baseForm || baseForm.phonemic_ipa !== "/rʌn/") {
    throw new Error("FAIL: Phonemic IPA /rʌn/ was not recorded on the base form.");
  }
  console.log("✓ Test 5.2: IPA pronunciation correctly associated with base form.");

  // Test 3: Senses and Raw Claims Ledger
  const senses = await all("SELECT * FROM senses WHERE definition LIKE '%swiftly%'");
  if (senses.length !== 1) throw new Error("FAIL: Expected 1 sense matching Wiktionary gloss.");
  const claims = await all("SELECT * FROM claims WHERE source_id = 'WIKTIONARY_KAIKKI_20260805'");
  if (claims.length < 3) throw new Error("FAIL: Source claims not materialized in claims ledger.");
  console.log("✓ Test 5.3: Multiple senses and raw claims ledger populated.");

  // Test 4: Inflected forms separated from Lexeme
  const forms = await all(
    `SELECT f.surface 
     FROM relations r 
     JOIN forms f ON r.object_id = f.id 
     WHERE r.relation_type = 'HAS_FORM' AND r.subject_id = (SELECT id FROM lexemes WHERE lemma = 'run')`
  );
  if (forms.length < 3) throw new Error("FAIL: Expected inflectional forms (runs, running, ran) linked via HAS_FORM.");
  console.log("✓ Test 5.4: Surface forms cleanly linked via HAS_FORM edges.");

  // Test 5: Derivational term linkage with provenance
  const deriv = await get(
    `SELECT r.relation_type, c.source_id 
     FROM relations r
     JOIN relation_claims rc ON r.id = rc.relation_id
     JOIN claims c ON rc.claim_id = c.id
     WHERE r.relation_type = 'DERIVED_FROM'`
  );
  if (!deriv || deriv.source_id !== "WIKTIONARY_KAIKKI_20260805") {
    throw new Error("FAIL: Derivation runner -> run with Wiktionary claim provenance missing.");
  }
  console.log("✓ Test 5.5: Derived terms extracted as DERIVED_FROM edges with provenance.");

  // Clean up
  db.close(() => {
    fs.unlinkSync(dbPath);
    fs.unlinkSync(sampleJsonlPath);
    console.log("\n==================================================");
    console.log("WIKTIONARY STREAMING PARSER VERIFIED. GATE 5 COMPLETE.");
    console.log("==================================================");
  });
}

verify().catch((err) => {
  console.error("\nPhase 5 verification failed:", err);
  process.exit(1);
});
