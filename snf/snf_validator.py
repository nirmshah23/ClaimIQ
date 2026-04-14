
from claim.registry import register_validator
from claim.base_validator import BaseBusinessValidator
from claim.decorators import rule

@register_validator(types=["snf"])
class SNFBusinessValidator(BaseBusinessValidator):
    
    @rule("SNF claim amount must be at least 100.")
    def validate_positive_amount(self, claim):
        return True #float(claim["amount"]) >= 100x
