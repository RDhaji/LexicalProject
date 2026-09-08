/**
 * Lexical Explorer - Canvas Graph Engine (Milestone 9 Updated)
 */
class GraphRenderer {
  constructor(canvas) {
    this.canvas = canvas;
    this.ctx = canvas.getContext("2d");
    this.nodes = new Map();
    this.links = [];
    this.width = canvas.width;
    this.height = canvas.height;
    this.draggedNode = null;
    this._initEvents();
    this._animate();
  }

  setData(data) {
    this.nodes.clear();
    this.links = [];
    const cx = this.width / 2;
    const cy = this.height / 2;

    data.nodes.forEach((n, idx) => {
      const angle = (idx / data.nodes.length) * 2 * Math.PI;
      const radius = idx === 0 ? 0 : 130 + Math.random() * 60;
      let r = 12;
      if (n.type === "LEXEME") r = 20;
      else if (n.type === "SYNSET") r = 16;
      else if (n.type === "SENSE") r = 14;

      this.nodes.set(n.id, {
        id: n.id,
        label: n.label,
        type: n.type,
        pos: n.pos || "",
        x: cx + radius * Math.cos(angle),
        y: cy + radius * Math.sin(angle),
        vx: 0,
        vy: 0,
        radius: r
      });
    });

    data.links.forEach(l => {
      if (this.nodes.has(l.source) && this.nodes.has(l.target)) {
        this.links.push({
          source: this.nodes.get(l.source),
          target: this.nodes.get(l.target),
          relation_type: l.relation_type,
          evidence_type: l.evidence_type
        });
      }
    });
  }

  _initEvents() {
    let isDragging = false;
    this.canvas.addEventListener("mousedown", (e) => {
      const rect = this.canvas.getBoundingClientRect();
      const x = e.clientX - rect.left;
      const y = e.clientY - rect.top;
      for (let n of this.nodes.values()) {
        const dx = n.x - x;
        const dy = n.y - y;
        if (Math.sqrt(dx * dx + dy * dy) < n.radius + 6) {
          this.draggedNode = n;
          isDragging = true;
          break;
        }
      }
    });

    this.canvas.addEventListener("mousemove", (e) => {
      if (isDragging && this.draggedNode) {
        const rect = this.canvas.getBoundingClientRect();
        this.draggedNode.x = e.clientX - rect.left;
        this.draggedNode.y = e.clientY - rect.top;
      }
    });

    window.addEventListener("mouseup", () => {
      isDragging = false;
      this.draggedNode = null;
    });
  }

  _animate() {
    this._updatePhysics();
    this._render();
    requestAnimationFrame(() => this._animate());
  }

  _updatePhysics() {
    const k = 0.04;
    const repulsion = 1400;
    const nodeArr = Array.from(this.nodes.values());

    for (let i = 0; i < nodeArr.length; i++) {
      for (let j = i + 1; j < nodeArr.length; j++) {
        const a = nodeArr[i];
        const b = nodeArr[j];
        const dx = b.x - a.x;
        const dy = b.y - a.y;
        const dist = Math.sqrt(dx * dx + dy * dy) || 1;
        if (dist < 260) {
          const force = repulsion / (dist * dist);
          const fx = (dx / dist) * force;
          const fy = (dy / dist) * force;
          a.vx -= fx;
          a.vy -= fy;
          b.vx += fx;
          b.vy += fy;
        }
      }
    }

    this.links.forEach(l => {
      const dx = l.target.x - l.source.x;
      const dy = l.target.y - l.source.y;
      const dist = Math.sqrt(dx * dx + dy * dy) || 1;
      let targetDist = 120;
      if (l.relation_type === "HAS_FORM") targetDist = 70;
      if (l.relation_type === "HAS_SENSE") targetDist = 95;
      if (l.relation_type === "MEMBER_OF_SYNSET") targetDist = 80;

      const force = (dist - targetDist) * k;
      const fx = (dx / dist) * force;
      const fy = (dy / dist) * force;
      l.source.vx += fx;
      l.source.vy += fy;
      l.target.vx -= fx;
      l.target.vy -= fy;
    });

    nodeArr.forEach(n => {
      if (n !== this.draggedNode) {
        n.vx *= 0.85;
        n.vy *= 0.85;
        n.x += n.vx;
        n.y += n.vy;
        n.x = Math.max(n.radius + 10, Math.min(this.width - n.radius - 10, n.x));
        n.y = Math.max(n.radius + 10, Math.min(this.height - n.radius - 10, n.y));
      }
    });
  }

  _render() {
    this.ctx.clearRect(0, 0, this.width, this.height);

    // Render Edges
    this.links.forEach(l => {
      this.ctx.beginPath();
      this.ctx.moveTo(l.source.x, l.source.y);
      this.ctx.lineTo(l.target.x, l.target.y);

      if (l.relation_type === "HAS_SENSE") {
        this.ctx.strokeStyle = "#10b981"; // Emerald
        this.ctx.lineWidth = 2.0;
      } else if (l.relation_type === "MEMBER_OF_SYNSET") {
        this.ctx.strokeStyle = "#8b5cf6"; // Purple
        this.ctx.lineWidth = 1.8;
      } else if (l.relation_type === "HAS_FORM") {
        this.ctx.strokeStyle = "#64748b"; // Slate
        this.ctx.lineWidth = 1.5;
      } else {
        this.ctx.strokeStyle = "#38bdf8"; // Sky
        this.ctx.lineWidth = 2.2;
      }

      this.ctx.stroke();
    });

    // Render Nodes
    this.nodes.forEach(n => {
      this.ctx.beginPath();
      this.ctx.arc(n.x, n.y, n.radius, 0, 2 * Math.PI);

      if (n.type === "LEXEME") {
        this.ctx.fillStyle = "#1e293b";
        this.ctx.strokeStyle = "#38bdf8";
        this.ctx.lineWidth = 2.5;
      } else if (n.type === "SENSE") {
        this.ctx.fillStyle = "#064e3b";
        this.ctx.strokeStyle = "#10b981";
        this.ctx.lineWidth = 2.0;
      } else if (n.type === "SYNSET") {
        this.ctx.fillStyle = "#4c1d95";
        this.ctx.strokeStyle = "#a78bfa";
        this.ctx.lineWidth = 2.0;
      } else {
        this.ctx.fillStyle = "#0f172a";
        this.ctx.strokeStyle = "#94a3b8";
        this.ctx.lineWidth = 1.5;
      }

      this.ctx.fill();
      this.ctx.stroke();

      this.ctx.fillStyle = "#f8fafc";
      this.ctx.font = n.type === "LEXEME" ? "bold 12px monospace" : "10px monospace";
      this.ctx.textAlign = "center";
      this.ctx.textBaseline = "middle";
      this.ctx.fillText(n.label, n.x, n.y + n.radius + 12);
    });
  }
}
