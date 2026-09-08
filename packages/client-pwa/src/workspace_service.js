const sqlite3 = require(require("path").join(require("os").homedir(), "Desktop/LexicalProject/packages/schema/node_modules/sqlite3")).verbose();

class UserWorkspaceService {
  static async initWorkspace(dbPath) {
    const db = new sqlite3.Database(dbPath);

    await new Promise((resolve, reject) => {
      db.exec(`
        PRAGMA journal_mode = WAL;
        
        CREATE TABLE IF NOT EXISTS user_favorites (
          lexeme_id TEXT PRIMARY KEY,
          lemma TEXT NOT NULL,
          created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS user_notes (
          id TEXT PRIMARY KEY,
          lexeme_id TEXT NOT NULL,
          note_content TEXT NOT NULL,
          updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
      `, (err) => {
        if (err) reject(err);
        else resolve();
      });
    });

    return db;
  }

  static async addFavorite(db, lexemeId, lemma) {
    return new Promise((resolve, reject) => {
      db.run(
        `INSERT OR REPLACE INTO user_favorites (lexeme_id, lemma) VALUES (?, ?)`,
        [lexemeId, lemma],
        (err) => {
          if (err) reject(err);
          else resolve();
        }
      );
    });
  }

  static async getFavorites(db) {
    return new Promise((resolve, reject) => {
      db.all("SELECT * FROM user_favorites ORDER BY created_at DESC", (err, rows) => {
        if (err) reject(err);
        else resolve(rows || []);
      });
    });
  }
}

module.exports = { UserWorkspaceService };
