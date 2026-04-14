from dataclasses import dataclass

# Create your models here.

@dataclass # define how rule results will be structured
class RuleResult:
    rule_id: str
    severity: str     # e.g. "error", "warning", "info"
    message: str
    passed: bool
