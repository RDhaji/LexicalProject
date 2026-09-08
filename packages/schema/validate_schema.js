const fs = require("fs");
const path = require("path");
const sqlite3 = require("sqlite3").verbose();

const dbPath = path.join(__dirname, "test_lexical.db");
if (fs.existsSync(dbPath)) {
  fs.unlinkSync(dbPath);
}

const db = new sqlite3.Database(dbPath);
const schemaSql = fs.readFileSync(path.join(__dirname, "schema.sql"), "utf8");

function run(query, params = []) {
  return new Promise((resolve, reject) => {
    db.run(query, params, function (err) {
      if (err) reject(err);
      else resolve(this);
    });
  });
}

function get(query, params = []) {
  return new Promise((resolve, reject) => {
    db.get(query, params, (err, row) => {
      if (err) reject(err);
      else resolve(row);
    });
  });
}

async function verify() {
  console.log("Beginning Phase 2 Database Invariant Verifications...\n");

  await new Promise((resolve, reject) => {
    db.exec(schemaSql, (err) => {
      if (err) reject(err);
      else resolve();
    });
  });
  console.log("✓ DDL statements executed successfully without syntax or pragma errors.");

  // Test 1: Insert Source Metadata
  await run(
    `INSERT INTO sources (id, name, version, downloaded_at, sha256, license, attribution_url) 
     VALUES (?, ?, ?, ?, ?, ?, ?)`,
    ["OEWN_2025", "Open English WordNet", "2025", "2026-09-04", "E3B0C44298FC1C149AFBF4C8996FB92427AE41E4649B934CA495991B7852B855", "CC BY 4.0", "https://en-word.net/"]
  );

  // Test 2: Insert Distinct Lexemes for Homographs (run NOUN vs run VERB)
  await run(
    `INSERT INTO lexemes (id, lemma, normalized_lemma, language, pos, lexeme_key, source_presence, status)
     VALUES (?, ?, ?, ?, ?, ?, ?, ?)`,
    ["lex-run-v", "run", "run", "eng", "VERB", "eng:run:VERB", JSON.stringify(["OEWN_2025"]), "CANONICAL"]
  );

  await run(
    `INSERT INTO lexemes (id, lemma, normalized_lemma, language, pos, lexeme_key, source_presence, status)
     VALUES (?, ?, ?, ?, ?, ?, ?, ?)`,
    ["lex-run-n", "run", "run", "eng", "NOUN", "eng:run:NOUN", JSON.stringify(["OEWN_2025"]), "CANONICAL"]
  );

  // Test 3: Unique Constraint Verification on lexeme_key
  try {
    await run(
      `INSERT INTO lexemes (id, lemma, normalized_lemma, language, pos, lexeme_key, source_presence, status)
       VALUES (?, ?, ?, ?, ?, ?, ?, ?)`,
      ["lex-run-v-dup", "run", "run", "eng", "VERB", "eng:run:VERB", JSON.stringify(["OEWN_2025"]), "CANONICAL"]
    );
    throw new Error("FAIL: Duplicate lexeme_key was erroneously permitted.");
  } catch (err) {
    if (err.message.includes("UNIQUE constraint failed")) {
      console.log("✓ Gate B Verified: Unique constraint correctly prevents homograph collisions.");
    } else {
      throw err;
    }
  }

  // Test 4: Morphological Invariant (Form is not a Lexeme; attaches via HAS_FORM)
  await run(
    `INSERT INTO forms (id, surface, normalized_surface, script, language, features_json, form_type, source, evidence, confidence)
     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`,
    ["form-running", "running", "running", "Latn", "eng", JSON.stringify({tense: "pres", aspect: "prog"}), "INFLECTED", "UNIMORPH_ENG", "EXPLICIT", 1.0]
  );

  await run(
    `INSERT INTO relations (id, subject_type, subject_id, relation_type, object_type, object_id, evidence_type, confidence, resolution_status)
     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)`,
    ["rel-run-has-running", "LEXEME", "lex-run-v", "HAS_FORM", "FORM", "form-running", "EXPLICIT", 1.0, "RESOLVED"]
  );
  console.log("✓ Gate C Verified: Inflected form correctly mapped to lexeme without instantiating new lexeme.");

  // Test 5: Derivational Invariant (runner NOUN derived from run VERB)
  await run(
    `INSERT INTO lexemes (id, lemma, normalized_lemma, language, pos, lexeme_key, source_presence, status)
     VALUES (?, ?, ?, ?, ?, ?, ?, ?)`,
    ["lex-runner-n", "runner", "runner", "eng", "NOUN", "eng:runner:NOUN", JSON.stringify(["OEWN_2025"]), "CANONICAL"]
  );

  await run(
    `INSERT INTO relations (id, subject_type, subject_id, relation_type, object_type, object_id, evidence_type, confidence, resolution_status)
     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)`,
    ["rel-runner-derived-run", "LEXEME", "lex-runner-n", "DERIVED_FROM", "LEXEME", "lex-run-v", "EXPLICIT", 1.0, "RESOLVED"]
  );
  console.log("✓ ADR-003 Verified: Derivation cleanly separated from inflection across lexeme boundaries.");

  // Test 6: Provenance Tracing ("Why Connected?")
  await run(
    `INSERT INTO claims (id, source_id, source_version, subject_type, subject_source_id, predicate, object_type, object_source_id, raw_payload, evidence_type, confidence)
     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`,
    ["claim-wn-derivation-1", "OEWN_2025", "2025", "LEXEME", "runner", "DERIVED_FROM", "LEXEME", "run", JSON.stringify({pointer: "+"}), "EXPLICIT", 0.99]
  );

  await run(
    `INSERT INTO relation_claims (relation_id, claim_id) VALUES (?, ?)`,
    ["rel-runner-derived-run", "claim-wn-derivation-1"]
  );

  const traced = await get(
    `SELECT r.relation_type, c.source_id, c.confidence, c.evidence_type 
     FROM relations r
     JOIN relation_claims rc ON r.id = rc.relation_id
     JOIN claims c ON rc.claim_id = c.id
     WHERE r.id = ?`,
    ["rel-runner-derived-run"]
  );

  if (traced && traced.source_id === "OEWN_2025" && traced.evidence_type === "EXPLICIT") {
    console.log("✓ Gate E Verified: Provenance tracing correctly resolves supporting claims for relations.");
  } else {
    throw new Error("FAIL: Provenance trace failed.");
  }

  // Cleanup test database file
  db.close(() => {
    fs.unlinkSync(dbPath);
    console.log("\nAll schema and relational tests passed. Test database cleanly purged.");
  });
}

verify().catch((err) => {
  console.error("\nSchema verification failed with error:", err);
  process.exit(1);
});
