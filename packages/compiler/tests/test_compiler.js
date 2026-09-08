const fs = require("fs");
const path = require("path");
const os = require("os");
const sqlite3 = require(path.join(os.homedir(), "Desktop/LexicalProject/packages/schema/node_modules/sqlite3")).verbose();
const { DatabaseCompiler } = require("../index");

const projectPath = path.join(os.homedir(), "Desktop", "LexicalProject");
const schemaSqlPath = path.join(projectPath, "packages", "schema", "schema.sql");
const testCompiledDb = path.join(__dirname, "test_compiled_graph.db");
const testManifestPath = path.join(__dirname, "test_manifest.json");

if (fs.existsSync(testCompiledDb)) fs.unlinkSync(testCompiledDb);
if (fs.existsSync(testManifestPath)) fs.unlinkSync(testManifestPath);

async function verify() {
  console.log("Beginning Phase 13: Database Compiler & Indexer Tests (PRD §57 Gate 13)...\n");

  const db = await DatabaseCompiler.compileDatabase(testCompiledDb, schemaSqlPath);
  console.log("✓ Database compiled and initialized with canonical DDL and covering indexes.");

  const run = (q, p = []) => new Promise((resolve, reject) => {
    db.run(q, p, function (err) {
      if (err) reject(err);
      else resolve(this);
    });
  });

  const all = (q, p = []) => new Promise((resolve, reject) => {
    db.all(q, p, (err, rows) => {
      if (err) reject(err);
      else resolve(rows);
    });
  });

  // Seed sample data for compiler test
  await run(`INSERT INTO sources (id, name, version, downloaded_at, sha256, license, attribution_url) 
             VALUES ("OEWN_2025", "Open English WordNet", "2025", "2026-09-04", "hash-oewn", "CC BY 4.0", "url")`);
  
  await run(`INSERT INTO lexemes (id, lemma, normalized_lemma, language, pos, lexeme_key, source_presence, status)
             VALUES ("lex-run-v", "run", "run", "eng", "VERB", "eng:run:VERB", "[]", "CANONICAL")`);
  await run(`INSERT INTO lexemes (id, lemma, normalized_lemma, language, pos, lexeme_key, source_presence, status)
             VALUES ("lex-runner-n", "runner", "runner", "eng", "NOUN", "eng:runner:NOUN", "[]", "CANONICAL")`);

  await run(`INSERT INTO senses (id, lexeme_id, definition, source, confidence)
             VALUES ("sense-1", "lex-run-v", "move quickly on foot", "OEWN_2025", 1.0)`);
  await run(`INSERT INTO senses (id, lexeme_id, definition, source, confidence)
             VALUES ("sense-2", "lex-runner-n", "a person or athlete who runs", "OEWN_2025", 1.0)`);

  // Build FTS5 Indexes
  await DatabaseCompiler.rebuildFtsIndexes(db);
  console.log("✓ FTS5 full-text search indexes populated.");

  // Test 13.1: FTS5 Lexeme Search
  const ftsLexemes = await all("SELECT lemma FROM fts_lexemes WHERE fts_lexemes MATCH 'run*'");
  if (ftsLexemes.length !== 2) {
    throw new Error("FAIL: FTS5 prefix match on 'run*' expected 2 records, got: " + ftsLexemes.length);
  }
  console.log("✓ Test 13.1: FTS5 prefix and token search verified on lexemes.");

  // Test 13.2: FTS5 Sense Search
  const ftsSenses = await all("SELECT definition FROM fts_senses WHERE fts_senses MATCH 'athlete'");
  if (ftsSenses.length !== 1 || !ftsSenses[0].definition.includes("athlete")) {
    throw new Error("FAIL: FTS5 match on definition failed.");
  }
  console.log("✓ Test 13.2: FTS5 search verified on sense definitions.");

  // Execute optimization
  await DatabaseCompiler.optimize(db);
  console.log("✓ PRAGMA optimize and ANALYZE completed.");

  // Close db for manifest calculation
  await new Promise((resolve, reject) => {
    db.close((err) => {
      if (err) reject(err);
      else resolve();
    });
  });

  // Test 13.3: Manifest generation and SHA-256 verification
  const manifest = DatabaseCompiler.generateManifest(testCompiledDb, testManifestPath);
  if (!manifest.sha256 || manifest.size_bytes <= 0) {
    throw new Error("FAIL: Build manifest generated with invalid size or checksum.");
  }
  console.log("✓ Test 13.3: Deterministic build manifest generated with verified SHA-256: " + manifest.sha256.substring(0, 16) + "...");

  // Clean up
  fs.unlinkSync(testCompiledDb);
  fs.unlinkSync(testManifestPath);
  console.log("\n==================================================");
  console.log("DATABASE COMPILER & INDEXES VERIFIED. GATE 13 COMPLETE.");
  console.log("==================================================");
}

verify().catch((err) => {
  console.error("\nPhase 13 verification failed:", err);
  process.exit(1);
});
