# ADR-003: Lexeme and Form Separation
Status: APPROVED
Date: 2026-09-04

Enforce strict physical and schema separation between abstract Lexeme nodes and grammatical Form realizations. Inflectional variants map via `HAS_FORM` carrying UniMorph feature bundles. A Form never instantiates a new Lexeme.
