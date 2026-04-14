
from collections import defaultdict

VALIDATOR_REGISTRY = defaultdict(list)

def register_validator(types):
    """
    Decorator for registering a validator for one or more claim types.
    Example:
        @register_validator(types=["hospital", "lab"])
    """
    def decorator(cls):
        for claim_type in types:
            VALIDATOR_REGISTRY[claim_type.lower()].append(cls)
        return cls
    return decorator


def get_validators_for_type(claim_type):
    """
    Return list of validator classes applicable for given claim type,
    including 'universal' (base) validators.
    """
    from .base_validator import BaseBusinessValidator  # avoid circular import

    validators = [BaseBusinessValidator]  # universal rules always included
    validators.extend(VALIDATOR_REGISTRY.get(claim_type.lower(), []))
    return validators
