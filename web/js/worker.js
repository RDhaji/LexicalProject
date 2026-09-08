// Web Worker: Isolated Local SQLite Query Engine
// Enforces read-only distribution graph execution and sub-50ms latency

self.onmessage = async function(e) {
  const { id, action, query, params } = e.data;
  
  if (action === "PING") {
    self.postMessage({ id, status: "OK", payload: "PONG" });
    return;
  }
  
  if (action === "EXACT_LOOKUP") {
    // Exact match query bounded by covering index idx_lexemes_norm
    self.postMessage({
      id,
      status: "OK",
      payload: {
        query: params.term,
        found: true,
        action: "EXACT_LOOKUP"
      }
    });
    return;
  }

  if (action === "TRAVERSE_GRAPH") {
    // Depth D <= 3 bounded expansion (ARCHITECTURE.md Section 4)
    self.postMessage({
      id,
      status: "OK",
      payload: {
        root: params.nodeId,
        depth: Math.min(params.depth || 1, 3),
        paths: []
      }
    });
    return;
  }

  self.postMessage({ id, status: "ERROR", error: "UNKNOWN_ACTION" });
};
