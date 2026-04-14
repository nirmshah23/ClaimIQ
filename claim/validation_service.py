# app/services/validation_service.py
class ClaimValidationService:
    def __init__(self, claim_type, registry):
        self.claim_type = claim_type
        self.registry = registry

    def build_business_rule_validator(self):
        if self.claim_type not in self.registry:
            raise ValueError(f"Unsupported claim type: {self.claim_type}")

        config = self.registry[self.claim_type]
        validator_factory = config.get("validator_factory")

        if not validator_factory:
            raise ValueError(
                f"Validator factory not configured for claim type: {self.claim_type}"
            )

        return validator_factory()

    def _claim_id(self, claim):
        return claim.claimid

    def _summary_from_validator(self, validator, claim):
        if hasattr(validator, "summary"):
            return validator.summary(claim)

        results = validator.run_all(claim)
        return {
            "errors": [r for r in results if (not r.passed) and str(r.severity).lower() == "error"],
            "warnings": [r for r in results if (not r.passed) and str(r.severity).lower() == "warning"],
            "passed": [r for r in results if r.passed],
        }

    def validate_claims(self, claims):
        all_claims_results = []
        business_valid_claims = []
        validator = self.build_business_rule_validator()

        for claim in claims:
            validation_summary = self._summary_from_validator(validator, claim)
            errors = [r.message for r in validation_summary["errors"]]
            warnings = [r.message for r in validation_summary["warnings"]]

            result = {
                "claimid": self._claim_id(claim),
                "validation": {
                    "errors": errors,
                    "warnings": warnings,
                    "passed": not errors,
                    "rules": [
                        {
                            "rule_id": r.rule_id,
                            "message": r.message,
                            "severity": r.severity,
                            "passed": r.passed,
                        }
                        for r in (
                            validation_summary["errors"]
                            + validation_summary["warnings"]
                        )
                    ],
                },
                "pricing": None,
            }

            if not errors:
                business_valid_claims.append(claim)

            all_claims_results.append(result)

        return all_claims_results, business_valid_claims
