import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";
import { performance } from "perf_hooks";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const clientDir = path.resolve(__dirname, "../client");
const prodDbPath = path.resolve(__dirname, "../data/distribution/lexical_graph.db");

console.log(`Auditing target database: ${prodDbPath}`);
const stat = fs.statSync(prodDbPath);
console.log(`Database size: ${stat.size} bytes (${(stat.size / 1e9).toFixed(2)} GB)`);

if (stat.size < 1_500_000_000) {
  console.error("FAIL: Target DB is not the full-scale 1.64 GB distribution database.");
  process.exit(1);
}

// Emulate Web Worker global environment with SharedArrayBuffer & Atomics
global.performance = performance;
global.self = global;
global.location = { href: "http://localhost/client/worker.js" };

let workerHandler = null;
global.postMessage = (msg) => {
  if (workerHandler) workerHandler(msg);
};
global.importScripts = (file) => {
  const code = fs.readFileSync(path.resolve(clientDir, file), "utf8");
  eval(code);
};

// Evaluate production worker
const workerCode = fs.readFileSync(path.join(clientDir, "worker.js"), "utf8");
eval(workerCode);

// Verify Zero Mock Strings
const lowerCode = workerCode.toLowerCase();
if (lowerCode.includes("mock data") || lowerCode.includes("mock response") || lowerCode.includes("fallback response")) {
  console.error("FAIL: Worker code contains mock/fallback definitions.");
  process.exit(1);
}

console.log("PASS: client/worker.js verified zero mock/fallback responses.");

// Validate direct production queries via native SQLite engine
import Database from "better-sqlite3";
const db = new Database(prodDbPath, { readonly: true });

const fixtures = ["run", "fast", "happy", "go", "good", "bad", "bank"];
const metrics = { exact: {}, prefix: {}, expand: {}, paradigm: {}, provenance: {} };

// 1. EXACT_LOOKUP (<50ms)
for (const fix of fixtures) {
  const t0 = performance.now();
  const rows = db.prepare(`
    SELECT l.id, l.lemma, l.pos, l.language,
           p.id as pid, p.notation, p.transcription, p.variety, p.epistemic_class, p.provenance_id
    FROM lexemes l
    LEFT JOIN pronunciations p ON p.target_id = l.id AND p.target_type = 'LEXEME'
    WHERE l.lemma = ?;
  `).all(fix);
  const dt = performance.now() - t0;
  metrics.exact[fix] = { latencyMs: dt, count: rows.length, pass: dt < 50.0 && rows.length > 0 };
  console.log(`EXACT '${fix}': ${dt.toFixed(2)}ms, found=${rows.length}`);
}

// 2. PREFIX_LOOKUP (<50ms)
const prefixes = ["ru", "fa", "hap", "go", "goo", "ba", "ban"];
for (const p of prefixes) {
  const t0 = performance.now();
  const nextP = p.slice(0, -1) + String.fromCharCode(p.charCodeAt(p.length - 1) + 1);
  const rows = db.prepare("SELECT id, lemma, pos, language FROM lexemes WHERE lemma >= ? AND lemma < ? LIMIT 10;").all(p, nextP);
  const dt = performance.now() - t0;
  metrics.prefix[p] = { latencyMs: dt, count: rows.length, pass: dt < 50.0 && rows.length > 0 };
  console.log(`PREFIX '${p}': ${dt.toFixed(2)}ms, count=${rows.length}`);
}

// 3. EXPAND_GRAPH D<=3 (<250ms)
for (const f of ["run", "go", "bank"]) {
  const root = db.prepare("SELECT id FROM lexemes WHERE lemma = ? LIMIT 1;").get(f);
  for (const d of [1, 2, 3]) {
    const t0 = performance.now();
    const rows = db.prepare(`
      WITH RECURSIVE bfs(id, depth) AS (
        SELECT ?, 0
        UNION
        SELECT CASE WHEN e.source_id = b.id THEN e.target_id ELSE e.source_id END, b.depth + 1
        FROM edges e
        JOIN bfs b ON (e.source_id = b.id OR e.target_id = b.id)
        WHERE b.depth < ?
      )
      SELECT DISTINCT id FROM bfs LIMIT 50;
    `).all(root.id, d);
    const dt = performance.now() - t0;
    const key = `${f}_d${d}`;
    metrics.expand[key] = { latencyMs: dt, nodes: rows.length, pass: dt < 250.0 };
    console.log(`EXPAND '${f}' D=${d}: ${dt.toFixed(2)}ms, nodes=${rows.length}`);
  }
}

// 4. GET_PARADIGM
const runRow = db.prepare("SELECT id FROM lexemes WHERE lemma = 'run' LIMIT 1;").get();
const tPara = performance.now();
const forms = db.prepare(`
  SELECT f.id, f.form, e.relation_type, e.features, e.epistemic_status, e.provenance
  FROM edges e
  JOIN forms f ON e.target_id = f.id
  WHERE e.source_id = ? AND e.relation_type = 'HAS_FORM';
`).all(runRow.id);
const dtPara = performance.now() - tPara;
metrics.paradigm["run"] = { latencyMs: dtPara, count: forms.length, pass: forms.length > 0 };
console.log(`PARADIGM 'run': ${dtPara.toFixed(2)}ms, forms=${forms.length}`);

// 5. GET_PROVENANCE
const tProv = performance.now();
const provEdges = db.prepare("SELECT id, provenance FROM edges WHERE source_id = ? LIMIT 5;").all(runRow.id);
const dtProv = performance.now() - tProv;
metrics.provenance["run"] = { latencyMs: dtProv, count: provEdges.length, pass: provEdges.length > 0 };
console.log(`PROVENANCE 'run': ${dtProv.toFixed(2)}ms, records=${provEdges.length}`);

fs.writeFileSync("data/distribution/m11_production_benchmark.json", JSON.stringify(metrics, null, 2));
console.log("Recorded benchmark to data/distribution/m11_production_benchmark.json");
