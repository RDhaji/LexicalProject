/**
 * Node runner harness for validating sql-wasm.js and client query execution in CI.
 */
const fs = require("fs");
const path = require("path");

// Mock browser worker environment
global.self = global;
global.window = global;

global.importScripts = (...scripts) => {
  for (const s of scripts) {
    let resolved = s;
    if (s.includes("sql-wasm.js") || s.endsWith("sql-wasm.js")) {
      resolved = path.resolve(__dirname, "../client/vendor/sql-wasm.js");
    } else if (s.startsWith("http://") || s.startsWith("https://")) {
      resolved = path.resolve(__dirname, "../client/vendor", path.basename(s));
    } else if (!path.isAbsolute(s)) {
      resolved = path.resolve(__dirname, "../client", s);
    }
    const scriptContent = fs.readFileSync(resolved, "utf8");
    eval(scriptContent);
  }
};

async function run() {
  const initSqlJs = require("../client/vendor/sql-wasm.js");
  const wasmBinary = fs.readFileSync(path.resolve(__dirname, "../client/vendor/sql-wasm.wasm"));
  
  const SQL = await initSqlJs({
    wasmBinary
  });

  const db = new SQL.Database();
  db.run("CREATE TABLE test (id INTEGER PRIMARY KEY, lemma TEXT);");
  db.run("INSERT INTO test (lemma) VALUES (?);", ["run"]);
  
  const res = db.exec("SELECT lemma FROM test WHERE id = 1;");
  const val = res[0].values[0][0];
  
  if (val !== "run") {
    throw new Error(`Assertion failed: expected "run", got "${val}"`);
  }
  
  console.log("PASS: WASM node runner initialized and executed test query successfully.");
  db.close();
}

run().catch((err) => {
  console.error("FAIL: WASM node runner execution failed:", err);
  process.exit(1);
});
