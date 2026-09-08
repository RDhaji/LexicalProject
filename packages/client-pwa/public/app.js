// English Lexical & Morphological Explorer Client Shell Logic
class LexicalExplorerApp {
  constructor(queryService, workspaceService) {
    this.queryService = queryService;
    this.workspaceService = workspaceService;
    this.currentLexeme = null;
  }

  async handleSearchInput(val) {
    const trimmed = (val || '').trim();
    if (!trimmed) return [];
    return await this.queryService.searchPrefix(trimmed, 10);
  }

  async loadWordPage(lexemeId) {
    const details = await this.queryService.getWordDetails(lexemeId);
    if (!details) return null;
    this.currentLexeme = details.lexeme;
    return details;
  }

  async explainRelation(relationId) {
    return await this.queryService.explainConnection(relationId);
  }

  async saveCurrentToWorkspace(db) {
    if (!this.currentLexeme) return false;
    await this.workspaceService.addFavorite(db, this.currentLexeme.id, this.currentLexeme.lemma);
    return true;
  }
}

if (typeof module !== 'undefined') {
  module.exports = { LexicalExplorerApp };
}
