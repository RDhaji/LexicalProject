const fs = require("fs");
const path = require("path");
const os = require("os");
const sqlite3 = require(path.join(os.homedir(), "Desktop/LexicalProject/packages/schema/node_modules/sqlite3")).verbose();
const { LexicalQueryService } = require("../src/query_service");
const { UserWorkspaceService } = require("../src/workspace_service");

const schemaSqlPath = path.join(__dirname, "../../../packages/schema/schema.sql");
const testLexDbPath = path.join(__dirname, "test_pwa_lexical.db");
const testUserDbPath = path.join(__dirname, "test_pwa_user.db");

if (fs.existsSync(testLexDbPath)) fs.unlinkSync(testLexDbPath);
if (fs.existsSync(testUserDbPath)) fs.unlinkSync(testUserDbPath);

const lexDb = new sqlite3.Database(testLexDbPath);
const schemaSql = fs.readFileSync(schemaSqlPath, "utf8");

async function verify() {
  console.log("Beginning Phase 14: Client PWA & Query Engine Tests (PRD §57 Gate 14)...\n");

  await new Promise((resolve, reject) => {
    lexDb.exec(schemaSql, (err) => {
      if (err) reject(err);
      else resolve();
    });
  });

  const run = (q, p = []) => new Promise((resolve, reject) => {
    lexDb.run(q, p, function (err) {
      if (err) reject(err);
      else resolve(this);
    });
  });

  await run(`INSERT INTO sources (id, name, version, downloaded_at, sha256, license, attribution_url)
             VALUES ("OEWN_2025", "Open English WordNet", "2025", "2026-09-04", "hash-oewn", "CC BY 4.0", "url")`);

  await run(
    `INSERT INTO lexemes (id, lemma, normalized_lemma, pos, lexeme_key, source_presence, frequency_summary, status)
     VALUES ("lex-run-v", "run", "run", "VERB", "eng:run:VERB", "[]", json('{"tier":"VERY_COMMON","zipf_score":7.46}'), "CANONICAL")`
  );
  await run(
    `INSERT INTO lexemes (id, lemma, normalized_lemma, pos, lexeme_key, source_presence, frequency_summary, status)
     VALUES ("lex-runner-n", "runner", "runner", "NOUN", "eng:runner:NOUN", "[]", json('{"tier":"COMMON","zipf_score":4.2}'), "CANONICAL")`
  );

  await run(`INSERT INTO forms (id, surface, normalized_surface, form_type, source, evidence, confidence)
             VALUES ("form-run", "run", "run", "BASE", "OEWN_2025", "EXPLICIT", 1.0)`);
  await run(`INSERT INTO forms (id, surface, normalized_surface, form_type, source, evidence, confidence)
             VALUES ("form-running", "running", "running", "INFLECTED", "UNIMORPH_ENG", "EXPLICIT", 1.0)`);

  await run(`INSERT INTO relations (id, subject_type, subject_id, relation_type, object_type, object_id, evidence_type, confidence, resolution_status)
             VALUES ("rel-has-base", "LEXEME", "lex-run-v", "HAS_FORM", "FORM", "form-run", "EXPLICIT", 1.0, "RESOLVED")`);
  await run(`INSERT INTO relations (id, subject_type, subject_id, relation_type, object_type, object_id, evidence_type, confidence, resolution_status)
             VALUES ("rel-has-inflect", "LEXEME", "lex-run-v", "HAS_FORM", "FORM", "form-running", "EXPLICIT", 1.0, "RESOLVED")`);

  await run(`INSERT INTO claims (id, source_id, source_version, subject_type, subject_source_id, predicate, object_type, object_source_id, raw_payload, evidence_type, confidence)
             VALUES ("claim-deriv", "OEWN_2025", "2025", "LEXEME", "runner", "DERIVED_FROM", "LEXEME", "run", json('{"pointer":"+"}'), "EXPLICIT", 1.0)`);
  await run(`INSERT INTO relations (id, subject_type, subject_id, relation_type, object_type, object_id, evidence_type, confidence, resolution_status)
             VALUES ("rel-deriv-1", "LEXEME", "lex-runner-n", "DERIVED_FROM", "LEXEME", "lex-run-v", "EXPLICIT", 1.0, "RESOLVED")`);
  await run(`INSERT INTO relation_claims (relation_id, claim_id) VALUES ("rel-deriv-1", "claim-deriv")`);

  await run(`INSERT INTO senses (id, lexeme_id, definition, source, confidence)
             VALUES ("sense-run-1", "lex-run-v", "move quickly on foot", "OEWN_2025", 1.0)`);

  const queryService = new LexicalQueryService(lexDb);

  // Test 14.1: Fast Autocomplete Prefix Search
  const searchResults = await queryService.searchPrefix("ru", 10);
  if (searchResults.length !== 2 || searchResults[0].lemma !== "run") {
    throw new Error("FAIL: Prefix search ranking failed. Expected run ranked first.");
  }
  console.log("✓ Test 14.1: Fast prefix autocomplete and frequency ranking verified.");

  // Test 14.2: Word Page Aggregator
  const wordModel = await queryService.getWordDetails("lex-run-v");
  if (!wordModel || !wordModel.baseForm || wordModel.senses.length !== 1 || wordModel.inflectedForms.length !== 1) {
    throw new Error("FAIL: Word details view model incomplete.");
  }
  console.log("✓ Test 14.2: Word Page Aggregator verified (base form, senses, inflected forms).");

  // Test 14.3: Connection Explanation Subsystem
  const explanation = await queryService.explainConnection("rel-deriv-1");
  if (!explanation || explanation.claims.length !== 1 || explanation.claims[0].source_name !== "Open English WordNet") {
    throw new Error("FAIL: Connection explanation provenance failed.");
  }
  console.log("✓ Test 14.3: Connection explanation modal provenance lookup verified.");

  // Test 14.4: User Workspace Decoupling Invariant (PRD §39, ADR-006)
  const userDb = await UserWorkspaceService.initWorkspace(testUserDbPath);
  await UserWorkspaceService.addFavorite(userDb, "lex-run-v", "run");
  const favorites = await UserWorkspaceService.getFavorites(userDb);
  if (favorites.length !== 1 || favorites[0].lemma !== "run") {
    throw new Error("FAIL: User workspace persistence failed.");
  }

  const fkCheck = await new Promise((resolve) => {
    userDb.all("PRAGMA foreign_key_list(user_favorites)", (err, rows) => resolve(rows || []));
  });
  if (fkCheck.length > 0) {
    throw new Error("CRITICAL FAIL: user_workspace contains foreign key to distribution database!");
  }
  console.log("✓ Test 14.4: User partition isolation verified (zero cross-database foreign keys).");

  lexDb.close();
  userDb.close();
  fs.unlinkSync(testLexDbPath);
  fs.unlinkSync(testUserDbPath);

  console.log("\n==================================================");
  console.log("CLIENT PWA & QUERY SUBSYSTEM VERIFIED. GATE 14 COMPLETE.");
  console.log("==================================================");
}

verify().catch((err) => {
  console.error("\nPhase 14 verification failed:", err);
  process.exit(1);
});
