import uuid
import logging
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from pydantic import TypeAdapter, ValidationError

from .settings import settings
from service.response import PricingServiceError, PricingServiceResponse

logger = logging.getLogger(__name__)
PRICING_SERVICE_RESPONSE_ADAPTER = TypeAdapter(PricingServiceResponse)

def get_create_correlation_id(headers):
    
    """Generate a unique correlation ID."""

    cid = (
        headers.get("request-id")
    )

    if not cid:
        cid = str(uuid.uuid4())

    return cid


def _build_retry():
    return Retry(
        total=settings.pricing_service_retry_total,
        connect=settings.pricing_service_retry_total,
        read=settings.pricing_service_retry_total,
        status=settings.pricing_service_retry_total,
        backoff_factor=settings.pricing_service_retry_backoff_seconds,
        status_forcelist=settings.pricing_service_retry_statuses,
        allowed_methods=frozenset(["POST"]),
        raise_on_status=False,
    )


def _parse_pricing_service_response(data):
    return PRICING_SERVICE_RESPONSE_ADAPTER.validate_python(data)


def _call_pricing_service(payloads, claim_type, timeout=None):
    base_url = settings.pricing_service_base_url.rstrip("/")
    url = f"{base_url}/v1/price"
    timeout_seconds = (
        timeout if timeout is not None else settings.pricing_service_timeout_seconds
    )

    try:
        with requests.Session() as s:
            adapter = HTTPAdapter(max_retries=_build_retry())
            s.mount("http://", adapter)
            s.mount("https://", adapter)

            logger.info(
                "pricing_request_start",
                extra={
                    "claim_type": claim_type,
                    "url": url,
                    "payload_count": len(payloads),
                    "timeout_seconds": timeout_seconds,
                },
            )

            resp = s.post(
                url,
                json=payloads,
                timeout=timeout_seconds,
            )

            if resp.status_code != 200:
                logger.warning(
                    "pricing_request_error_response",
                    extra={
                        "claim_type": claim_type,
                        "status_code": resp.status_code,
                    },
                )
                return PricingServiceError(
                    status="Error",
                    error=(
                        f"Pricing service returned HTTP {resp.status_code}: "
                        f"{resp.text[:1000]}"
                    ),
                )

            try:
                response_data = resp.json()
            except ValueError:
                logger.error(
                    "pricing_response_invalid_json",
                    extra={
                        "claim_type": claim_type,
                        "status_code": resp.status_code,
                    },
                )
                return PricingServiceError(
                    status="Error",
                    error=f"Invalid pricing service JSON response: {resp.text[:1000]}",
                )

            try:
                parsed_response = _parse_pricing_service_response(response_data)
            except ValidationError as exc:
                logger.error(
                    "pricing_response_invalid_contract",
                    extra={
                        "claim_type": claim_type,
                        "status_code": resp.status_code,
                        "validation_errors": exc.errors(),
                    },
                )
                return PricingServiceError(
                    status="Error",
                    error="Invalid pricing service response contract",
                )

            logger.info(
                "pricing_request_success",
                extra={
                    "claim_type": claim_type,
                    "status_code": resp.status_code,
                    "payload_count": len(payloads),
                },
            )
            return parsed_response
    except requests.RequestException:
        logger.exception(
            "pricing_request_failed",
            extra={"claim_type": claim_type, "url": url},
        )
        return PricingServiceError(
            status="Error",
            error="Error while calculating payment data",
        )
