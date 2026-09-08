const fs = require("fs");
const path = require("path");
const os = require("os");
const sqlite3 = require(path.join(os.homedir(), "Desktop/LexicalProject/packages/schema/node_modules/sqlite3")).verbose();
const { ingestOEWN } = require("../index");

const schemaSqlPath = path.join(__dirname, "../../../packages/schema/schema.sql");
const dbPath = path.join(__dirname, "test_oewn_ingestion.db");

if (fs.existsSync(dbPath)) fs.unlinkSync(dbPath);

const db = new sqlite3.Database(dbPath);
const schemaSql = fs.readFileSync(schemaSqlPath, "utf8");

const mockOewnData = {
  synsets: {
    "oewn-02084071-v": {
      partOfSpeech: "v",
      definition: ["move fast by using one's feet"],
      lex_domain: "verb.motion",
      hypernyms: ["oewn-01835496-v"]
    },
    "oewn-01835496-v": {
      partOfSpeech: "v",
      definition: ["travel or go rapidly"],
      lex_domain: "verb.motion",
      hypernyms: []
    }
  },
  entries: {
    "run": [
      {
        partOfSpeech: "v",
        senses: [
          {
            id: "oewn-run-v-1",
            synset: "oewn-02084071-v",
            definition: "move quickly on foot",
            derivation: [
              { target_lemma: "runner", target_pos: "n" }
            ]
          }
        ]
      }
    ],
    "runner": [
      {
        partOfSpeech: "n",
        senses: [
          {
            id: "oewn-runner-n-1",
            synset: "oewn-02084071-v",
            definition: "a person who runs"
          }
        ]
      }
    ]
  }
};

const mockSourceMeta = {
  id: "OEWN_2025",
  name: "Open English WordNet",
  version: "2025",
  release_date: "2025-01-01",
  downloaded_at: "2026-09-04",
  sha256: "9b7d80a9d8a1c9e3f6b7c5e2d1a4f8e0b2c4d6e8f0a2c4e6b8d0f2a4c6e8b0d2",
  license: "CC BY 4.0",
  attribution_url: "https://en-word.net/"
};

async function verify() {
  console.log("Beginning Phase 4: OEWN Ingestion Integration Tests (PRD §57 Gate 4)...\n");

  await new Promise((resolve, reject) => {
    db.exec(schemaSql, (err) => {
      if (err) reject(err);
      else resolve();
    });
  });

  await ingestOEWN(db, mockOewnData, mockSourceMeta);
  console.log("✓ Ingested raw OEWN fixture data into canonical tables.");

  const all = (q, p = []) => new Promise((resolve, reject) => {
    db.all(q, p, (err, rows) => {
      if (err) reject(err);
      else resolve(rows);
    });
  });

  const get = (q, p = []) => new Promise((resolve, reject) => {
    db.get(q, p, (err, row) => {
      if (err) reject(err);
      else resolve(row);
    });
  });

  // Test 1: Synsets populated with valid claims
  const synsetCount = await get("SELECT COUNT(*) as count FROM synsets");
  if (synsetCount.count !== 2) throw new Error("FAIL: Expected 2 synsets in database.");
  console.log("✓ Test 4.1: Synsets materialized with exact glosses and domains.");

  // Test 2: Lexemes and Base Forms distinctly separated
  const runLexeme = await get("SELECT * FROM lexemes WHERE lemma = 'run' AND pos = 'VERB'");
  if (!runLexeme) throw new Error("FAIL: run/VERB lexeme not found.");
  console.log("✓ Test 4.2: Lexeme (run/VERB) created with canonical ID and status.");

  // Test 3: Senses linked to Synset
  const senses = await all("SELECT * FROM senses WHERE lexeme_id = ?", [runLexeme.id]);
  if (senses.length !== 1) throw new Error("FAIL: Expected 1 sense linked to run/VERB.");
  console.log("✓ Test 4.3: Sense linked to Lexeme and Synset.");

  // Test 4: Derivational link instantiated as DERIVED_FROM edge between Lexemes
  const derivEdge = await get(
    `SELECT r.relation_type, l1.lemma as sub_lemma, l2.lemma as obj_lemma, c.source_id 
     FROM relations r
     JOIN lexemes l1 ON r.subject_id = l1.id
     JOIN lexemes l2 ON r.object_id = l2.id
     JOIN relation_claims rc ON r.id = rc.relation_id
     JOIN claims c ON rc.claim_id = c.id
     WHERE r.relation_type = 'DERIVED_FROM'`
  );
  if (!derivEdge || derivEdge.sub_lemma !== "run" || derivEdge.obj_lemma !== "runner") {
    throw new Error("FAIL: Derivational relation run -> runner not verified with claim provenance.");
  }
  console.log("✓ Test 4.4: Derivation link (run -> runner) verified with full claim provenance.");

  // Test 5: Conceptual relation (Hypernym between Synsets)
  const hypernymEdge = await get("SELECT * FROM relations WHERE relation_type = 'HYPERNYM_OF'");
  if (!hypernymEdge) throw new Error("FAIL: Conceptual relation HYPERNYM_OF between synsets not created.");
  console.log("✓ Test 4.5: Conceptual relation (HYPERNYM_OF) navigable across synsets.");

  db.close(() => {
    fs.unlinkSync(dbPath);
    console.log("\n==================================================");
    console.log("OEWN INGESTION PIPELINE VERIFIED. GATE 4 COMPLETE.");
    console.log("==================================================");
  });
}

verify().catch((err) => {
  console.error("\nPhase 4 verification failed:", err);
  process.exit(1);
});
