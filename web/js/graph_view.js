// Graph Visualizer Component (D <= 3 Bounded Interactive Renderer)
export class LexicalGraphVisualizer {
  constructor(containerId) {
    this.container = document.getElementById(containerId);
  }

  render(data) {
    if (!this.container) return;
    this.container.innerHTML = "";
    
    const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
    svg.setAttribute("width", "100%");
    svg.setAttribute("height", "100%");
    svg.setAttribute("viewBox", "0 0 800 600");
    
    // Render Nodes
    (data.nodes || []).forEach((node, idx) => {
      const circle = document.createElementNS("http://www.w3.org/2000/svg", "circle");
      circle.setAttribute("cx", 200 + (idx * 120));
      circle.setAttribute("cy", 300);
      circle.setAttribute("r", 24);
      circle.setAttribute("fill", node.type === "LEXEME" ? "#3b82f6" : "#10b981");
      svg.appendChild(circle);

      const text = document.createElementNS("http://www.w3.org/2000/svg", "text");
      text.setAttribute("x", 200 + (idx * 120));
      text.setAttribute("y", 305);
      text.setAttribute("text-anchor", "middle");
      text.setAttribute("fill", "#ffffff");
      text.setAttribute("font-size", "12px");
      text.textContent = node.label;
      svg.appendChild(text);
    });

    this.container.appendChild(svg);
  }
}
