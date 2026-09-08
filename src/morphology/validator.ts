import { Lexeme, Form, Relation } from '../types/lexical';

export interface MorphologyValidationRule {
  lemma: string;
  pos: string;
  expectedForms: { surface: string; features: Record<string, string> }[];
}

export interface NegativeTrapRule {
  base: string;
  spuriousTarget: string;
  disallowedRelation: string;
}

export class MorphologyValidator {
  /**
   * Evaluates positive morphological benchmarks (Gate C)
   */
  public static validateBenchmark(
    lexeme: Lexeme,
    forms: Form[],
    relations: Relation[],
    rule: MorphologyValidationRule
  ): { passed: boolean; failureReason?: string } {
    if (lexeme.lemma !== rule.lemma || lexeme.pos !== rule.pos) {
      return { passed: false, failureReason: `Lexeme mismatch: expected ${rule.lemma}:${rule.pos}` };
    }

    for (const exp of rule.expectedForms) {
      const matchingForm = forms.find(f => f.surface === exp.surface);
      if (!matchingForm) {
        return { passed: false, failureReason: `Missing expected surface form: ${exp.surface}` };
      }

      const hasRelation = relations.some(
        r => r.subject_id === lexeme.id && r.object_id === matchingForm.id && r.relation_type === 'HAS_FORM'
      );

      if (!hasRelation) {
        return { passed: false, failureReason: `Missing HAS_FORM relation between ${lexeme.lemma} and ${exp.surface}` };
      }
    }

    return { passed: true };
  }

  /**
   * Enforces strict false-positive regression traps (Gate D & ADR-005)
   */
  public static evaluateNegativeTraps(
    relations: Relation[],
    lexemeMap: Map<string, Lexeme>,
    traps: NegativeTrapRule[]
  ): { violations: string[] } {
    const violations: string[] = [];

    for (const trap of traps) {
      for (const rel of relations) {
        const subj = lexemeMap.get(rel.subject_id);
        const obj = lexemeMap.get(rel.object_id);

        if (!subj || !obj) continue;

        const matchesTrap = 
          (subj.lemma === trap.base && obj.lemma === trap.spuriousTarget) ||
          (subj.lemma === trap.spuriousTarget && obj.lemma === trap.base);

        if (matchesTrap && rel.relation_type === trap.disallowedRelation) {
          violations.push(
            `[GATE D TRAP TRIGGERED] Disallowed relation '${rel.relation_type}' detected between '${trap.base}' and '${trap.spuriousTarget}'`
          );
        }
      }
    }

    return { violations };
  }
}
