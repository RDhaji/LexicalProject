// Provenance & "Why Connected?" Inspector
// Surfacing raw claims, evidence types, and confidence scores
export class ProvenanceInspector {
  constructor(containerId) {
    this.container = document.getElementById(containerId);
  }

  render(claimRecord) {
    if (!this.container) return;
    if (!claimRecord) {
      this.container.innerHTML = "<em>Select a node or edge to inspect epistemic claims.</em>";
      return;
    }

    const badgeColor = {
      EXPLICIT: "#10b981",
      ATTESTED: "#3b82f6",
      INFERRED: "#f59e0b",
      UNCERTAIN: "#ef4444"
    }[claimRecord.evidence_type] || "#64748b";

    this.container.innerHTML = `
      <div style="padding: 8px; border: 1px solid #334155; border-radius: 4px; background: #0f172a;">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
          <span style="font-size: 0.75rem; font-weight: 700; color: #94a3b8;">EPISTEMIC CLASS</span>
          <span style="background: ${badgeColor}; color: #fff; padding: 2px 6px; border-radius: 3px; font-size: 0.7rem; font-weight: 700;">
            ${claimRecord.evidence_type}
          </span>
        </div>
        <div style="font-size: 0.8rem; margin-bottom: 4px;">
          <strong>Relation:</strong> ${claimRecord.relation_type || "N/A"}
        </div>
        <div style="font-size: 0.8rem; margin-bottom: 4px;">
          <strong>Confidence:</strong> ${(claimRecord.confidence * 100).toFixed(1)}%
        </div>
        <div style="font-size: 0.75rem; color: #94a3b8; margin-top: 6px; border-top: 1px dashed #334155; padding-top: 4px;">
          <strong>Supporting Claims:</strong> ${(claimRecord.claims || []).join(", ") || "None"}
        </div>
      </div>
    `;
  }
}
