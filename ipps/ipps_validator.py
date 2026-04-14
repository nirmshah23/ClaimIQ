from claim.registry import register_validator
from claim.base_validator import BaseBusinessValidator

@register_validator(types=["ipps"])
class IppsBusinessValidator(BaseBusinessValidator):
    pass