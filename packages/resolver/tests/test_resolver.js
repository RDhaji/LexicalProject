const fs = require("fs");
const path = require("path");
const os = require("os");
const sqlite3 = require(path.join(os.homedir(), "Desktop/LexicalProject/packages/schema/node_modules/sqlite3")).verbose();
const { resolveLexeme, resolveSourceClaims } = require("../index");

const schemaSqlPath = path.join(__dirname, "../../../packages/schema/schema.sql");
const dbPath = path.join(__dirname, "test_resolver.db");

if (fs.existsSync(dbPath)) fs.unlinkSync(dbPath);

const db = new sqlite3.Database(dbPath);
const schemaSql = fs.readFileSync(schemaSqlPath, "utf8");

async function verify() {
  console.log("Beginning Phase 8: Entity Resolution Engine Tests (PRD §57 Gate 8)...\n");

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

  // Seed Required Sources to Satisfy Foreign Key Invariant (PRD §34, Gate B)
  await run(
    `INSERT INTO sources (id, name, version, downloaded_at, sha256, license, attribution_url)
     VALUES (?, ?, ?, ?, ?, ?, ?)`,
    ["OEWN_2025", "Open English WordNet", "2025", "2026-09-04", "hash-oewn", "CC BY 4.0", "https://en-word.net/"]
  );
  await run(
    `INSERT INTO sources (id, name, version, downloaded_at, sha256, license, attribution_url)
     VALUES (?, ?, ?, ?, ?, ?, ?)`,
    ["WIKTIONARY_KAIKKI_20260805", "Kaikki Wiktextract", "2026-08-05", "2026-09-04", "hash-kaikki", "CC BY-SA 4.0", "https://kaikki.org/"]
  );

  // Test 1: Cross-source resolution of identical lexeme (run VERB from OEWN and Wiktionary)
  const res1 = await resolveLexeme(db, { lemma: "run", pos: "VERB", source_id: "OEWN_2025" });
  if (res1.status !== "CREATED") throw new Error("FAIL: First assertion of run/VERB must create canonical lexeme.");

  const res2 = await resolveLexeme(db, { lemma: "run", pos: "VERB", source_id: "WIKTIONARY_KAIKKI_20260805" });
  if (res2.status !== "EXISTING" || res2.id !== res1.id) {
    throw new Error("FAIL: Second assertion of run/VERB from Wiktionary must resolve to the identical UUID.");
  }

  const runLex = await get("SELECT source_presence FROM lexemes WHERE id = ?", [res1.id]);
  const sources = JSON.parse(runLex.source_presence);
  if (!sources.includes("OEWN_2025") || !sources.includes("WIKTIONARY_KAIKKI_20260805")) {
    throw new Error("FAIL: Source presence array must track both authoritative sources.");
  }
  console.log("✓ Test 8.1: Cross-source entity unification verified (same lemma+POS unifies cleanly).");

  // Test 2: Homograph Isolation Invariant (run VERB vs run NOUN)
  const resNoun = await resolveLexeme(db, { lemma: "run", pos: "NOUN", source_id: "OEWN_2025" });
  if (resNoun.id === res1.id) {
    throw new Error("CRITICAL FAIL: run NOUN collapsed into run VERB! Violates PRD §4.1 and §11.");
  }

  const distinctCount = await get("SELECT COUNT(*) as count FROM lexemes WHERE normalized_lemma = 'run'");
  if (distinctCount.count !== 2) throw new Error("FAIL: Expected exactly 2 distinct lexemes for homograph run.");
  console.log("✓ Test 8.2: Homograph separation verified (run/VERB and run/NOUN remain distinct entities).");

  // Test 3: Heterogeneous Homograph Disambiguation (bank financial vs bank river edge)
  const bankFin = await resolveLexeme(db, {
    lemma: "bank",
    pos: "NOUN",
    homograph_disambiguator: "financial",
    source_id: "OEWN_2025"
  });

  const bankRiv = await resolveLexeme(db, {
    lemma: "bank",
    pos: "NOUN",
    homograph_disambiguator: "river",
    source_id: "OEWN_2025"
  });

  if (bankFin.id === bankRiv.id) {
    throw new Error("CRITICAL FAIL: Semantic homographs for bank collapsed into single node!");
  }
  console.log("✓ Test 8.3: Semantic homograph disambiguation verified (bank[fin] != bank[riv]).");

  // Test 4: Cross-Source Claim Alignment & Provenance Confirmation (PRD §18, §19, ADR-002)
  const runner = await resolveLexeme(db, { lemma: "runner", pos: "NOUN", source_id: "OEWN_2025" });

  await run(
    `INSERT INTO claims (id, source_id, source_version, subject_type, subject_source_id, predicate, object_type, object_source_id, raw_payload, evidence_type, confidence)
     VALUES ("c-deriv-1", "OEWN_2025", "2025", "LEXEME", "runner", "DERIVED_FROM", "LEXEME", "run", "{}", "EXPLICIT", 1.0)`
  );
  await run(
    `INSERT INTO claims (id, source_id, source_version, subject_type, subject_source_id, predicate, object_type, object_source_id, raw_payload, evidence_type, confidence)
     VALUES ("c-deriv-2", "WIKTIONARY_KAIKKI_20260805", "2026-08-05", "LEXEME", "runner", "DERIVED_FROM", "LEXEME", "run", "{}", "EXPLICIT", 0.9)`
  );

  await run(
    `INSERT INTO relations (id, subject_type, subject_id, relation_type, object_type, object_id, evidence_type, confidence, resolution_status)
     VALUES ("rel-runner-run", "LEXEME", ?, "DERIVED_FROM", "LEXEME", ?, "EXPLICIT", 0.9, "RESOLVED")`,
    [runner.id, res1.id]
  );

  await resolveSourceClaims(db);

  const resolvedRel = await get("SELECT confidence, resolution_status FROM relations WHERE id = 'rel-runner-run'");
  if (resolvedRel.confidence !== 1.0 || resolvedRel.resolution_status !== "RESOLVED") {
    throw new Error("FAIL: Cross-source agreement did not boost relation confidence.");
  }
  console.log("✓ Test 8.4: Cross-source claim resolution verified (multi-source agreement boosted confidence).");

  db.close(() => {
    fs.unlinkSync(dbPath);
    console.log("\n==================================================");
    console.log("ENTITY RESOLUTION ENGINE VERIFIED. GATE 8 COMPLETE.");
    console.log("==================================================");
  });
}

verify().catch((err) => {
  console.error("\nPhase 8 verification failed:", err);
  process.exit(1);
});
