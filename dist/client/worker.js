/**
 * Lexical Explorer - SQLite WASM Worker Engine with Milestone 9 Semantics
 * Compliance: ARCHITECTURE.md §4, ONTOLOGY.md §1.3, §1.4, ADR-006
 */

importScripts("https://cdnjs.cloudflare.com/ajax/libs/sql.js/1.12.0/sql-wasm.js");

let db = null;

async function initDB(dbBuffer) {
  const SQL = await initSqlJs({
    locateFile: file => `https://cdnjs.cloudflare.com/ajax/libs/sql.js/1.12.0/${file}`
  });
  db = new SQL.Database(new Uint8Array(dbBuffer));
}

function getGraphSubgraph(rootTerm, depth = 1) {
  if (!db) throw new Error("Database uninitialized");
  if (depth > 3) throw new Error("Hard constraint ceiling violated: depth D <= 3");

  const normalized = rootTerm.trim().toLowerCase();
  
  const rootStmt = db.prepare("SELECT id, lemma, pos, frequency_summary FROM lexemes WHERE normalized_lemma = ? LIMIT 5");
  rootStmt.bind([normalized]);

  const roots = [];
  while (rootStmt.step()) {
    roots.push(rootStmt.getAsObject());
  }
  rootStmt.free();

  if (roots.length === 0) {
    return { nodes: [], links: [] };
  }

  const nodes = new Map();
  const links = [];

  roots.forEach(r => {
    nodes.set(r.id, { id: r.id, label: r.lemma, type: "LEXEME", pos: r.pos });

    // 1. Inflections: HAS_FORM
    const formStmt = db.prepare(`
      SELECT f.id, f.surface, r.relation_type, r.evidence_type
      FROM relations r
      JOIN forms f ON r.object_id = f.id
      WHERE r.subject_id = ? AND r.relation_type = 'HAS_FORM'
      LIMIT 25
    `);
    formStmt.bind([r.id]);
    while (formStmt.step()) {
      const row = formStmt.getAsObject();
      nodes.set(row.id, { id: row.id, label: row.surface, type: "FORM" });
      links.push({
        source: r.id,
        target: row.id,
        relation_type: row.relation_type,
        evidence_type: row.evidence_type
      });
    }
    formStmt.free();

    // 2. Semantics: Senses and Synsets (Milestone 9)
    const senseStmt = db.prepare(`
      SELECT s.id as sense_id, s.definition, syn.id as synset_id, syn.gloss
      FROM senses s
      JOIN synsets syn ON s.synset_id = syn.id
      WHERE s.lexeme_id = ?
      LIMIT 10
    `);
    senseStmt.bind([r.id]);
    while (senseStmt.step()) {
      const sRow = senseStmt.getAsObject();
      const senseLabel = sRow.definition.length > 28 ? sRow.definition.substring(0, 25) + "..." : sRow.definition;
      nodes.set(sRow.sense_id, { id: sRow.sense_id, label: senseLabel, type: "SENSE", fullText: sRow.definition });
      links.push({
        source: r.id,
        target: sRow.sense_id,
        relation_type: "HAS_SENSE",
        evidence_type: "EXPLICIT"
      });

      nodes.set(sRow.synset_id, { id: sRow.synset_id, label: "Concept: " + sRow.synset_id.substring(0, 8), type: "SYNSET", fullText: sRow.gloss });
      links.push({
        source: sRow.sense_id,
        target: sRow.synset_id,
        relation_type: "MEMBER_OF_SYNSET",
        evidence_type: "EXPLICIT"
      });
    }
    senseStmt.free();

    // 3. Derivations: DERIVED_FROM
    const derivStmt = db.prepare(`
      SELECT l.id, l.lemma, l.pos, r.relation_type, r.evidence_type
      FROM relations r
      JOIN lexemes l ON r.object_id = l.id
      WHERE r.subject_id = ? AND r.relation_type = 'DERIVED_FROM'
      LIMIT 10
    `);
    derivStmt.bind([r.id]);
    while (derivStmt.step()) {
      const dRow = derivStmt.getAsObject();
      nodes.set(dRow.id, { id: dRow.id, label: dRow.lemma, type: "LEXEME", pos: dRow.pos });
      links.push({
        source: r.id,
        target: dRow.id,
        relation_type: dRow.relation_type,
        evidence_type: dRow.evidence_type
      });
    }
    derivStmt.free();
  });

  return {
    nodes: Array.from(nodes.values()),
    links
  };
}

onmessage = async function(e) {
  const { id, action, payload } = e.data;
  try {
    if (action === "INIT") {
      await initDB(payload.dbBuffer);
      postMessage({ id, success: true });
    } else if (action === "GET_SUBGRAPH") {
      const result = getGraphSubgraph(payload.term, payload.depth);
      postMessage({ id, success: true, result });
    }
  } catch (err) {
    postMessage({ id, success: false, error: err.message });
  }
};
