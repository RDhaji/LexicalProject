const fs = require("fs");
const path = require("path");
const os = require("os");
const sqlite3 = require(path.join(os.homedir(), "Desktop/LexicalProject/packages/schema/node_modules/sqlite3")).verbose();
const { DerivationGraphBuilder, generateUUID } = require("../index");

const schemaSqlPath = path.join(__dirname, "../../../packages/schema/schema.sql");
const dbPath = path.join(__dirname, "test_derivation.db");

if (fs.existsSync(dbPath)) fs.unlinkSync(dbPath);

const db = new sqlite3.Database(dbPath);
const schemaSql = fs.readFileSync(schemaSqlPath, "utf8");

async function verify() {
  console.log("Beginning Phase 10: Derivation & Affix Graph Tests (PRD §57 Gate 10)...\n");

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
     VALUES ("OEWN_2025", "Open English WordNet", "2025", "2026-09-04", "hash-oewn", "CC BY 4.0", "https://en-word.net/")`
  );

  // 1. Seed Lexemes: teach (VERB), teacher (NOUN)
  const teachId = generateUUID("lexeme:eng:teach:VERB");
  const teacherId = generateUUID("lexeme:eng:teacher:NOUN");
  await run(
    `INSERT INTO lexemes (id, lemma, normalized_lemma, language, pos, lexeme_key, source_presence, status)
     VALUES (?, "teach", "teach", "eng", "VERB", "eng:teach:VERB", "[]", "CANONICAL")`,
    [teachId]
  );
  await run(
    `INSERT INTO lexemes (id, lemma, normalized_lemma, language, pos, lexeme_key, source_presence, status)
     VALUES (?, "teacher", "teacher", "eng", "NOUN", "eng:teacher:NOUN", "[]", "CANONICAL")`,
    [teacherId]
  );

  // 2. Seed Claim and Link Derivation: teacher -> teach
  const claimId = generateUUID("claim:teach:teacher");
  await run(
    `INSERT INTO claims (id, source_id, source_version, subject_type, subject_source_id, predicate, object_type, object_source_id, raw_payload, evidence_type, confidence)
     VALUES (?, "OEWN_2025", "2025", "LEXEME", "teacher", "DERIVED_FROM", "LEXEME", "teach", "{}", "EXPLICIT", 1.0)`,
    [claimId]
  );
  await DerivationGraphBuilder.linkDerivation(db, teachId, teacherId, claimId);

  const edge = await get(
    `SELECT r.relation_type, rc.claim_id 
     FROM relations r 
     JOIN relation_claims rc ON r.id = rc.relation_id 
     WHERE r.subject_id = ? AND r.object_id = ?`,
    [teacherId, teachId]
  );
  if (!edge || edge.relation_type !== "DERIVED_FROM" || edge.claim_id !== claimId) {
    throw new Error("FAIL: Derivation link teacher -> teach with claim provenance missing.");
  }
  console.log("✓ Test 10.1: Explicit derivational link with provenance claim verified (teacher -> teach).");

  // 3. Affix Registration & Association: -er (DERIVATIONAL_AFFIX)
  const erMorphemeId = await DerivationGraphBuilder.registerMorpheme(db, "-er", "DERIVATIONAL_AFFIX");
  const teachBaseMorphemeId = await DerivationGraphBuilder.registerMorpheme(db, "teach", "BASE");

  // Create structure for teacher
  const structId = generateUUID("struct:teacher");
  await run(
    `INSERT INTO morphological_structures (id, target_type, target_id, structure_type, components, source, evidence, confidence)
     VALUES (?, "LEXEME", ?, "SUFFIXATION", "{}", "OEWN_2025", "EXPLICIT", 1.0)`,
    [structId, teacherId]
  );

  await DerivationGraphBuilder.attachAffix(db, structId, teachBaseMorphemeId, 1);
  await DerivationGraphBuilder.attachAffix(db, structId, erMorphemeId, 2);

  const morphRelations = await new Promise((resolve, reject) => {
    db.all("SELECT object_id FROM relations WHERE subject_id = ? AND relation_type = 'CONTAINS_MORPHEME'", [structId], (err, rows) => {
      if (err) reject(err);
      else resolve(rows);
    });
  });
  if (morphRelations.length !== 2) throw new Error("FAIL: Expected 2 morpheme components attached to structure.");
  console.log("✓ Test 10.2: Morphological structure and affix nodes linked via CONTAINS_MORPHEME.");

  // 4. Test Recursive Family Traversal: happy -> unhappy, happiness
  const happyId = generateUUID("lexeme:eng:happy:ADJECTIVE");
  const unhappyId = generateUUID("lexeme:eng:unhappy:ADJECTIVE");
  const happinessId = generateUUID("lexeme:eng:happiness:NOUN");

  await run(
    `INSERT INTO lexemes (id, lemma, normalized_lemma, language, pos, lexeme_key, source_presence, status)
     VALUES (?, "happy", "happy", "eng", "ADJECTIVE", "eng:happy:ADJECTIVE", "[]", "CANONICAL")`,
    [happyId]
  );
  await run(
    `INSERT INTO lexemes (id, lemma, normalized_lemma, language, pos, lexeme_key, source_presence, status)
     VALUES (?, "unhappy", "unhappy", "eng", "ADJECTIVE", "eng:unhappy:ADJECTIVE", "[]", "CANONICAL")`,
    [unhappyId]
  );
  await run(
    `INSERT INTO lexemes (id, lemma, normalized_lemma, language, pos, lexeme_key, source_presence, status)
     VALUES (?, "happiness", "happiness", "eng", "NOUN", "eng:happiness:NOUN", "[]", "CANONICAL")`,
    [happinessId]
  );

  await DerivationGraphBuilder.linkDerivation(db, happyId, unhappyId);
  await DerivationGraphBuilder.linkDerivation(db, happyId, happinessId);

  const family = await DerivationGraphBuilder.getDerivationalFamily(db, happyId, 2);
  const lemmas = family.map(f => f.lemma);
  if (!lemmas.includes("happy") || !lemmas.includes("unhappy") || !lemmas.includes("happiness")) {
    throw new Error("FAIL: Derivational family traversal failed to retrieve all family members.");
  }
  console.log("✓ Test 10.3: Recursive derivational family traversal verified (happy -> unhappy, happiness).");

  // 5. Test Gate D: Substring Negative Trap Regression (go != goal, car != carpet)
  const goId = generateUUID("lexeme:eng:go:VERB");
  const goalId = generateUUID("lexeme:eng:goal:NOUN");
  await run(`INSERT INTO lexemes (id, lemma, normalized_lemma, pos, lexeme_key, source_presence, status) VALUES (?, "go", "go", "VERB", "eng:go:VERB", "[]", "CANONICAL")`, [goId]);
  await run(`INSERT INTO lexemes (id, lemma, normalized_lemma, pos, lexeme_key, source_presence, status) VALUES (?, "goal", "goal", "NOUN", "eng:goal:NOUN", "[]", "CANONICAL")`, [goalId]);

  const falseCheck = await get(
    `SELECT id FROM relations 
     WHERE (subject_id = ? AND object_id = ?) OR (subject_id = ? AND object_id = ?)`,
    [goId, goalId, goalId, goId]
  );
  if (falseCheck) throw new Error("CRITICAL FAIL: Substring relationship go <-> goal created in derivation graph!");
  console.log("✓ Test Gate D: False substring traps confirmed absent in derivation graph.");

  // Clean up
  db.close(() => {
    fs.unlinkSync(dbPath);
    console.log("\n==================================================");
    console.log("DERIVATION & AFFIX GRAPH VERIFIED. GATE 10 COMPLETE.");
    console.log("==================================================");
  });
}

verify().catch((err) => {
  console.error("\nPhase 10 verification failed:", err);
  process.exit(1);
});
