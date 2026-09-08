const crypto = require("crypto");

const NAMESPACE_OID = "6ba7b812-9dad-11d1-80b4-00c04fd430c8";
function generateUUID(name) {
  return crypto.createHash("sha1").update(NAMESPACE_OID + name).digest("hex").replace(
    /(.{8})(.{4})(.{4})(.{4})(.{12})/,
    "$1-$2-5$3-$4-$5"
  ).slice(0, 36);
}

function normalizeString(str) {
  return (str || "").normalize("NFC").trim().toLowerCase();
}

/**
 * Curated Irregular / Suppletive Exception Tables (Priority 1)
 */
const IRREGULAR_INFLECTIONS = {
  "go:V": {
    "past": { surface: "went", type: "SUPPLETIVE", features: { tense: "past" } },
    "participle_past": { surface: "gone", type: "SUPPLETIVE", features: { aspect: "perfect", form: "participle" } }
  },
  "run:V": {
    "past": { surface: "ran", type: "IRREGULAR", features: { tense: "past" } },
    "pres_3sg": { surface: "runs", type: "INFLECTED", features: { tense: "present", person: "3", number: "singular" } },
    "participle_pres": { surface: "running", type: "INFLECTED", features: { aspect: "progressive", form: "participle" } }
  },
  "be:V": {
    "pres_1sg": { surface: "am", type: "SUPPLETIVE", features: { tense: "present", person: "1", number: "singular" } },
    "pres_3sg": { surface: "is", type: "SUPPLETIVE", features: { tense: "present", person: "3", number: "singular" } },
    "pres_pl": { surface: "are", type: "SUPPLETIVE", features: { tense: "present", number: "plural" } },
    "past_sg": { surface: "was", type: "SUPPLETIVE", features: { tense: "past", number: "singular" } },
    "past_pl": { surface: "were", type: "SUPPLETIVE", features: { tense: "past", number: "plural" } }
  },
  "good:ADJ": {
    "comparative": { surface: "better", type: "SUPPLETIVE", features: { degree: "comparative" } },
    "superlative": { surface: "best", type: "SUPPLETIVE", features: { degree: "superlative" } }
  },
  "bad:ADJ": {
    "comparative": { surface: "worse", type: "SUPPLETIVE", features: { degree: "comparative" } },
    "superlative": { surface: "worst", type: "SUPPLETIVE", features: { degree: "superlative" } }
  },
  "mouse:N": {
    "plural": { surface: "mice", type: "IRREGULAR", features: { number: "plural" } }
  },
  "child:N": {
    "plural": { surface: "children", type: "IRREGULAR", features: { number: "plural" } }
  }
};

/**
 * Validated Orthographic Rules for Regular English Inflections
 */
function applyRegularVerbInflections(lemma) {
  const forms = [];
  const norm = normalizeString(lemma);

  // 3rd Person Singular Present
  let pres3sg = norm + "s";
  if (norm.endsWith("s") || norm.endsWith("sh") || norm.endsWith("ch") || norm.endsWith("x") || norm.endsWith("z")) {
    pres3sg = norm + "es";
  } else if (norm.endsWith("y") && !/[aeiou]y$/.test(norm)) {
    pres3sg = norm.slice(0, -1) + "ies";
  }
  forms.push({ surface: pres3sg, slot: "pres_3sg", features: { tense: "present", person: "3", number: "singular" }, type: "INFLECTED" });

  // Present Participle / Progressive
  let prog = norm + "ing";
  if (norm.endsWith("ee")) {
    prog = norm + "ing";
  } else if (norm.endsWith("e") && !norm.endsWith("ie")) {
    prog = norm.slice(0, -1) + "ing";
  } else if (norm.endsWith("ie")) {
    prog = norm.slice(0, -2) + "ying";
  } else if (/[bcdfghjklmnpqrstvwxyz][aeiou][bcdfgklmnprtvz]$/.test(norm) && !norm.endsWith("w") && !norm.endsWith("x") && !norm.endsWith("y")) {
    prog = norm + norm.slice(-1) + "ing"; // Consonant doubling
  }
  forms.push({ surface: prog, slot: "participle_pres", features: { aspect: "progressive", form: "participle" }, type: "INFLECTED" });

  // Past / Past Participle (Regular -ed)
  let past = norm + "ed";
  if (norm.endsWith("e")) {
    past = norm + "d";
  } else if (norm.endsWith("y") && !/[aeiou]y$/.test(norm)) {
    past = norm.slice(0, -1) + "ied";
  } else if (/[bcdfghjklmnpqrstvwxyz][aeiou][bcdfgklmnprtvz]$/.test(norm) && !norm.endsWith("w") && !norm.endsWith("x") && !norm.endsWith("y")) {
    past = norm + norm.slice(-1) + "ed"; // Consonant doubling
  }
  forms.push({ surface: past, slot: "past", features: { tense: "past" }, type: "INFLECTED" });

  return forms;
}

