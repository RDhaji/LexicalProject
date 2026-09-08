// Paradigm Inspector Table Component
// Renders inflectional realization bundles (ADR-003)
export class ParadigmInspector {
  constructor(containerId) {
    this.container = document.getElementById(containerId);
  }

  render(forms) {
    if (!this.container) return;
    if (!forms || forms.length === 0) {
      this.container.innerHTML = "<em>No inflectional forms attested.</em>";
      return;
    }

    let html = `<table style="width:100%; border-collapse:collapse; font-size:0.8rem;">
      <thead>
        <tr style="border-bottom:1px solid #475569; text-align:left;">
          <th style="padding:4px;">Surface</th>
          <th style="padding:4px;">Features</th>
        </tr>
      </thead>
      <tbody>`;

    for (const f of forms) {
      html += `<tr style="border-bottom:1px solid #334155;">
        <td style="padding:4px; font-weight:600;">${f.surface}</td>
        <td style="padding:4px; color:#94a3b8;">${f.features || "{}"}</td>
      </tr>`;
    }

    html += `</tbody></table>`;
    this.container.innerHTML = html;
  }
}
