const fs = require("fs");
const path = require("path");
const os = require("os");
const sqlite3 = require(path.join(os.homedir(), "Desktop/LexicalProject/packages/schema/node_modules/sqlite3")).verbose();
const { LexicalQueryService } = require("../src/query_service");
const { UserWorkspaceService } = require("../src/workspace_service");
const { LexicalExplorerApp } = require("../public/app");

const compiledDbPath = path.join(os.homedir(), "Desktop/LexicalProject/data/compiled/lexical_graph.db");
const testUserDbPath = path.join(__dirname, "test_m12_user.db");

if (fs.existsSync(testUserDbPath)) fs.unlinkSync(testUserDbPath);

async function runMilestone12Suite() {
  console.log("Executing Milestone 12 Client Integration & UI Shell Suite...");

  const lexDb = new sqlite3.Database(compiledDbPath, sqlite3.OPEN_READONLY);
  const queryService = new LexicalQueryService(lexDb);
  const app = new LexicalExplorerApp(queryService, UserWorkspaceService);

  // 1. Autocomplete Search Integration
  const searchResults = await app.handleSearchInput("run");
  if (!searchResults || searchResults.length === 0) {
    throw new Error("Search failed: No results returned for prefix 'run'");
  }
  const topMatch = searchResults[0];
  console.log(`[PASS] Autocomplete Search: returned ${searchResults.length} matches (Top: ${topMatch.lemma}, POS: ${topMatch.pos})`);

  // 2. Word Page Aggregator Verification
  const wordModel = await app.loadWordPage(topMatch.id);
  if (!wordModel || !wordModel.lexeme) {
    throw new Error("Word Page failed: Lexeme record missing");
  }
  console.log(`[PASS] Word Page Aggregator: loaded '${wordModel.lexeme.lemma}' with ${wordModel.senses.length} senses, ${wordModel.inflectedForms.length} inflected forms`);

  // 3. Epistemic Connection Explanation Subsystem
  if (wordModel.derivationalLinks && wordModel.derivationalLinks.length > 0) {
    const relId = wordModel.derivationalLinks[0].relation_id;
    const explanation = await app.explainRelation(relId);
    if (!explanation || !explanation.relation) {
      throw new Error("Connection explanation failed: Relation payload missing");
    }
    console.log(`[PASS] Provenance Modal: verified relation ${relId} (Evidence: ${explanation.relation.evidence_type}, Claims: ${explanation.claims.length})`);
  } else {
    const sampleRel = await queryService._get("SELECT id FROM relations LIMIT 1");
    if (sampleRel) {
      const explanation = await app.explainRelation(sampleRel.id);
      if (!explanation || !explanation.relation) throw new Error("Relation explanation failed");
      console.log(`[PASS] Provenance Modal: verified relation ${sampleRel.id} (Evidence: ${explanation.relation.evidence_type})`);
    }
  }

  // 4. User Workspace Decoupling Invariant Verification (PRD §39, §63, ADR-006)
  const userDb = await UserWorkspaceService.initWorkspace(testUserDbPath);
  const saved = await app.saveCurrentToWorkspace(userDb);
  if (!saved) throw new Error("User workspace save operation failed");

  const favorites = await UserWorkspaceService.getFavorites(userDb);
  if (favorites.length !== 1 || favorites[0].lexeme_id !== topMatch.id) {
    throw new Error("Workspace integrity failed: favorite entry mismatch");
  }

  const fkCheck = await new Promise((resolve) => {
    userDb.all("PRAGMA foreign_key_list(user_favorites)", (err, rows) => resolve(rows || []));
  });
  if (fkCheck.length > 0) {
    throw new Error("CRITICAL INVARIANT VIOLATION: foreign keys found in user_workspace.db referencing main graph!");
  }
  console.log("[PASS] User Workspace Decoupling: Zero cross-database FKs attested (ADR-006 compliant)");

  lexDb.close();
  userDb.close();
  fs.unlinkSync(testUserDbPath);

  console.log("[GATE PASSED] Milestone 12 integration and client shell verified with 100% compliance.");
}

runMilestone12Suite().catch((err) => {
  console.error("[GATE FAILED] Milestone 12 execution failed:", err);
  process.exit(1);
});
