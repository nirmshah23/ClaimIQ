
from claim.registry import register_validator
from claim.base_validator import BaseBusinessValidator

@register_validator(types=["opps"])
class OppsBusinessValidator(BaseBusinessValidator):
    pass

    # @rule("OPPS claim amount must be at least 100.")
    # def validate_positive_amount(self, claim):
    #     return True #float(claim["amount"]) >= 100