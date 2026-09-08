const fs = require("fs");
const path = require("path");
const os = require("os");
const sqlite3 = require(path.join(os.homedir(), "Desktop/LexicalProject/packages/schema/node_modules/sqlite3")).verbose();
const { ClaimResolver, QualitySystem, generateUUID } = require("../index");

const schemaSqlPath = path.join(__dirname, "../../../packages/schema/schema.sql");
const dbPath = path.join(__dirname, "test_quality.db");

if (fs.existsSync(dbPath)) fs.unlinkSync(dbPath);

const db = new sqlite3.Database(dbPath);
const schemaSql = fs.readFileSync(schemaSqlPath, "utf8");

async function verify() {
  console.log("Beginning Phase 12: Resolution & Quality System Tests (PRD §57 Gate 12)...\n");

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

  // Seed source table
  await run(`INSERT INTO sources (id, name, version, downloaded_at, sha256, license, attribution_url) 
             VALUES ("OEWN_2025", "Open English WordNet", "2025", "2026-09-04", "hash-oewn", "CC BY 4.0", "url")`);
  await run(`INSERT INTO sources (id, name, version, downloaded_at, sha256, license, attribution_url) 
             VALUES ("WIKTIONARY_KAIKKI", "Kaikki Wiktextract", "2026-08-05", "2026-09-04", "hash-kaikki", "CC BY-SA 4.0", "url")`);

  // 1. Seed competing claims for bank etymology (ADR-002: Zero Silent Merging)
  const bankLexId = generateUUID("lexeme:eng:bank:NOUN");
  await run(
    `INSERT INTO lexemes (id, lemma, normalized_lemma, language, pos, lexeme_key, source_presence, status)
     VALUES (?, "bank", "bank", "eng", "NOUN", "eng:bank:NOUN", "[]", "CANONICAL")`,
    [bankLexId]
  );

  const claimAId = generateUUID("claim:bank:etym:oewn");
  const claimBId = generateUUID("claim:bank:etym:wikt");

  await run(
    `INSERT INTO claims (id, source_id, source_version, subject_type, subject_source_id, predicate, object_type, object_source_id, raw_payload, evidence_type, confidence)
     VALUES (?, "OEWN_2025", "2025", "LEXEME", ?, "ETYMOLOGICALLY_FROM", "ETYMON", "gmw-pro:*banki-", "{}", "EXPLICIT", 0.85)`,
    [claimAId, bankLexId]
  );
  await run(
    `INSERT INTO claims (id, source_id, source_version, subject_type, subject_source_id, predicate, object_type, object_source_id, raw_payload, evidence_type, confidence)
     VALUES (?, "WIKTIONARY_KAIKKI", "2026-08-05", "LEXEME", ?, "ETYMOLOGICALLY_FROM", "ETYMON", "fro:banque", "{}", "EXPLICIT", 0.88)`,
    [claimBId, bankLexId]
  );

  // Execute Resolver
  await ClaimResolver.resolveAllClaims(db);

  // Test 12.1: Disputed relations marked CONFLICTING and UNCERTAIN
  const conflictingRels = await new Promise((resolve, reject) => {
    db.all("SELECT * FROM relations WHERE subject_id = ? AND resolution_status = 'CONFLICTING'", [bankLexId], (err, rows) => {
      if (err) reject(err);
      else resolve(rows);
    });
  });
  if (conflictingRels.length !== 2 || conflictingRels.some(r => r.evidence_type !== "UNCERTAIN")) {
    throw new Error("FAIL: Competing claims must produce relations marked CONFLICTING and UNCERTAIN.");
  }
  console.log("✓ Test 12.1: Disputed claims successfully flagged as CONFLICTING with zero silent merging.");

  // 2. Seed a valid verified relation to test Quality Gates
  const runLexId = generateUUID("lexeme:eng:run:VERB");
  const runFormId = generateUUID("form:run");
  await run(
    `INSERT INTO forms (id, surface, normalized_surface, form_type, source, evidence, confidence)
     VALUES (?, "run", "run", "BASE", "OEWN_2025", "EXPLICIT", 1.0)`,
    [runFormId]
  );
  await run(
    `INSERT INTO lexemes (id, lemma, normalized_lemma, language, pos, lemma_form_id, lexeme_key, source_presence, status)
     VALUES (?, "run", "run", "eng", "VERB", ?, "eng:run:VERB", "[]", "CANONICAL")`,
    [runLexId, runFormId]
  );

  const runClaimId = generateUUID("claim:run:base");
  await run(
    `INSERT INTO claims (id, source_id, source_version, subject_type, subject_source_id, predicate, object_type, object_source_id, raw_payload, evidence_type, confidence)
     VALUES (?, "OEWN_2025", "2025", "LEXEME", "run", "HAS_FORM", "FORM", "run", "{}", "EXPLICIT", 1.0)`,
    [runClaimId]
  );

  const runRelId = generateUUID("rel:run:has_form");
  await run(
    `INSERT INTO relations (id, subject_type, subject_id, relation_type, object_type, object_id, evidence_type, confidence, resolution_status)
     VALUES (?, "LEXEME", ?, "HAS_FORM", "FORM", ?, "EXPLICIT", 1.0, "RESOLVED")`,
    [runRelId, runLexId, runFormId]
  );
  await run(
    `INSERT INTO relation_claims (relation_id, claim_id) VALUES (?, ?)`,
    [runRelId, runClaimId]
  );

  // Execute Quality Gates
  const qualityReport = await QualitySystem.executeQualityGates(db);
  if (!qualityReport.passed) {
    throw new Error("FAIL: Quality gates failed on clean database state: " + JSON.stringify(qualityReport.errors));
  }
  console.log("✓ Test 12.2: Quality Gates (A, B, E) passed on verified clean database.");

  // Test 12.3: Markdown Build Report Generation
  const markdownOutput = QualitySystem.formatReportAsMarkdown(qualityReport);
  if (!markdownOutput.includes("Build & Data Quality Summary Report") || !markdownOutput.includes("Gate A")) {
    throw new Error("FAIL: Markdown build report generation failed formatting check.");
  }
  console.log("✓ Test 12.3: Structured Markdown observability report cleanly generated.");

  // Clean up
  db.close(() => {
    fs.unlinkSync(dbPath);
    console.log("\n==================================================");
    console.log("QUALITY & RESOLUTION SYSTEM VERIFIED. GATE 12 COMPLETE.");
    console.log("==================================================");
  });
}

verify().catch((err) => {
  console.error("\nPhase 12 verification failed:", err);
  process.exit(1);
});
