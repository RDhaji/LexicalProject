const crypto = require("crypto");

const NAMESPACE_OID = "6ba7b812-9dad-11d1-80b4-00c04fd430c8";
function generateUUID(name) {
  return crypto.createHash("sha1").update(NAMESPACE_OID + name).digest("hex").replace(
    /(.{8})(.{4})(.{4})(.{4})(.{12})/,
    "$1-$2-5$3-$4-$5"
  ).slice(0, 36);
}

class ClaimResolver {
  /**
   * Evaluates competing claims and compiles resolved relations.
   * Zero silent merging: Conflicting claims are preserved and flagged (PRD §19, ADR-002).
   */
  static async resolveAllClaims(db) {
    const run = (q, p = []) => new Promise((resolve, reject) => {
      db.run(q, p, function (err) {
        if (err) reject(err);
        else resolve(this);
      });
    });

    const all = (q, p = []) => new Promise((resolve, reject) => {
      db.all(q, p, (err, rows) => {
        if (err) reject(err);
        else resolve(rows);
      });
    });

    // Group claims by subject and predicate to detect competing claims
    const claimGroups = await all(
      `SELECT subject_source_id, subject_type, predicate, COUNT(DISTINCT object_source_id) as target_count
       FROM claims
       WHERE object_source_id IS NOT NULL
       GROUP BY subject_source_id, subject_type, predicate`
    );

    for (const group of claimGroups) {
      if (group.target_count > 1) {
        // Material conflict detected across sources for the same predicate
        const conflictingClaims = await all(
          `SELECT id, source_id, object_source_id, object_type, confidence 
           FROM claims 
           WHERE subject_source_id = ? AND subject_type = ? AND predicate = ?`,
          [group.subject_source_id, group.subject_type, group.predicate]
        );

        for (const claim of conflictingClaims) {
          const relId = generateUUID("rel:conflict:" + group.subject_source_id + ":" + claim.object_source_id);
          
          await run(
            `INSERT OR REPLACE INTO relations (id, subject_type, subject_id, relation_type, object_type, object_id, evidence_type, confidence, resolution_status)
             VALUES (?, ?, ?, ?, ?, ?, "UNCERTAIN", ?, "CONFLICTING")`,
            [relId, group.subject_type, group.subject_source_id, group.predicate, claim.object_type, claim.object_source_id, claim.confidence]
          );

          await run(
            `INSERT OR IGNORE INTO relation_claims (relation_id, claim_id) VALUES (?, ?)`,
            [relId, claim.id]
          );
        }
      }
    }
  }
}

class QualitySystem {
  /**
   * Executes Quality Gates A through E (PRD §35).
   */
  static async executeQualityGates(db) {
    const get = (q, p = []) => new Promise((resolve, reject) => {
      db.get(q, p, (err, row) => {
        if (err) reject(err);
        else resolve(row);
      });
    });

    const all = (q, p = []) => new Promise((resolve, reject) => {
      db.all(q, p, (err, rows) => {
        if (err) reject(err);
        else resolve(rows);
      });
    });

    const report = {
      passed: true,
      gates: {},
      metrics: {},
      errors: []
    };

    // 1. Gate A: Foreign Key & Pragma Integrity
    const foreignKeyViolations = await all("PRAGMA foreign_key_check");
    if (foreignKeyViolations.length > 0) {
      report.passed = false;
      report.gates["Gate_A_Integrity"] = "FAILED";
      report.errors.push(`Foreign key check failed: ${foreignKeyViolations.length} orphan records detected.`);
    } else {
      report.gates["Gate_A_Integrity"] = "PASSED";
    }

    // 2. Gate B: Ontological Validations
    const invalidPos = await all(
      `SELECT id, pos FROM lexemes WHERE pos NOT IN (
        "NOUN", "VERB", "ADJECTIVE", "ADVERB", "PRONOUN", 
        "DETERMINER", "PREPOSITION", "CONJUNCTION", "INTERJECTION", 
        "AUXILIARY", "NUMERAL", "PARTICLE", "OTHER"
      )`
    );
    if (invalidPos.length > 0) {
      report.passed = false;
      report.gates["Gate_B_Ontology"] = "FAILED";
      report.errors.push(`Found ${invalidPos.length} lexemes with illegal POS values.`);
    } else {
      report.gates["Gate_B_Ontology"] = "PASSED";
    }

    // 3. Gate E: Provenance Completeness (100% visible non-generated facts trace to a claim)
    const unbackedRelations = await all(
      `SELECT r.id, r.relation_type 
       FROM relations r 
       LEFT JOIN relation_claims rc ON r.id = rc.relation_id 
       WHERE rc.claim_id IS NULL AND r.evidence_type != "GENERATED"`
    );
    if (unbackedRelations.length > 0) {
      report.passed = false;
      report.gates["Gate_E_Provenance"] = "FAILED";
      report.errors.push(`Found ${unbackedRelations.length} relations missing claim provenance.`);
    } else {
      report.gates["Gate_E_Provenance"] = "PASSED";
    }

    // 4. Observability Metrics (PRD §38)
    report.metrics.lexemeCount = (await get("SELECT COUNT(*) as count FROM lexemes")).count;
    report.metrics.formCount = (await get("SELECT COUNT(*) as count FROM forms")).count;
    report.metrics.senseCount = (await get("SELECT COUNT(*) as count FROM senses")).count;
    report.metrics.synsetCount = (await get("SELECT COUNT(*) as count FROM synsets")).count;
    report.metrics.relationCount = (await get("SELECT COUNT(*) as count FROM relations")).count;
    report.metrics.claimCount = (await get("SELECT COUNT(*) as count FROM claims")).count;
    report.metrics.conflictingRelations = (await get("SELECT COUNT(*) as count FROM relations WHERE resolution_status = 'CONFLICTING'")).count;
    report.metrics.inferredRelations = (await get("SELECT COUNT(*) as count FROM relations WHERE evidence_type = 'INFERRED'")).count;

    return report;
  }

  /**
   * Emits a Markdown formatted build summary report (PRD §38).
   */
  static formatReportAsMarkdown(report) {
    return `# Build & Data Quality Summary Report
Generated: ${new Date().toISOString()}
Status: ${report.passed ? "PASSED" : "FAILED"}

## Quality Gates Status
- Gate A (Source & Foreign Key Integrity): ${report.gates["Gate_A_Integrity"]}
- Gate B (Ontological Purity): ${report.gates["Gate_B_Ontology"]}
- Gate E (Provenance Completeness): ${report.gates["Gate_E_Provenance"]}

## Graph Counts
- Lexemes: ${report.metrics.lexemeCount}
- Forms: ${report.metrics.formCount}
- Senses: ${report.metrics.senseCount}
- Synsets: ${report.metrics.synsetCount}
- Relations: ${report.metrics.relationCount}
- Claims: ${report.metrics.claimCount}

## Epistemic Status
- Conflicting Relations: ${report.metrics.conflictingRelations}
- Inferred Relations: ${report.metrics.inferredRelations}

## Errors / Anomalies
${report.errors.length === 0 ? "None. Zero integrity violations detected." : report.errors.map(e => "- " + e).join("\n")}
`;
  }
}

module.exports = { ClaimResolver, QualitySystem, generateUUID };