function applyRegularAdjectiveInflections(lemma) {
  const forms = [];
  const norm = normalizeString(lemma);

  let cmpr = norm + "er";
  let sprl = norm + "est";

  if (norm.endsWith("e")) {
    cmpr = norm + "r";
    sprl = norm + "st";
  } else if (norm.endsWith("y") && !/[aeiou]y$/.test(norm)) {
    cmpr = norm.slice(0, -1) + "ier";
    sprl = norm.slice(0, -1) + "iest";
  }
  forms.push({ surface: cmpr, slot: "comparative", features: { degree: "comparative" }, type: "INFLECTED" });
  forms.push({ surface: sprl, slot: "superlative", features: { degree: "superlative" }, type: "INFLECTED" });
  return forms;
}

/**
 * Inflection Engine: Synthesizes or retrieves all attested inflectional forms for a Lexeme.
 */
class InflectionEngine {
  static getInflectionsForLexeme(lemma, pos) {
    const norm = normalizeString(lemma);
    const key = norm + ":" + (pos === "VERB" ? "V" : pos === "ADJECTIVE" ? "ADJ" : pos === "NOUN" ? "N" : "OTHER");

    // Check irregular / suppletive table first
    const irregulars = IRREGULAR_INFLECTIONS[key] || {};
    let generated = [];

    if (pos === "VERB") {
      generated = applyRegularVerbInflections(norm);
    } else if (pos === "ADJECTIVE") {
      generated = applyRegularAdjectiveInflections(norm);
    } else if (pos === "NOUN") {
      const pl = norm.endsWith("s") || norm.endsWith("sh") || norm.endsWith("ch") || norm.endsWith("x") ? norm + "es" : norm + "s";
      generated = [{ surface: pl, slot: "plural", features: { number: "plural" }, type: "INFLECTED" }];
    }

    // Irregular entries strictly override regular rules
    const resultMap = new Map();
    for (const g of generated) {
      resultMap.set(g.slot, g);
    }
    for (const [slot, irr] of Object.entries(irregulars)) {
      resultMap.set(slot, { slot, surface: irr.surface, features: irr.features, type: irr.type });
    }

    return Array.from(resultMap.values());
  }

