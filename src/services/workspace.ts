import crypto from 'crypto';
import { DatabaseClient } from '../db/client';

export interface UserNote {
  id: string;
  targetEntityId: string;
  targetEntityType: 'LEXEME' | 'FORM' | 'SENSE' | 'CONSTRUCTION';
  noteContent: string;
  createdAt: number;
  updatedAt: number;
}

export interface UserBookmark {
  id: string;
  lexemeId: string;
  tags: string[];
  createdAt: number;
}

export class WorkspaceService {
  private client: DatabaseClient;

  constructor(client: DatabaseClient) {
    this.client = client;
  }

  /**
   * Creates or updates a user note bound to an immutable entity UUID
   */
  public saveNote(targetEntityId: string, targetEntityType: UserNote['targetEntityType'], noteContent: string): UserNote {
    const now = Date.now();
    const existing = this.client.workspaceDb.prepare(
      'SELECT id, created_at FROM user_notes WHERE target_entity_id = ? AND target_entity_type = ?'
    ).get(targetEntityId, targetEntityType) as { id: string; created_at: number } | undefined;

    if (existing) {
      this.client.workspaceDb.prepare(`
        UPDATE user_notes
        SET note_content = ?, updated_at = ?
        WHERE id = ?
      `).run(noteContent, now, existing.id);

      return {
        id: existing.id,
        targetEntityId,
        targetEntityType,
        noteContent,
        createdAt: existing.created_at,
        updatedAt: now
      };
    } else {
      const id = crypto.randomUUID();
      this.client.workspaceDb.prepare(`
        INSERT INTO user_notes (id, target_entity_id, target_entity_type, note_content, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?)
      `).run(id, targetEntityId, targetEntityType, noteContent, now, now);

      return {
        id,
        targetEntityId,
        targetEntityType,
        noteContent,
        createdAt: now,
        updatedAt: now
      };
    }
  }

  /**
   * Retrieves notes for a specific lexical entity
   */
  public getNotesForEntity(targetEntityId: string): UserNote[] {
    const rows = this.client.workspaceDb.prepare(
      'SELECT id, target_entity_id, target_entity_type, note_content, created_at, updated_at FROM user_notes WHERE target_entity_id = ?'
    ).all(targetEntityId) as any[];

    return rows.map(r => ({
      id: r.id,
      targetEntityId: r.target_entity_id,
      targetEntityType: r.target_entity_type,
      noteContent: r.note_content,
      createdAt: r.created_at,
      updatedAt: r.updated_at
    }));
  }

  /**
   * Adds or updates a bookmark for a Lexeme
   */
  public setBookmark(lexemeId: string, tags: string[] = []): UserBookmark {
    const now = Date.now();
    const existing = this.client.workspaceDb.prepare(
      'SELECT id, created_at FROM user_bookmarks WHERE lexeme_id = ?'
    ).get(lexemeId) as { id: string; created_at: number } | undefined;

    const tagsJson = JSON.stringify(tags);

    if (existing) {
      this.client.workspaceDb.prepare(`
        UPDATE user_bookmarks
        SET tags = ?
        WHERE id = ?
      `).run(tagsJson, existing.id);

      return {
        id: existing.id,
        lexemeId,
        tags,
        createdAt: existing.created_at
      };
    } else {
      const id = crypto.randomUUID();
      this.client.workspaceDb.prepare(`
        INSERT INTO user_bookmarks (id, lexeme_id, tags, created_at)
        VALUES (?, ?, ?, ?)
      `).run(id, lexemeId, tagsJson, now);

      return {
        id,
        lexemeId,
        tags,
        createdAt: now
      };
    }
  }

  /**
   * Removes a bookmark by Lexeme ID
   */
  public removeBookmark(lexemeId: string): boolean {
    const result = this.client.workspaceDb.prepare(
      'DELETE FROM user_bookmarks WHERE lexeme_id = ?'
    ).run(lexemeId);
    return result.changes > 0;
  }
}
