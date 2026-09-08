import fs from 'fs';
import readline from 'readline';
import { Claim, EpistemicClass } from '../types/lexical';

export class KaikkiStreamer {
  /**
   * Streams a Kaikki JSONL export line-by-line without loading the file into memory.
   * Emits raw claims into staging SQLite or batch handlers per ADR-002.
   */
  public async parseStream(
    filePath: string,
    onClaimBatch: (claims: Claim[]) => Promise<void>,
    batchSize = 1000
  ): Promise<number> {
    if (!fs.existsSync(filePath)) {
      throw new Error(`[PARSER ERROR] Kaikki JSONL dump not found at ${filePath}`);
    }

    const fileStream = fs.createReadStream(filePath, { encoding: 'utf-8' });
    const rl = readline.createInterface({
      input: fileStream,
      crlfDelay: Infinity
    });

    let batch: Claim[] = [];
    let totalProcessed = 0;

    for await (const line of rl) {
      if (!line.trim()) continue;

      try {
        const rawRecord = JSON.parse(line);
        const word = rawRecord.word;
        const pos = rawRecord.pos;
        const langCode = rawRecord.lang_code || 'en';

        if (langCode === 'en' && word && pos) {
          const claim: Claim = {
            id: `claim-kaikki-${word}-${pos}-${totalProcessed}`,
            source_id: 'WIKTIONARY_KAIKKI_20260805',
            subject_type: 'LEXEME',
            subject_id: `${word}:${pos}`,
            predicate: 'ASSERTS_LEXEME',
            object_type: 'LEXEME',
            object_id: `${word}:${pos}`,
            raw_assertion: rawRecord,
            evidence_type: 'EXPLICIT' as EpistemicClass,
            extraction_confidence: 1.0
          };

          batch.push(claim);
          totalProcessed++;

          if (batch.length >= batchSize) {
            await onClaimBatch(batch);
            batch = [];
          }
        }
      } catch (err) {
        // Drop corrupted JSON lines without halting pipeline unless Gate A threshold fails
      }
    }

    if (batch.length > 0) {
      await onClaimBatch(batch);
    }

    return totalProcessed;
  }
}
