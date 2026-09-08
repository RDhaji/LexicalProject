import Database from 'better-sqlite3';
import path from 'path';

export class DatabaseClient {
  private static instance: DatabaseClient;
  public readonly graphDb: Database.Database;
  public readonly workspaceDb: Database.Database;

  private constructor(projectRoot: string) {
    const graphPath = path.join(projectRoot, 'data/compiled/lexical_graph.db');
    const workspacePath = path.join(projectRoot, 'data/user_workspace.db');

    // Invariant: Read-only access to compiled distribution graph
    this.graphDb = new Database(graphPath, { readonly: true, fileMustExist: true });
    this.graphDb.pragma('journal_mode = OFF');
    this.graphDb.pragma('query_only = ON');

    // Invariant: Isolated user partition; zero foreign keys across database boundary
    this.workspaceDb = new Database(workspacePath);
    this.workspaceDb.pragma('journal_mode = WAL');
    this.workspaceDb.pragma('foreign_keys = ON');

    this.initUserWorkspace();
  }

  public static getInstance(projectRoot = '/Users/rd/Desktop/LexicalProject'): DatabaseClient {
    if (!DatabaseClient.instance) {
      DatabaseClient.instance = new DatabaseClient(projectRoot);
    }
    return DatabaseClient.instance;
  }

  private initUserWorkspace(): void {
    this.workspaceDb.exec(`
      CREATE TABLE IF NOT EXISTS user_notes (
        id TEXT PRIMARY KEY,
        target_entity_id TEXT NOT NULL,
        target_entity_type TEXT NOT NULL,
        note_content TEXT NOT NULL,
        created_at INTEGER NOT NULL,
        updated_at INTEGER NOT NULL
      );

      CREATE TABLE IF NOT EXISTS user_bookmarks (
        id TEXT PRIMARY KEY,
        lexeme_id TEXT NOT NULL UNIQUE,
        tags JSON,
        created_at INTEGER NOT NULL
      );

      CREATE INDEX IF NOT EXISTS idx_user_notes_target 
      ON user_notes(target_entity_id, target_entity_type);
    `);
  }
}
