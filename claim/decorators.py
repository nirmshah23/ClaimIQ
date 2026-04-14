# app/validators/decorators.py
#import functools

def rule(message, severity="error", condition=None):
    """
    
    Decorator to annotate validation methods with metadata.
    - rule_id: unique identifier. will be auto-generated
    - message: human-readable message
    - severity: error/warning/info
    - condition: optional callable (claim -> bool), allows to define applicability based on claim data
    
    """
    def decorator(func):
        func._rule_metadata = {
            "rule_id": None,   # placeholder
            "message": message,
            "severity": severity,
            "condition": condition,
        }
        return func
    return decorator
