// Lexical Explorer Client Access Controller
// Communicates with SQLite WebAssembly / Web Worker backend

console.log("[INIT] Lexical Explorer Client Runtime initialized.");

const searchInput = document.getElementById("lexical-search");
const paradigmBlock = document.getElementById("paradigm-content");
const provenanceBlock = document.getElementById("provenance-content");

searchInput.addEventListener("keydown", async (event) => {
  if (event.key === "Enter") {
    const query = searchInput.value.trim();
    if (!query) return;
    console.log(`[QUERY] Executing exact/prefix lookup: ${query}`);
    // Future Worker RPC dispatch
  }
});
