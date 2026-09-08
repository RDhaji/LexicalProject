/**
 * Lexical Explorer Client Interface
 * Compliance: ARCHITECTURE.md Section 4, ADR-006
 */

class LexicalClient {
  constructor() {
    this.worker = new Worker("worker.js");
    this.pending = new Map();
    this.reqId = 0;

    this.worker.onmessage = (e) => {
      const { id, success, result, error } = e.data;
      if (this.pending.has(id)) {
        const { resolve, reject } = this.pending.get(id);
        this.pending.delete(id);
        if (success) resolve(result);
        else reject(new Error(error));
      }
    };
  }

  _send(action, payload) {
    return new Promise((resolve, reject) => {
      const id = ++this.reqId;
      this.pending.set(id, { resolve, reject });
      this.worker.postMessage({ id, action, payload });
    });
  }

  async loadDatabase(arrayBuffer) {
    return this._send("INIT", { dbBuffer: arrayBuffer });
  }

  async lookup(term) {
    return this._send("LOOKUP", { term });
  }

  async expand(entityId, depth = 1) {
    return this._send("EXPAND", { entityId, depth });
  }
}
