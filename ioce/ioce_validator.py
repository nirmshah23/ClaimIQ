from claim.registry import register_validator
from claim.base_validator import BaseBusinessValidator

@register_validator(types=["ioce"])
class IoceBusinessValidator(BaseBusinessValidator):
    pass