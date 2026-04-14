
import itertools

_rule_id_counter = itertools.count(1)

def next_rule_id():
    """Generate a unique numeric rule ID per process."""
    return next(_rule_id_counter)
