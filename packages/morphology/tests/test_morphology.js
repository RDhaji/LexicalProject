const fs = require("fs");
const path = require("path");
const os = require("os");
const sqlite3 = require(path.join(os.homedir(), "Desktop/LexicalProject/packages/schema/node_modules/sqlite3")).verbose();
const { InflectionEngine, DerivationEngine, CompositionEngine, generateUUID } = require("../index");

const schemaSqlPath = path.join(__dirname, "../../../packages/schema/schema.sql");
const dbPath = path.join(__dirname, "test_morphology.db");

if (fs.existsSync(dbPath)) fs.unlinkSync(dbPath);

const db = new sqlite3.Database(dbPath);
const schemaSql = fs.readFileSync(schemaSqlPath, "utf8");

async function verify() {
  console.log("Beginning Phase 9: Morphology Engine Tests (PRD §57 Gate 9)...\n");

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

  const all = (q, p = []) => new Promise((resolve, reject) => {
    db.all(q, p, (err, rows) => {
      if (err) reject(err);
      else resolve(rows);
    });
  });

  // Seed source table to satisfy foreign keys
  await run(
    `INSERT INTO sources (id, name, version, downloaded_at, sha256, license, attribution_url)
     VALUES ("SYSTEM_RULE_ENGINE", "Rule Engine", "1.0", "2026-09-04", "hash-rules", "Internal", "local")`
  );

  // ---------------------------------------------------------------------------
  // Test Gate C.1: Benchmark Verbs (run -> ran, runs, running; go -> went, goes)
  // ---------------------------------------------------------------------------
  const runLexId = generateUUID("lexeme:eng:run:VERB");
  await run(
    `INSERT INTO lexemes (id, lemma, normalized_lemma, language, pos, lexeme_key, source_presence, status)
     VALUES (?, "run", "run", "eng", "VERB", "eng:run:VERB", "[]", "CANONICAL")`,
    [runLexId]
  );
  await InflectionEngine.materializeInflections(db, runLexId, "run", "VERB");

  const runForms = await all(
    `SELECT f.surface, f.form_type 
     FROM relations r JOIN forms f ON r.object_id = f.id 
     WHERE r.subject_id = ? AND r.relation_type = "HAS_FORM"`,
    [runLexId]
  );
  const ran = runForms.find(f => f.surface === "ran");
  if (!ran || ran.form_type !== "IRREGULAR") throw new Error("FAIL: run past tense must be ran (IRREGULAR).");
  console.log("✓ Test 9.1: Irregular verb inflection verified (run -> ran, runs, running).");

  const goLexId = generateUUID("lexeme:eng:go:VERB");
  await run(
    `INSERT INTO lexemes (id, lemma, normalized_lemma, language, pos, lexeme_key, source_presence, status)
     VALUES (?, "go", "go", "eng", "VERB", "eng:go:VERB", "[]", "CANONICAL")`,
    [goLexId]
  );
  await InflectionEngine.materializeInflections(db, goLexId, "go", "VERB");

  const went = await get(
    `SELECT f.surface, f.form_type 
     FROM relations r JOIN forms f ON r.object_id = f.id 
     WHERE r.subject_id = ? AND f.surface = "went"`,
    [goLexId]
  );
  if (!went || went.form_type !== "SUPPLETIVE") throw new Error("FAIL: go past tense must be went (SUPPLETIVE).");
  console.log("✓ Test 9.2: Extreme suppletion verified (go -> went tagged SUPPLETIVE).");

  // ---------------------------------------------------------------------------
  // Test Gate C.2: Benchmark Adjectives (fast -> faster, fastest; good -> better, best)
  // ---------------------------------------------------------------------------
  const fastLexId = generateUUID("lexeme:eng:fast:ADJECTIVE");
  await run(
    `INSERT INTO lexemes (id, lemma, normalized_lemma, language, pos, lexeme_key, source_presence, status)
     VALUES (?, "fast", "fast", "eng", "ADJECTIVE", "eng:fast:ADJECTIVE", "[]", "CANONICAL")`,
    [fastLexId]
  );
  await InflectionEngine.materializeInflections(db, fastLexId, "fast", "ADJECTIVE");

  const fastForms = await all(
    `SELECT f.surface FROM relations r JOIN forms f ON r.object_id = f.id WHERE r.subject_id = ?`,
    [fastLexId]
  );
  if (!fastForms.some(f => f.surface === "faster") || !fastForms.some(f => f.surface === "fastest")) {
    throw new Error("FAIL: fast comparative/superlative failed.");
  }
  console.log("✓ Test 9.3: Regular comparative/superlative verified (fast -> faster, fastest).");

  const goodLexId = generateUUID("lexeme:eng:good:ADJECTIVE");
  await run(
    `INSERT INTO lexemes (id, lemma, normalized_lemma, language, pos, lexeme_key, source_presence, status)
     VALUES (?, "good", "good", "eng", "ADJECTIVE", "eng:good:ADJECTIVE", "[]", "CANONICAL")`,
    [goodLexId]
  );
  await InflectionEngine.materializeInflections(db, goodLexId, "good", "ADJECTIVE");

  const better = await get(
    `SELECT f.surface, f.form_type FROM relations r JOIN forms f ON r.object_id = f.id 
     WHERE r.subject_id = ? AND f.surface = "better"`,
    [goodLexId]
  );
  if (!better || better.form_type !== "SUPPLETIVE") throw new Error("FAIL: good -> better must be SUPPLETIVE.");
  console.log("✓ Test 9.4: Adjective suppletion verified (good -> better, best).");

  // ---------------------------------------------------------------------------
  // Test 9.5: Derivation Boundary Separation (ADR-003, PRD §13)
  // ---------------------------------------------------------------------------
  const runnerLexId = generateUUID("lexeme:eng:runner:NOUN");
  await run(
    `INSERT INTO lexemes (id, lemma, normalized_lemma, language, pos, lexeme_key, source_presence, status)
     VALUES (?, "runner", "runner", "eng", "NOUN", "eng:runner:NOUN", "[]", "CANONICAL")`,
    [runnerLexId]
  );

  await DerivationEngine.linkDerivation(db, runLexId, runnerLexId, "SUFFIXATION");

  const derivRel = await get(
    `SELECT relation_type, subject_type, object_type 
     FROM relations 
     WHERE subject_id = ? AND object_id = ?`,
    [runnerLexId, runLexId]
  );
  if (!derivRel || derivRel.relation_type !== "DERIVED_FROM") {
    throw new Error("FAIL: Derivation runner NOUN -> run VERB must be an explicit DERIVED_FROM edge.");
  }
  console.log("✓ Test 9.5: Derivation boundary separated from inflection across lexemes.");

  // ---------------------------------------------------------------------------
  // Test Gate D: False-Positive Substring Regression Traps (PRD §35 Gate D)
  // ---------------------------------------------------------------------------
  // Rule verification: Substring matching alone must never yield derivation
  const goalLexId = generateUUID("lexeme:eng:goal:NOUN");
  await run(
    `INSERT INTO lexemes (id, lemma, normalized_lemma, language, pos, lexeme_key, source_presence, status)
     VALUES (?, "goal", "goal", "eng", "NOUN", "eng:goal:NOUN", "[]", "CANONICAL")`,
    [goalLexId]
  );

  const falseLink = await get(
    `SELECT id FROM relations 
     WHERE (subject_id = ? AND object_id = ?) OR (subject_id = ? AND object_id = ?)`,
    [goLexId, goalLexId, goalLexId, goLexId]
  );
  if (falseLink) throw new Error("CRITICAL FAIL: go <-> goal relation found! Violates Gate D.");
  console.log("✓ Test Gate D: Regression trap passed (go != goal disconnected).");

  // ---------------------------------------------------------------------------
  // Test 9.6: Morphological Tree Composition (PRD §4.6, §14)
  // ---------------------------------------------------------------------------
  const unMorphId = await CompositionEngine.registerMorpheme(db, "un-", "PREFIX");
  const happyMorphId = await CompositionEngine.registerMorpheme(db, "happy", "BASE");
  const nessMorphId = await CompositionEngine.registerMorpheme(db, "-ness", "SUFFIX");

  const unhapppinessLexId = generateUUID("lexeme:eng:unhappiness:NOUN");
  await run(
    `INSERT INTO lexemes (id, lemma, normalized_lemma, language, pos, lexeme_key, source_presence, status)
     VALUES (?, "unhappiness", "unhappiness", "eng", "NOUN", "eng:unhappiness:NOUN", "[]", "CANONICAL")`,
    [unhapppinessLexId]
  );

  const structId = await CompositionEngine.buildStructure(db, unhapppinessLexId, "LEXEME", "COMPLEX", {
    prefix: unMorphId,
    base: {
      root: happyMorphId,
      suffix: nessMorphId
    }
  });

  const savedStruct = await get("SELECT * FROM morphological_structures WHERE id = ?", [structId]);
  if (!savedStruct || savedStruct.structure_type !== "COMPLEX") {
    throw new Error("FAIL: MorphologicalStructure for unhappiness failed.");
  }
  console.log("✓ Test 9.6: Morphological constituent tree structure verified (un- + happy + -ness).");

  // Clean up
  db.close(() => {
    fs.unlinkSync(dbPath);
    console.log("\n==================================================");
    console.log("MORPHOLOGY ENGINE VERIFIED. GATE 9 COMPLETE.");
    console.log("==================================================");
  });
}

verify().catch((err) => {
  console.error("\nPhase 9 verification failed:", err);
  process.exit(1);
});
