
from typing_extensions import Annotated
from input.base_claim import BaseClaim
from pydantic import BaseModel, ConfigDict, Field
from typing import Any, Literal

ClaimInput = dict[str, Any]

ModuleOutput = dict[str, Any]

class ServiceOutput(BaseModel):
    model_config = ConfigDict(json_schema_mode_override="validation")
    error: str | None = None
    # Editors
    ioce: ModuleOutput | None = None
    mce: ModuleOutput | None = None
    # Groupers
    hhag: ModuleOutput | None = None
    msdrg: ModuleOutput | None = None
    cmg: ModuleOutput | None = None
    # Pricers
    ipps: ModuleOutput | None = None
    opps: ModuleOutput | None = None
    psych: ModuleOutput | None = None
    ltch: ModuleOutput | None = None
    irf: ModuleOutput | None = None
    hospice: ModuleOutput | None = None
    snf: ModuleOutput | None = None
    hha: ModuleOutput | None = None
    esrd: ModuleOutput | None = None
    fqhc: ModuleOutput | None = None
    ipsf: ModuleOutput | None = None   
    opsf: ModuleOutput | None = None
    asc: ModuleOutput | None = None
	
class ServiceIO(BaseModel):
    """Container for claim input/output pairs - used for batch results and exports."""

    input: Annotated[
        ClaimInput | None, Field(default=None, json_schema_extra={"readOnly": False})
    ]
    output: Annotated[
        ServiceOutput | None, Field(default=None, json_schema_extra={"readOnly": True})
    ]

class PricingServiceSuccess(BaseModel):
    status: Literal["Success"]
    results: list[ServiceIO]

class PricingServiceError(BaseModel):
    status: Literal["Error"]
    error: str

PricingServiceResponse = PricingServiceSuccess | PricingServiceError


