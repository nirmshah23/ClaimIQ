# app/validators/validator_engine.py

from .registry import get_validators_for_type
from .domain_models import RuleResult

class CompositeClaimValidator:
    def __init__(self, claim_type):
        self.claim_type = claim_type
        self.validators = [v() for v in get_validators_for_type(claim_type)]

    def run_all(self, claim):
        """Aggregate rule results with override resolution."""
        seen_rules = {}
        for validator in self.validators:
            for method in validator.get_rule_methods():
                rule_id = method._rule_metadata["rule_id"]
                seen_rules[rule_id] = (validator, method)

        results = []
        for rule_id, (validator, method) in seen_rules.items():
            meta = method._rule_metadata
            if meta["condition"] and not meta["condition"](claim):
                continue
            passed = bool(method(claim))
            results.append(RuleResult(
                    rule_id=rule_id,
                    severity=meta["severity"],
                    message=meta["message"],
                    passed=passed
                ))
                
        return results

    def summary(self, claim):
        results = self.run_all(claim)
        summary = {
            "errors": [r for r in results if not r.passed and r.severity == "error"],
            "warnings": [r for r in results if not r.passed and r.severity == "warning"],
            "passed": [r for r in results if r.passed],
        }
        return summary
