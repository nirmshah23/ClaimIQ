from snf.snf_pricer import SNFPricer
from snf.snf_model import SNFClaim
from snf.snf_validator import SNFBusinessValidator

from opps.opps_model import OppsClaim
from opps.opps_pricer import OPPSPricer
from opps.opps_validator import OppsBusinessValidator

from ioce.ioce_pricer import IOCEPricer
from ioce.ioce_validator import IoceBusinessValidator

from ipps.ipps_model import IppsClaim
from ipps.ipps_pricer import IPPSPricer
from ipps.ipps_validator import IppsBusinessValidator

from hospice.hospice_model import HospiceClaim
from hospice.hospice_pricer import HospicePricer
from hospice.hospice_validator import HospiceBusinessValidator

CLAIM_TYPE_REGISTRY = {
    "snf": {
        "model": SNFClaim,
        "pricing_logic": SNFPricer,
        "validator_factory": SNFBusinessValidator,       
    },
    "opps": {
        "model": OppsClaim,
        "pricing_logic": OPPSPricer,
        "validator_factory": OppsBusinessValidator,       
    },
    "ioce": {
        "model": OppsClaim,# Using OppsClaim for IOCE claims as well
        "pricing_logic": IOCEPricer,
        "validator_factory": IoceBusinessValidator,
    },
    "ipps": {
        "model": IppsClaim,
        "pricing_logic": IPPSPricer,
        "validator_factory": IppsBusinessValidator,
    },
    "hospice": {
        "model": HospiceClaim,
        "pricing_logic": HospicePricer,
        "validator_factory": HospiceBusinessValidator,
    },
}
