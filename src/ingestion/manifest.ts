import fs from 'fs';
import path from 'path';
import crypto from 'crypto';

export interface SourceManifestEntry {
  identifier: string;
  filename: string;
  sha256: string;
  expected_bytes: number;
}

export interface ManifestSchema {
  version: string;
  sources: SourceManifestEntry[];
}

export class ManifestValidator {
  private rootDir: string;

  constructor(rootDir = '/Users/rd/Desktop/LexicalProject') {
    this.rootDir = rootDir;
  }

  public verifyManifest(manifestPath?: string): boolean {
    const targetPath = manifestPath || path.join(this.rootDir, 'data/sources/manifest.json');
    if (!fs.existsSync(targetPath)) {
      throw new Error(`[CRITICAL] Source manifest missing at ${targetPath}. Gate A violated.`);
    }

    const manifest: ManifestSchema = JSON.parse(fs.readFileSync(targetPath, 'utf-8'));
    
    for (const entry of manifest.sources) {
      const artifactPath = path.join(path.dirname(targetPath), entry.filename);
      if (!fs.existsSync(artifactPath)) {
        throw new Error(`[CRITICAL] Source artifact missing: ${entry.filename}`);
      }

      const stats = fs.statSync(artifactPath);
      if (stats.size !== entry.expected_bytes) {
        throw new Error(`[GATE A FAILURE] Size mismatch for ${entry.filename}: expected ${entry.expected_bytes}, found ${stats.size}`);
      }

      const fileBuffer = fs.readFileSync(artifactPath);
      const computedHash = crypto.createHash('sha256').update(fileBuffer).digest('hex');

      if (computedHash !== entry.sha256) {
        throw new Error(`[GATE A FAILURE] SHA-256 mismatch for ${entry.filename}! Expected ${entry.sha256}, got ${computedHash}`);
      }
    }

    return true;
  }
}
