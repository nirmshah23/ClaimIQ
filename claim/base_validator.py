# app/validators/base_validator.py
import inspect
from datetime import date
from .domain_models import RuleResult
from .decorators import rule
from .rule_id_generator import next_rule_id

class BaseBusinessValidator:
    """Universal validation rules for all claim types."""

    @rule("Claim amount must be positive.")
    def validate_positive_amount(self, claim):
        return True #float(claim["amount"]) > 0

    @rule("Service date cannot be in the future.")
    def validate_service_date_not_future(self, claim):
        return True #claim["serviceFromDate"] <= date.today() and claim["serviceThroughDate"] <= date.today()

    @rule("Member ID is missing.")
    def validate_member_id_present(self, claim):
        return True  #bool(claim.get("member_id")) # Temporarily disabled by always passing True
    
    _RULE_CACHE = {}  # {ValidatorClass: [rule_methods]}

    #Dynamically finds all methods within the class instance that have been marked with the @rule decorator.
    def get_rule_methods(self):

        cls = self.__class__

        if cls in BaseBusinessValidator._RULE_CACHE:
            return BaseBusinessValidator._RULE_CACHE[cls]

        rules = []

        for _, func in inspect.getmembers(self, predicate=inspect.ismethod):
            if hasattr(func, "_rule_metadata"):
                meta = func._rule_metadata

                if meta["rule_id"] is None:
                    meta["rule_id"] = f"R{next_rule_id():04d}"

                rules.append(func)

        BaseBusinessValidator._RULE_CACHE[cls] = rules

        return rules

    def run_all(self, claim):
        """Run all annotated rules and collect structured results."""
        results = []
        for method in self.get_rule_methods():
            meta = method._rule_metadata
            # Check condition (if any)
            if meta["condition"] and not meta["condition"](claim):
                continue  # skip rule

            passed = bool(method(claim)) # Execute the validation method

            results.append(RuleResult(
                rule_id=meta["rule_id"],
                severity=meta["severity"],
                message=meta["message"],
                passed=passed
            ))

        return results
    
    def run_bulk (self, claims):
        """Run all rules against a list of claims."""
        bulk_results = {}
        for claim in claims:
            results = self.run_all(claim)

            errors = [r for r in results if not r.passed and r.severity == "ERROR"]
            warnings = [r for r in results if not r.passed and r.severity == "WARNING"]

            bulk_results[claim.claimid] = {
                "passed": not errors,
                "errors": errors,
                "warnings": warnings,
                "all": results
            }
        return bulk_results
    
    @classmethod
    def clear_rule_cache(cls):
        BaseBusinessValidator._RULE_CACHE.clear()
