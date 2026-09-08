const fs = require("fs");
const path = require("path");
const crypto = require("crypto");
const os = require("os");
const sqlite3 = require(path.join(os.homedir(), "Desktop/LexicalProject/packages/schema/node_modules/sqlite3")).verbose();

class DatabaseCompiler {
  /**
   * Compiles canonical database tables, creates covering indexes, and builds FTS5 structures.
   * Conforms strictly to schema.sql and ONTOLOGY.md.
   */
  static async compileDatabase(targetDbPath, schemaSqlPath) {
    if (fs.existsSync(targetDbPath)) {
      fs.unlinkSync(targetDbPath);
    }

    const db = new sqlite3.Database(targetDbPath);
    const schemaSql = fs.readFileSync(schemaSqlPath, "utf8");

    const exec = (sql) => new Promise((resolve, reject) => {
      db.exec(sql, (err) => {
        if (err) reject(err);
        else resolve();
      });
    });

    // 1. Execute Canonical DDL Schema
    await exec(schemaSql);

    // 2. Add covering B-Trees conforming to ONTOLOGY.md (no extraneous or non-existent columns)
    await exec(`
      CREATE INDEX IF NOT EXISTS idx_covering_lexemes_lemma ON lexemes(normalized_lemma, pos, id);
      CREATE INDEX IF NOT EXISTS idx_covering_forms_surface ON forms(normalized_surface, form_type, id);
      CREATE INDEX IF NOT EXISTS idx_covering_relations_adj ON relations(subject_id, relation_type, object_id);
    `);

    return db;
  }

  /**
   * Synchronizes FTS5 virtual tables from canonical tables.
   */
  static async rebuildFtsIndexes(db) {
    const run = (q, p = []) => new Promise((resolve, reject) => {
      db.run(q, p, function (err) {
        if (err) reject(err);
        else resolve(this);
      });
    });

    // Populate Lexeme FTS5 index
    await run(`
      INSERT INTO fts_lexemes (rowid, lemma, normalized_lemma)
      SELECT rowid, lemma, normalized_lemma FROM lexemes
    `);

    // Populate Sense FTS5 index
    await run(`
      INSERT INTO fts_senses (rowid, definition)
      SELECT rowid, definition FROM senses
    `);
  }

  /**
   * Optimizes compiled database: executes ANALYZE and VACUUM.
   */
  static async optimize(db) {
    const exec = (sql) => new Promise((resolve, reject) => {
      db.exec(sql, (err) => {
        if (err) reject(err);
        else resolve();
      });
    });

    await exec("PRAGMA optimize;");
    await exec("ANALYZE;");
  }

  /**
   * Generates build manifest with SHA-256 hash.
   */
  static generateManifest(dbFilePath, outputPath) {
    const fileBuffer = fs.readFileSync(dbFilePath);
    const hashSum = crypto.createHash("sha256").update(fileBuffer).digest("hex");
    const stat = fs.statSync(dbFilePath);

    const manifest = {
      database_name: "lexical_graph.db",
      compiled_at: new Date().toISOString(),
      size_bytes: stat.size,
      sha256: hashSum,
      version: "1.0.0"
    };

    fs.writeFileSync(outputPath, JSON.stringify(manifest, null, 2) + "\n", "utf8");
    return manifest;
  }
}

module.exports = { DatabaseCompiler };
