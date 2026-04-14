
from fastapi import APIRouter, FastAPI, HTTPException
from fastapi.responses import JSONResponse

from .claim_type_registry import CLAIM_TYPE_REGISTRY
from .logging_config import configure_logging
from .orchestra import Orchestra
from .settings import settings
from service.response import PricingServiceError

from input.base_claim import BaseClaim


configure_logging(level=settings.log_level, json_logs=settings.log_json)

app = FastAPI(title="ClaimCraft API")
router = APIRouter()

@router.post("/api/v1/price-claims")
def price_claims(claims: list[BaseClaim]):
    if not isinstance(claims, list):
        raise HTTPException(status_code=400, detail="Input must be a list of claims.")

    service = Orchestra(CLAIM_TYPE_REGISTRY)

    try:
        result = service.process(claims)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if isinstance(result, PricingServiceError):
        return JSONResponse(status_code=502, content=result.model_dump(mode="json"))

    response = {
        "success_count": len(result["priced_claims"]),
        "failed_count": len(result["validation_errors"]),
        "results": result["priced_claims"],
        "errors": result["validation_errors"],
    }

    return response

app.include_router(router)

# Backward-compatible alias for existing imports.
#api = app
