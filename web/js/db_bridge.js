// Client RPC Bridge to SQLite Worker
export class LexicalDatabaseBridge {
  constructor(workerPath = "js/worker.js") {
    this.worker = new Worker(workerPath);
    this.pending = new Map();
    this.requestId = 0;

    this.worker.onmessage = (e) => {
      const { id, status, payload, error } = e.data;
      if (this.pending.has(id)) {
        const { resolve, reject } = this.pending.get(id);
        this.pending.delete(id);
        if (status === "OK") resolve(payload);
        else reject(new Error(error));
      }
    };
  }

  request(action, params = {}) {
    return new Promise((resolve, reject) => {
      const id = ++this.requestId;
      this.pending.set(id, { resolve, reject });
      this.worker.postMessage({ id, action, params });
    });
  }

  ping() {
    return this.request("PING");
  }

  exactLookup(term) {
    return this.request("EXACT_LOOKUP", { term });
  }

  traverse(nodeId, depth = 1) {
    return this.request("TRAVERSE_GRAPH", { nodeId, depth });
  }
}
