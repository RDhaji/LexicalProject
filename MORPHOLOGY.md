# Morphology Engine & Separation Specification
Version: 1.0.0
Status: LOCKED
Downstream From: PRD.md, ADR-003, ADR-005

## 1. The Core Morphology Invariant
**Inflection and Derivation are formally distinct linguistic subsystems and must NEVER share relational types, entity representations, or database tables.**
- Inflections map a `Lexeme` to a surface `Form` (`relation_type = 'HAS_FORM'`).
- Derivations link a base `Lexeme` to a derived `Lexeme` (`relation_type = 'DERIVED_FROM'`).
- Forms express grammatical feature bundles: person, number, tense, aspect, mood, voice, degree.
- An inflected form never instantiates a new `Lexeme`.

## 2. Strict Heuristic Prohibitions
1. **No Substring Matching:** Prefix/suffix overlaps (e.g., "in-" in "internet", "car" in "carpet") never generate relationships.
2. **No Stemmer Inversion:** Algorithmic stemmers (Porter, Snowball, Krovetz) must NEVER be inverted into generative grammars.
3. **Compound Deconstruction Guard:** Compounding requires both constituents to be independently attested canonical lexemes or root morphemes.
