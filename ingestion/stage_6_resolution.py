from typing import List, Dict, Any

class ClaimResolutionEngine:
    """
    Enforces ADR-002:
    - Never silently overwrite or merge contradictory source assertions.
    - If multiple sources agree: evidence_type = ATTESTED, confidence = 1.0.
    - If sources conflict: resolution_status = CONFLICTING, evidence_type = UNCERTAIN, confidence = 0.5.
    - Preserves all claim references in the relation_claims link table.
    """

    def resolve_claims(self, claims: List[Dict[str, Any]]) -> Dict[str, Any]:
        if not claims:
            raise ValueError("Cannot resolve empty claim set")

        first_val = claims[0]["asserted_value"]
        has_conflict = any(c["asserted_value"] != first_val for c in claims)

        claim_ids = [c["claim_id"] for c in claims]

        if has_conflict:
            return {
                "resolved_value": first_val,
                "resolution_status": "CONFLICTING",
                "evidence_type": "UNCERTAIN",
                "confidence": 0.50,
                "claim_ids": claim_ids
            }
        else:
            evidence = "ATTESTED" if len(claims) > 1 else claims[0].get("evidence_type", "EXPLICIT")
            return {
                "resolved_value": first_val,
                "resolution_status": "RESOLVED",
                "evidence_type": evidence,
                "confidence": 1.00,
                "claim_ids": claim_ids
            }