  static async materializeInflections(db, lexemeId, lemma, pos, sourceId = "SYSTEM_RULE_ENGINE") {
    const run = (q, p = []) => new Promise((resolve, reject) => {
      db.run(q, p, function (err) {
        if (err) reject(err);
        else resolve(this);
      });
    });

    const inflections = InflectionEngine.getInflectionsForLexeme(lemma, pos);
    const baseFormId = generateUUID("form:" + normalizeString(lemma));

    for (const inf of inflections) {
      const normSurface = normalizeString(inf.surface);
      const formId = generateUUID("form:" + normSurface + ":" + inf.slot);
      const evidence = inf.type === "SUPPLETIVE" || inf.type === "IRREGULAR" ? "ATTESTED" : "GENERATED";

      // 1. Insert Form entity
      await run(
        `INSERT OR REPLACE INTO forms (id, surface, normalized_surface, features_json, form_type, source, evidence, confidence)
         VALUES (?, ?, ?, ?, ?, ?, ?, ?)`,
        [formId, inf.surface, normSurface, JSON.stringify(inf.features), inf.type, sourceId, evidence, 1.0]
      );

      // 2. Link Lexeme -> Form via HAS_FORM
      const relFormId = generateUUID("rel:has_form:" + lexemeId + ":" + formId);
      await run(
        `INSERT OR IGNORE INTO relations (id, subject_type, subject_id, relation_type, object_type, object_id, evidence_type, confidence, resolution_status)
         VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)`,
        [relFormId, "LEXEME", lexemeId, "HAS_FORM", "FORM", formId, evidence, 1.0, "RESOLVED"]
      );

      // 3. Link Base Form -> Inflected Form via INFLECTS_TO
      const relInflectId = generateUUID("rel:inflects_to:" + baseFormId + ":" + formId);
      await run(
        `INSERT OR IGNORE INTO relations (id, subject_type, subject_id, relation_type, object_type, object_id, evidence_type, confidence, resolution_status)
         VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)`,
        [relInflectId, "FORM", baseFormId, "INFLECTS_TO", "FORM", formId, evidence, 1.0, "RESOLVED"]
      );
    }
  }
}

/**
 * Derivation Engine: Encapsulates explicit derivational processes.
 * Substring matches are strictly banned (PRD §13, ADR-005).
 */
class DerivationEngine {
  static async linkDerivation(db, sourceLexemeId, targetLexemeId, derivationType, sourceId = "SYSTEM_DERIVATION") {
    const run = (q, p = []) => new Promise((resolve, reject) => {
      db.run(q, p, function (err) {
        if (err) reject(err);
        else resolve(this);
      });
    });

    const relId = generateUUID("rel:derived:" + targetLexemeId + ":" + sourceLexemeId);
    await run(
      `INSERT OR REPLACE INTO relations (id, subject_type, subject_id, relation_type, object_type, object_id, evidence_type, confidence, resolution_status)
       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)`,
      [relId, "LEXEME", targetLexemeId, "DERIVED_FROM", "LEXEME", sourceLexemeId, "EXPLICIT", 1.0, "RESOLVED"]
    );
  }
}

/**
 * Morphological Composition Engine: Hierarchical trees with Morpheme nodes.
 */
class CompositionEngine {
  static async registerMorpheme(db, shape, type, status = "ATTESTED") {
    const run = (q, p = []) => new Promise((resolve, reject) => {
      db.run(q, p, function (err) {
        if (err) reject(err);
        else resolve(this);
      });
    });

    const morphemeId = generateUUID("morpheme:" + normalizeString(shape) + ":" + type);
    await run(
      `INSERT OR IGNORE INTO morphemes (id, shape, type, status) VALUES (?, ?, ?, ?)`,
      [morphemeId, shape, type, status]
    );
    return morphemeId;
  }

  static async buildStructure(db, targetId, targetType, structureType, components, sourceId = "SYSTEM_MORPH") {
    const run = (q, p = []) => new Promise((resolve, reject) => {
      db.run(q, p, function (err) {
        if (err) reject(err);
        else resolve(this);
      });
    });

    const structId = generateUUID("morph_struct:" + targetId + ":" + structureType);
    await run(
      `INSERT OR REPLACE INTO morphological_structures (id, target_type, target_id, structure_type, components, source, evidence, confidence)
       VALUES (?, ?, ?, ?, ?, ?, ?, ?)`,
      [structId, targetType, targetId, structureType, JSON.stringify(components), sourceId, "EXPLICIT", 1.0]
    );
    return structId;
  }
}

module.exports = {
  InflectionEngine,
  DerivationEngine,
  CompositionEngine,
  generateUUID,
  normalizeString
};
