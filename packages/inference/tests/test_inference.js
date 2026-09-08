const fs = require("fs");
const path = require("path");
const os = require("os");
const sqlite3 = require(path.join(os.homedir(), "Desktop/LexicalProject/packages/schema/node_modules/sqlite3")).verbose();
const { ControlledInferenceEngine, generateUUID } = require("../index");

const schemaSqlPath = path.join(__dirname, "../../../packages/schema/schema.sql");
const dbPath = path.join(__dirname, "test_inference.db");

if (fs.existsSync(dbPath)) fs.unlinkSync(dbPath);

const db = new sqlite3.Database(dbPath);
const schemaSql = fs.readFileSync(schemaSqlPath, "utf8");

async function verify() {
  console.log("Beginning Phase 11: Controlled Inference Engine Tests (PRD §57 Gate 11)...\n");

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

  // Seed source table to satisfy foreign keys
  await run(
    `INSERT INTO sources (id, name, version, downloaded_at, sha256, license, attribution_url)
     VALUES ("INFERENCE_ENGINE", "Controlled Inference Subsystem", "1.0", "2026-09-04", "hash-inf", "Internal", "local")`
  );
  await run(
    `INSERT INTO sources (id, name, version, downloaded_at, sha256, license, attribution_url)
     VALUES ("OEWN_2025", "Open English WordNet", "2025", "2026-09-04", "hash-oewn", "CC BY 4.0", "https://en-word.net/")`
  );

  // 1. Seed candidate pair for valid inference: write (VERB) and rewrite (VERB)
  const writeId = generateUUID("lexeme:eng:write:VERB");
  const rewriteId = generateUUID("lexeme:eng:rewrite:VERB");

  await run(
    `INSERT INTO lexemes (id, lemma, normalized_lemma, language, pos, lexeme_key, source_presence, status)
     VALUES (?, "write", "write", "eng", "VERB", "eng:write:VERB", "[]", "CANONICAL")`,
    [writeId]
  );
  await run(
    `INSERT INTO lexemes (id, lemma, normalized_lemma, language, pos, lexeme_key, source_presence, status)
     VALUES (?, "rewrite", "rewrite", "eng", "VERB", "eng:rewrite:VERB", "[]", "CANONICAL")`,
    [rewriteId]
  );

  // 2. Seed false-relationship regression trap words: go (VERB), goal (NOUN), car (NOUN), carpet (NOUN)
  const goId = generateUUID("lexeme:eng:go:VERB");
  const goalId = generateUUID("lexeme:eng:goal:NOUN");
  const carId = generateUUID("lexeme:eng:car:NOUN");
  const carpetId = generateUUID("lexeme:eng:carpet:NOUN");

  await run(`INSERT INTO lexemes (id, lemma, normalized_lemma, pos, lexeme_key, source_presence, status) VALUES (?, "go", "go", "VERB", "eng:go:VERB", "[]", "CANONICAL")`, [goId]);
  await run(`INSERT INTO lexemes (id, lemma, normalized_lemma, pos, lexeme_key, source_presence, status) VALUES (?, "goal", "goal", "NOUN", "eng:goal:NOUN", "[]", "CANONICAL")`, [goalId]);
  await run(`INSERT INTO lexemes (id, lemma, normalized_lemma, pos, lexeme_key, source_presence, status) VALUES (?, "car", "car", "NOUN", "eng:car:NOUN", "[]", "CANONICAL")`, [carId]);
  await run(`INSERT INTO lexemes (id, lemma, normalized_lemma, pos, lexeme_key, source_presence, status) VALUES (?, "carpet", "carpet", "NOUN", "eng:carpet:NOUN", "[]", "CANONICAL")`, [carpetId]);

  // 3. Seed explicit relation pair to test non-duplication: teach (VERB) -> teacher (NOUN)
  const teachId = generateUUID("lexeme:eng:teach:VERB");
  const teacherId = generateUUID("lexeme:eng:teacher:NOUN");
  await run(`INSERT INTO lexemes (id, lemma, normalized_lemma, pos, lexeme_key, source_presence, status) VALUES (?, "teach", "teach", "VERB", "eng:teach:VERB", "[]", "CANONICAL")`, [teachId]);
  await run(`INSERT INTO lexemes (id, lemma, normalized_lemma, pos, lexeme_key, source_presence, status) VALUES (?, "teacher", "teacher", "NOUN", "eng:teacher:NOUN", "[]", "CANONICAL")`, [teacherId]);

  await run(
    `INSERT INTO relations (id, subject_type, subject_id, relation_type, object_type, object_id, evidence_type, confidence, resolution_status)
     VALUES ("rel-teach-teacher", "LEXEME", ?, "DERIVED_FROM", "LEXEME", ?, "EXPLICIT", 1.0, "RESOLVED")`,
    [teacherId, teachId]
  );

  // Run the Controlled Inference Engine
  const inferences = await ControlledInferenceEngine.inferDerivations(db);
  console.log("✓ Ingested and executed controlled inference rules.");

  // Test 11.1: Valid inferred relation generated with INFERRED evidence type
  const rewriteRel = await get(
    `SELECT r.relation_type, r.evidence_type, r.confidence, c.raw_payload 
     FROM relations r
     JOIN relation_claims rc ON r.id = rc.relation_id
     JOIN claims c ON rc.claim_id = c.id
     WHERE r.subject_id = ? AND r.object_id = ?`,
    [rewriteId, writeId]
  );
  if (!rewriteRel || rewriteRel.evidence_type !== "INFERRED" || rewriteRel.confidence !== 0.75) {
    throw new Error("FAIL: Inferred relation rewrite -> write not created with INFERRED evidence type.");
  }
  const payload = JSON.parse(rewriteRel.raw_payload);
  if (payload.rule !== "PREFIX_RE_VERB" || !payload.evidence_summary) {
    throw new Error("FAIL: Explanation payload missing required inference documentation.");
  }
  console.log("✓ Test 11.1: Valid inferred relation generated, strictly classified as INFERRED with explanation.");

  // Test 11.2: Invariant check: Inferred edge NEVER upgrades to EXPLICIT
  const explicitCheck = await get("SELECT * FROM relations WHERE subject_id = ? AND evidence_type = 'EXPLICIT'", [rewriteId]);
  if (explicitCheck) {
    throw new Error("CRITICAL FAIL: Inferred edge silently upgraded to EXPLICIT! Violates AI Engineering Rule 9.");
  }
  console.log("✓ Test 11.2: Evidence tagging invariant verified (inferred edge remains INFERRED).");

  // Test 11.3: Non-duplication check (Explicit teach -> teacher remains unaffected)
  const teacherRels = await new Promise((resolve, reject) => {
    db.all("SELECT * FROM relations WHERE subject_id = ? AND object_id = ?", [teacherId, teachId], (err, rows) => {
      if (err) reject(err);
      else resolve(rows);
    });
  });
  if (teacherRels.length !== 1 || teacherRels[0].evidence_type !== "EXPLICIT") {
    throw new Error("FAIL: Pre-existing EXPLICIT relation corrupted or duplicated by inference engine.");
  }
  console.log("✓ Test 11.3: Non-duplication invariant verified (pre-existing EXPLICIT relation preserved).");

  // Test Gate D: Regression Trap Confirmation (Zero false inferences)
  const falseGo = await get("SELECT * FROM relations WHERE (subject_id = ? AND object_id = ?) OR (subject_id = ? AND object_id = ?)", [goId, goalId, goalId, goId]);
  const falseCar = await get("SELECT * FROM relations WHERE (subject_id = ? AND object_id = ?) OR (subject_id = ? AND object_id = ?)", [carId, carpetId, carpetId, carId]);
  if (falseGo || falseCar) {
    throw new Error("CRITICAL FAIL: Substring regression trap tripped! go=goal or car=carpet inferred!");
  }
  console.log("✓ Test Gate D: Substring traps successfully blocked (go != goal, car != carpet).");

  // Clean up
  db.close(() => {
    fs.unlinkSync(dbPath);
    console.log("\n==================================================");
    console.log("CONTROLLED INFERENCE ENGINE VERIFIED. GATE 11 COMPLETE.");
    console.log("==================================================");
  });
}

verify().catch((err) => {
  console.error("\nPhase 11 verification failed:", err);
  process.exit(1);
});
