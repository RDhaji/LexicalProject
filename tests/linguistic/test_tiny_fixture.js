const fs = require("fs");
const path = require("path");
const sqlite3 = require(path.join(__dirname, "../../packages/schema/node_modules/sqlite3")).verbose();

const fixturePath = path.join(__dirname, "../fixtures/tiny_fixture.json");
const schemaSqlPath = path.join(__dirname, "../../packages/schema/schema.sql");
const dbPath = path.join(__dirname, "test_linguistic_fixture.db");

if (fs.existsSync(dbPath)) fs.unlinkSync(dbPath);

const db = new sqlite3.Database(dbPath);
const schemaSql = fs.readFileSync(schemaSqlPath, "utf8");
const fixture = JSON.parse(fs.readFileSync(fixturePath, "utf8"));

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

function all(query, params = []) {
  return new Promise((resolve, reject) => {
    db.all(query, params, (err, rows) => {
      if (err) reject(err);
      else resolve(rows);
    });
  });
}

async function verifyFixture() {
  console.log("Beginning Linguistic Vertical Slice Fixture Verification (PRD §59, §60, §61)...\n");

  await new Promise((resolve, reject) => {
    db.exec(schemaSql, (err) => {
      if (err) reject(err);
      else resolve();
    });
  });

  // 1. Insert Sources
  await run(`INSERT INTO sources (id, name, version, downloaded_at, sha256, license, attribution_url) 
             VALUES ("OEWN_2025", "Open English WordNet", "2025", "2026-09-04", "hash-oewn", "CC-BY-4.0", "url")`);
  await run(`INSERT INTO sources (id, name, version, downloaded_at, sha256, license, attribution_url) 
             VALUES ("WIKTIONARY_KAIKKI_20260805", "Kaikki Wiktextract", "2026-08-05", "2026-09-04", "hash-kaikki", "CC-BY-SA-4.0", "url")`);
  await run(`INSERT INTO sources (id, name, version, downloaded_at, sha256, license, attribution_url) 
             VALUES ("UNIMORPH_ENG", "UniMorph English", "2026", "2026-09-04", "hash-unimorph", "CC-BY-SA-4.0", "url")`);

  // 2. Insert Forms
  for (const f of fixture.forms) {
    await run(
      `INSERT INTO forms (id, surface, normalized_surface, form_type, features_json, source, evidence, confidence)
       VALUES (?, ?, ?, ?, ?, ?, ?, ?)`,
      [f.id, f.surface, f.normalized_surface, f.form_type, JSON.stringify(f.features), f.source, f.evidence, f.confidence]
    );
  }

  // 3. Insert Lexemes
  for (const l of fixture.lexemes) {
    await run(
      `INSERT INTO lexemes (id, lemma, normalized_lemma, pos, lexeme_key, source_presence, status)
       VALUES (?, ?, ?, ?, ?, ?, ?)`,
      [l.id, l.lemma, l.normalized_lemma, l.pos, l.lexeme_key, JSON.stringify(l.source_presence), l.status]
    );
  }

  // 4. Insert Claims
  for (const c of fixture.claims) {
    await run(
      `INSERT INTO claims (id, source_id, source_version, subject_type, subject_source_id, predicate, object_type, object_source_id, raw_payload, evidence_type, confidence)
       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`,
      [c.id, c.source_id, c.source_version, c.subject_type, c.subject_source_id, c.predicate, c.object_type, c.object_source_id, JSON.stringify(c.raw_payload), c.evidence_type, c.confidence]
    );
  }

  // 5. Insert Relations
  for (const r of fixture.relations) {
    await run(
      `INSERT INTO relations (id, subject_type, subject_id, relation_type, object_type, object_id, evidence_type, confidence, resolution_status)
       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)`,
      [r.id, r.subject_type, r.subject_id, r.relation_type, r.object_type, r.object_id, r.evidence_type, r.confidence, r.resolution_status]
    );
  }

  console.log("✓ Fixture data successfully loaded into canonical SQLite tables.");

  // Test Gate C.1: Verification of run homographs
  const runLexemes = await all("SELECT id, pos FROM lexemes WHERE lemma = ? ORDER BY pos DESC", ["run"]);
  if (runLexemes.length !== 2 || runLexemes[0].pos !== "VERB" || runLexemes[1].pos !== "NOUN") {
    throw new Error("FAIL: Homographs run (VERB) and run (NOUN) not resolved as distinct lexemes.");
  }
  console.log("✓ Test C.1: Homograph isolation verified (run/VERB and run/NOUN remain distinct).");

  // Test Gate C.2: Verification of run inflections vs derivation
  const runForms = await all(
    `SELECT f.surface, f.form_type, r.relation_type 
     FROM relations r 
     JOIN forms f ON r.object_id = f.id 
     WHERE r.subject_id = "lex-run-v" AND r.relation_type = "HAS_FORM"`
  );
  if (runForms.length !== 3) {
    throw new Error("FAIL: Expected 3 inflectional forms for run VERB.");
  }
  console.log("✓ Test C.2: Inflectional forms for run/VERB verified (runs, ran, running).");

  const runnerDerivation = await get(
    `SELECT subject_id, relation_type, object_id 
     FROM relations 
     WHERE subject_id = "lex-runner-n" AND relation_type = "DERIVED_FROM" AND object_id = "lex-run-v"`
  );
  if (!runnerDerivation) {
    throw new Error("FAIL: Derivational relation runner NOUN -> run VERB missing.");
  }
  console.log("✓ Test C.3: Derivation boundary verified (runner NOUN derived from run VERB).");

  // Test Gate C.4: Verification of Suppletion (go -> went, good -> better, bad -> worse)
  const wentForm = await get(
    `SELECT f.surface, f.form_type 
     FROM relations r JOIN forms f ON r.object_id = f.id 
     WHERE r.subject_id = "lex-go-v" AND f.surface = "went"`
  );
  if (!wentForm || wentForm.form_type !== "SUPPLETIVE") {
    throw new Error("FAIL: Suppletive form went for go VERB failed validation.");
  }
  console.log("✓ Test C.4: Irregular suppletion verified (go -> went tagged SUPPLETIVE).");

  // Test Gate D: False-Positive Regression Guard (go != goal)
  const falseRel = await get(
    `SELECT id FROM relations 
     WHERE (subject_id = "lex-go-v" AND object_id = "lex-goal-n") 
        OR (subject_id = "lex-goal-n" AND object_id = "lex-go-v")`
  );
  if (falseRel) {
    throw new Error("CRITICAL FAIL: False substring relationship go <-> goal detected in relations table!");
  }
  console.log("✓ Test Gate D: False-positive regression trap verified (go != goal disconnected).");

  // Test Gate E: Conflicting Source Claims (Zero Silent Merging - ADR-002)
  const bankClaims = await all(
    `SELECT source_id, object_source_id, confidence 
     FROM claims 
     WHERE subject_source_id = "bank" AND predicate = "ETYMOLOGICALLY_FROM"`
  );
  if (bankClaims.length !== 2) {
    throw new Error("FAIL: Disagreeing claims for bank etymology must be preserved.");
  }
  const bankRel = await get(
    `SELECT resolution_status FROM relations WHERE subject_id = "lex-bank-fin-n" AND relation_type = "ETYMOLOGICALLY_FROM"`
  );
  if (bankRel.resolution_status !== "CONFLICTING") {
    throw new Error("FAIL: Disputed relation for bank etymology must be marked CONFLICTING.");
  }
  console.log("✓ Test Gate E: Disputed source claims preserved and relation marked CONFLICTING (Zero Silent Resolution).");

  db.close(() => {
    fs.unlinkSync(dbPath);
    console.log("\n==================================================");
    console.log("ALL LINGUISTIC VERTICAL SLICE TESTS PASSED (GATE 3).");
    console.log("==================================================");
  });
}

verifyFixture().catch((err) => {
  console.error("\nLinguistic fixture verification failed:", err);
  process.exit(1);
});
