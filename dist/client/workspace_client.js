/**
 * Lexical Explorer - Workspace Client & Bidirectional Sync Bridge
 * Compliance: ARCHITECTURE.md §2, ADR-006, Milestone 13
 */

class WorkspaceController {
  constructor() {
    this.dbName = "LexicalExplorerWorkspace";
    this.dbVersion = 2;
    this.db = null;
    this.deviceId = this._getDeviceId();
  }

  _getDeviceId() {
    let dId = localStorage.getItem("lex_device_id");
    if (!dId) {
      dId = crypto.randomUUID();
      localStorage.setItem("lex_device_id", dId);
    }
    return dId;
  }

  async init() {
    return new Promise((resolve, reject) => {
      const request = indexedDB.open(this.dbName, this.dbVersion);

      request.onupgradeneeded = (e) => {
        const db = e.target.result;
        if (!db.objectStoreNames.contains("bookmarks")) {
          const bmStore = db.createObjectStore("bookmarks", { keyPath: "id" });
          bmStore.createIndex("target_id", "target_id", { unique: false });
          bmStore.createIndex("target_type", "target_type", { unique: false });
          bmStore.createIndex("updated_at", "updated_at", { unique: false });
        }
        if (!db.objectStoreNames.contains("notes")) {
          const noteStore = db.createObjectStore("notes", { keyPath: "id" });
          noteStore.createIndex("target_id", "target_id", { unique: false });
          noteStore.createIndex("updated_at", "updated_at", { unique: false });
        }
        if (!db.objectStoreNames.contains("tags")) {
          db.createObjectStore("tags", { keyPath: "id" });
        }
        if (!db.objectStoreNames.contains("sync_log")) {
          db.createObjectStore("sync_log", { keyPath: "id" });
        }
      };

      request.onsuccess = (e) => {
        this.db = e.target.result;
        resolve(this);
      };

      request.onerror = (e) => reject(e.target.error);
    });
  }

  async toggleBookmark(entity) {
    return new Promise((resolve, reject) => {
      const tx = this.db.transaction(["bookmarks", "sync_log"], "readwrite");
      const store = tx.objectStore("bookmarks");
      const logStore = tx.objectStore("sync_log");
      const index = store.index("target_id");
      const req = index.get(entity.target_id);

      req.onsuccess = () => {
        const now = Date.now();
        if (req.result && !req.result.is_deleted) {
          const updated = {
            ...req.result,
            is_deleted: 1,
            updated_at: now,
            sync_version: (req.result.sync_version || 1) + 1,
            device_id: this.deviceId
          };
          store.put(updated);
          logStore.put({
            id: crypto.randomUUID(),
            table_name: "user_bookmarks",
            entity_id: updated.id,
            action: "DELETE",
            timestamp: now
          });
          resolve({ status: "REMOVED", target_id: entity.target_id });
        } else {
          const item = {
            id: req.result ? req.result.id : crypto.randomUUID(),
            target_type: entity.target_type,
            target_id: entity.target_id,
            target_label: entity.target_label,
            category: entity.category || "DEFAULT",
            is_deleted: 0,
            created_at: req.result ? req.result.created_at : new Date(now).toISOString(),
            updated_at: now,
            sync_version: req.result ? (req.result.sync_version || 1) + 1 : 1,
            device_id: this.deviceId
          };
          store.put(item);
          logStore.put({
            id: crypto.randomUUID(),
            table_name: "user_bookmarks",
            entity_id: item.id,
            action: "UPSERT",
            timestamp: now
          });
          resolve({ status: "ADDED", item });
        }
      };
      req.onerror = () => reject(tx.error);
    });
  }

  async isBookmarked(targetId) {
    return new Promise((resolve) => {
      const tx = this.db.transaction("bookmarks", "readonly");
      const req = tx.objectStore("bookmarks").index("target_id").get(targetId);
      req.onsuccess = () => {
        const res = req.result;
        resolve(res && !res.is_deleted);
      };
      req.onerror = () => resolve(false);
    });
  }

  async getBookmarks() {
    return new Promise((resolve, reject) => {
      const tx = this.db.transaction("bookmarks", "readonly");
      const req = tx.objectStore("bookmarks").getAll();
      req.onsuccess = () => {
        const active = (req.result || []).filter(b => !b.is_deleted);
        resolve(active);
      };
      req.onerror = () => reject(tx.error);
    });
  }

  async saveNote(note) {
    return new Promise((resolve, reject) => {
      const tx = this.db.transaction(["notes", "sync_log"], "readwrite");
      const store = tx.objectStore("notes");
      const logStore = tx.objectStore("sync_log");
      const now = Date.now();

      const record = {
        id: note.id || crypto.randomUUID(),
        target_type: note.target_type,
        target_id: note.target_id,
        note_title: note.note_title || "",
        note_body: note.note_body || "",
        is_deleted: 0,
        created_at: note.created_at || new Date(now).toISOString(),
        updated_at: now,
        sync_version: (note.sync_version || 0) + 1,
        device_id: this.deviceId
      };

      store.put(record);
      logStore.put({
        id: crypto.randomUUID(),
        table_name: "user_notes",
        entity_id: record.id,
        action: "UPSERT",
        timestamp: now
      });

      tx.oncomplete = () => resolve(record);
      tx.onerror = () => reject(tx.error);
    });
  }

  async exportSyncPackage() {
    const tx = this.db.transaction(["bookmarks", "notes"], "readonly");
    const bookmarksReq = tx.objectStore("bookmarks").getAll();
    const notesReq = tx.objectStore("notes").getAll();

    return new Promise((resolve, reject) => {
      tx.oncomplete = () => {
        const pkg = {
          device_id: this.deviceId,
          exported_at: Date.now(),
          bookmarks: bookmarksReq.result || [],
          notes: notesReq.result || []
        };
        resolve(pkg);
      };
      tx.onerror = () => reject(tx.error);
    });
  }

  async importSyncPackage(pkg) {
    if (!pkg || !pkg.bookmarks || !pkg.notes) {
      throw new Error("Invalid sync package format");
    }

    return new Promise((resolve, reject) => {
      const tx = this.db.transaction(["bookmarks", "notes"], "readwrite");
      const bmStore = tx.objectStore("bookmarks");
      const noteStore = tx.objectStore("notes");

      // Merge bookmarks using Last-Write-Wins (updated_at timestamp vector)
      pkg.bookmarks.forEach(incoming => {
        const req = bmStore.get(incoming.id);
        req.onsuccess = () => {
          const local = req.result;
          if (!local || incoming.updated_at > (local.updated_at || 0)) {
            bmStore.put(incoming);
          }
        };
      });

      // Merge notes using Last-Write-Wins
      pkg.notes.forEach(incoming => {
        const req = noteStore.get(incoming.id);
        req.onsuccess = () => {
          const local = req.result;
          if (!local || incoming.updated_at > (local.updated_at || 0)) {
            noteStore.put(incoming);
          }
        };
      });

      tx.oncomplete = () => resolve(true);
      tx.onerror = () => reject(tx.error);
    });
  }
}
window.WorkspaceController = WorkspaceController;
