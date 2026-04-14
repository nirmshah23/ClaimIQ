from claim.registry import register_validator
from claim.base_validator import BaseBusinessValidator
from claim.decorators import rule

@register_validator(types=["hospice"])
class HospiceBusinessValidator(BaseBusinessValidator):
    
    @rule("Hospice claim must have a valid hospice provider number.")
    def validate_hospice_provider_number(self, claim):
        # Implement logic to validate hospice provider number
        return True