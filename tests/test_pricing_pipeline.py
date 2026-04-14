import pytest
import requests
from fastapi.testclient import TestClient
from pydantic import ValidationError

from claim.api import app
from claim.base_pricer import BasePricer
from claim.orchestra import ClaimPricingService, Orchestra
from claim.utils import _call_pricing_service
from hospice.hospice_model import HospiceClaim
from input.base_claim import BaseClaim, Modules
from service.response import PricingServiceError, PricingServiceSuccess, ServiceIO, ServiceOutput
from snf.snf_model import SNFClaim
from snf.snf_utils import transform_snfClaimData_to_snfServiceRequest


VALID_BILLING_PROVIDER = {"npi": "1234567890"}
VALID_SNF_LINE = {"hcpcs": "A1234", "units": 1, "revenue_code": "0022"}
VALID_HOSPICE_LINE = {
    "service_date": "2026-03-01T00:00:00",
    "hcpcs": "Q5001",
    "units": 1,
}
VALID_HOSPICE_VALUE_CODE = {"code": "61", "amount": 1.0}


class DummyPricer(BasePricer):
    def extract_provider_data(self, claim):
        return claim

    def build_provider_data_attr(self, claim):
        return claim

    def transform_input_to_service_request(self, claim, override_provider_data):
        return {"claimid": claim.claimid}


class FakeResponse:
    def __init__(self, status_code, payload=None, text=""):
        self.status_code = status_code
        self._payload = payload
        self.text = text

    def json(self):
        if isinstance(self._payload, Exception):
            raise self._payload
        return self._payload


class FakeSession:
    def __init__(self, response=None, exc=None):
        self.response = response
        self.exc = exc

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def mount(self, prefix, adapter):
        return None

    def post(self, url, json, timeout):
        if self.exc is not None:
            raise self.exc
        return self.response


class FakeOrchestra:
    def __init__(self, result):
        self.result = result

    def process(self, claims):
        return self.result


@pytest.fixture
def client():
    return TestClient(app)


def test_transform_service_response_to_output_stores_only_non_none_output_fields():
    pricer = DummyPricer()
    claims = [
        BaseClaim(claimid="c1", billing_provider=VALID_BILLING_PROVIDER),
        BaseClaim(claimid="c2", billing_provider=VALID_BILLING_PROVIDER),
    ]
    results = [
        ServiceIO(
            input={"claimid": "c1"},
            output=ServiceOutput(snf={"rate": 100}, opps=None, error=None),
        ),
        ServiceIO(
            input={"claimid": "c2"},
            output=ServiceOutput(error="warn", ipps={"drg": "001"}, snf=None),
        ),
    ]

    output_claims = pricer.transform_service_response_to_output(results, claims)

    assert output_claims[0].claim_payment_data == {"snf": {"rate": 100}}
    assert output_claims[1].claim_payment_data == {
        "error": "warn",
        "ipps": {"drg": "001"},
    }


def test_transform_service_response_to_output_skips_invalid_items():
    pricer = DummyPricer()
    claims = [
        BaseClaim(claimid="c1", billing_provider=VALID_BILLING_PROVIDER),
        BaseClaim(claimid="c2", billing_provider=VALID_BILLING_PROVIDER),
    ]
    results = [
        ServiceIO(input=None, output=ServiceOutput(snf={"rate": 100})),
        ServiceIO(input={"claimid": ""}, output=ServiceOutput(snf={"rate": 200})),
        ServiceIO(input={"claimid": "c2"}, output=None),
    ]

    output_claims = pricer.transform_service_response_to_output(results, claims)

    assert output_claims[0].claim_payment_data == {}
    assert output_claims[1].claim_payment_data == {}


def test_base_pricer_price_returns_typed_error_unchanged(monkeypatch):
    monkeypatch.setattr(
        "claim.base_pricer._call_pricing_service",
        lambda payloads, claim_type: PricingServiceError(status="Error", error="boom"),
    )
    pricer = DummyPricer()

    response = pricer.price(
        [BaseClaim(claimid="c1", billing_provider=VALID_BILLING_PROVIDER)],
        claim_type="snf",
    )

    assert isinstance(response, PricingServiceError)
    assert response.error == "boom"


def test_base_pricer_price_uses_results_from_success_response(monkeypatch):
    monkeypatch.setattr(
        "claim.base_pricer._call_pricing_service",
        lambda payloads, claim_type: PricingServiceSuccess(
            status="Success",
            results=[
                ServiceIO(
                    input={"claimid": "c1"},
                    output=ServiceOutput(snf={"rate": 100}),
                )
            ],
        ),
    )
    pricer = DummyPricer()

    response = pricer.price(
        [BaseClaim(claimid="c1", billing_provider=VALID_BILLING_PROVIDER)],
        claim_type="snf",
    )

    assert response[0].claim_payment_data == {"snf": {"rate": 100}}


def test_call_pricing_service_parses_success_envelope(monkeypatch):
    monkeypatch.setattr(
        "claim.utils.requests.Session",
        lambda: FakeSession(
            response=FakeResponse(
                200,
                {
                    "status": "Success",
                    "results": [
                        {
                            "input": {"claimid": "c1"},
                            "output": {"snf": {"rate": 100}},
                        }
                    ],
                },
            )
        ),
    )

    response = _call_pricing_service([{"claimid": "c1"}], "snf")

    assert isinstance(response, PricingServiceSuccess)
    assert response.results[0].input["claimid"] == "c1"


def test_call_pricing_service_parses_error_envelope(monkeypatch):
    monkeypatch.setattr(
        "claim.utils.requests.Session",
        lambda: FakeSession(
            response=FakeResponse(200, {"status": "Error", "error": "pricing failed"})
        ),
    )

    response = _call_pricing_service([{"claimid": "c1"}], "snf")

    assert isinstance(response, PricingServiceError)
    assert response.error == "pricing failed"


def test_call_pricing_service_non_200_returns_http_error_with_body(monkeypatch):
    monkeypatch.setattr(
        "claim.utils.requests.Session",
        lambda: FakeSession(
            response=FakeResponse(502, {"unexpected": "payload"}, text="gateway timeout")
        ),
    )

    response = _call_pricing_service([{"claimid": "c1"}], "snf")

    assert isinstance(response, PricingServiceError)
    assert response.error == "Pricing service returned HTTP 502: gateway timeout"


def test_call_pricing_service_handles_invalid_json(monkeypatch):
    monkeypatch.setattr(
        "claim.utils.requests.Session",
        lambda: FakeSession(
            response=FakeResponse(200, payload=ValueError("bad json"), text="not-json")
        ),
    )

    response = _call_pricing_service([{"claimid": "c1"}], "snf")

    assert isinstance(response, PricingServiceError)
    assert "Invalid pricing service JSON response" in response.error


def test_call_pricing_service_handles_invalid_contract(monkeypatch):
    monkeypatch.setattr(
        "claim.utils.requests.Session",
        lambda: FakeSession(
            response=FakeResponse(200, {"status": "Success", "error": "wrong-shape"})
        ),
    )

    response = _call_pricing_service([{"claimid": "c1"}], "snf")

    assert isinstance(response, PricingServiceError)
    assert response.error == "Invalid pricing service response contract"


def test_call_pricing_service_handles_transport_failure(monkeypatch):
    monkeypatch.setattr(
        "claim.utils.requests.Session",
        lambda: FakeSession(exc=requests.RequestException("network down")),
    )

    response = _call_pricing_service([{"claimid": "c1"}], "snf")

    assert isinstance(response, PricingServiceError)
    assert response.error == "Error while calculating payment data"


def test_claim_pricing_service_returns_typed_error():
    class ErrorPricer:
        def price(self, claims, claim_type):
            return PricingServiceError(status="Error", error="pricing failed")

    pricing_service = ClaimPricingService(
        {"snf": {"pricing_logic": ErrorPricer, "model": BaseClaim}}
    )

    response = pricing_service.price_claims(
        "snf", [BaseClaim(claimid="c1", billing_provider=VALID_BILLING_PROVIDER)]
    )

    assert isinstance(response, PricingServiceError)
    assert response.error == "pricing failed"


def test_claim_pricing_service_builds_lookup_for_priced_claims():
    class SuccessPricer:
        def price(self, claims, claim_type):
            claim = BaseClaim(claimid="c1", billing_provider=VALID_BILLING_PROVIDER)
            claim.claim_payment_data = {"snf": {"rate": 100}}
            return [claim]

    pricing_service = ClaimPricingService(
        {"snf": {"pricing_logic": SuccessPricer, "model": BaseClaim}}
    )

    response = pricing_service.price_claims(
        "snf", [BaseClaim(claimid="c1", billing_provider=VALID_BILLING_PROVIDER)]
    )

    assert response["c1"]["claim_payment_data"] == {"snf": {"rate": 100}}


def test_orchestra_process_propagates_typed_pricing_error(monkeypatch):
    class ErrorPricer:
        def price(self, claims, claim_type):
            return PricingServiceError(status="Error", error="pricing failed")

    registry = {
        "snf": {
            "model": BaseClaim,
            "pricing_logic": ErrorPricer,
            "validator_factory": lambda: object(),
        }
    }
    claim = BaseClaim(
        claimid="c1",
        modules=[Modules.SNF],
        billing_provider=VALID_BILLING_PROVIDER,
    )

    monkeypatch.setattr(Orchestra, "_normalize_modules", lambda self, modules: ["snf"])
    monkeypatch.setattr(
        "claim.validation_service.ClaimValidationService._summary_from_validator",
        lambda self, validator, claim: {"errors": [], "warnings": [], "passed": []},
    )

    result = Orchestra(registry).process([claim])

    assert isinstance(result, PricingServiceError)
    assert result.error == "pricing failed"


def test_snf_request_transform_preserves_pdpm_prior_days():
    claim = SNFClaim(
        claimid="SNF-1",
        from_date="2026-03-01T00:00:00",
        thru_date="2026-03-05T00:00:00",
        los=5,
        total_charges=100.0,
        patient_status="01",
        modules=["SNF"],
        billing_provider=VALID_BILLING_PROVIDER,
        lines=[VALID_SNF_LINE],
        pdpmPriorDays=7,
    )

    payload = transform_snfClaimData_to_snfServiceRequest(claim)

    assert payload["pdpmPriorDays"] == 7


def test_base_claim_preserves_unknown_fields():
    claim = BaseClaim.model_validate(
        {
            "claimid": "SNF-1",
            "modules": ["SNF"],
            "billing_provider": VALID_BILLING_PROVIDER,
            "pdpmPriorDays": 7,
        }
    )

    assert claim.pdpmPriorDays == 7


def test_base_claim_model_dump_includes_unknown_fields():
    claim = BaseClaim.model_validate(
        {
            "claimid": "SNF-1",
            "modules": ["SNF"],
            "billing_provider": VALID_BILLING_PROVIDER,
            "pdpmPriorDays": 7,
        }
    )

    dumped_claim = claim.model_dump(mode="python")

    assert dumped_claim["pdpmPriorDays"] == 7


def test_orchestra_module_schema_validation_receives_preserved_extra_fields():
    base_claim = BaseClaim.model_validate(
        {
            "claimid": "SNF-1",
            "from_date": "2026-03-01T00:00:00",
            "thru_date": "2026-03-05T00:00:00",
            "los": 5,
            "total_charges": 100.0,
            "patient_status": "01",
            "modules": ["SNF"],
            "billing_provider": VALID_BILLING_PROVIDER,
            "lines": [VALID_SNF_LINE],
            "pdpmPriorDays": 7,
        }
    )

    validated_claim = SNFClaim.model_validate(base_claim.model_dump(mode="python"))

    assert validated_claim.pdpmPriorDays == 7


def test_base_claim_copies_billing_provider_to_missing_line_servicing_provider():
    claim = BaseClaim.model_validate(
        {
            "claimid": "SNF-1",
            "billing_provider": VALID_BILLING_PROVIDER,
            "lines": [{"hcpcs": "A1234", "units": 1}],
        }
    )

    assert claim.lines[0].servicing_provider is not None
    assert claim.lines[0].servicing_provider.npi == VALID_BILLING_PROVIDER["npi"]


def test_base_claim_preserves_explicit_line_servicing_provider():
    claim = BaseClaim.model_validate(
        {
            "claimid": "SNF-1",
            "billing_provider": VALID_BILLING_PROVIDER,
            "lines": [
                {
                    "hcpcs": "A1234",
                    "units": 1,
                    "servicing_provider": {"other_id": "ALT-1"},
                }
            ],
        }
    )

    assert claim.lines[0].servicing_provider is not None
    assert claim.lines[0].servicing_provider.other_id == "ALT-1"


def test_snf_claim_accepts_valid_line_without_servicing_provider():
    claim = SNFClaim.model_validate(
        {
            "claimid": "SNF-1",
            "from_date": "2026-03-01T00:00:00",
            "thru_date": "2026-03-05T00:00:00",
            "billing_provider": VALID_BILLING_PROVIDER,
            "lines": [VALID_SNF_LINE],
            "pdpmPriorDays": 7,
        }
    )

    assert claim.lines[0].hcpcs == "A1234"
    assert claim.lines[0].units == 1
    assert claim.lines[0].servicing_provider is not None
    assert claim.lines[0].servicing_provider.npi == VALID_BILLING_PROVIDER["npi"]
    assert claim.lines[0].service_date == claim.from_date


def test_snf_claim_copies_from_date_to_missing_line_service_date():
    claim = SNFClaim.model_validate(
        {
            "claimid": "SNF-1",
            "from_date": "2026-03-01T00:00:00",
            "thru_date": "2026-03-05T00:00:00",
            "billing_provider": VALID_BILLING_PROVIDER,
            "lines": [VALID_SNF_LINE],
            "pdpmPriorDays": 7,
        }
    )

    assert claim.lines[0].service_date == claim.from_date


def test_snf_claim_requires_at_least_one_line_with_revenue_code_0022():
    with pytest.raises(
        ValidationError,
        match="SNFClaim must include at least one line with revenue_code 0022",
    ):
        SNFClaim.model_validate(
            {
                "claimid": "SNF-1",
                "from_date": "2026-03-01T00:00:00",
                "thru_date": "2026-03-05T00:00:00",
                "billing_provider": VALID_BILLING_PROVIDER,
                "lines": [{"hcpcs": "A1234", "units": 1, "revenue_code": "0123"}],
                "pdpmPriorDays": 7,
            }
        )


def test_snf_claim_requires_from_date():
    with pytest.raises(ValidationError, match="from_date"):
        SNFClaim.model_validate(
            {
                "claimid": "SNF-1",
                "thru_date": "2026-03-05T00:00:00",
                "billing_provider": VALID_BILLING_PROVIDER,
                "lines": [VALID_SNF_LINE],
                "pdpmPriorDays": 7,
            }
        )


def test_snf_claim_requires_thru_date():
    with pytest.raises(ValidationError, match="thru_date"):
        SNFClaim.model_validate(
            {
                "claimid": "SNF-1",
                "from_date": "2026-03-01T00:00:00",
                "billing_provider": VALID_BILLING_PROVIDER,
                "lines": [VALID_SNF_LINE],
                "pdpmPriorDays": 7,
            }
        )


def test_snf_claim_requires_at_least_one_line():
    with pytest.raises(ValidationError, match="lines"):
        SNFClaim.model_validate(
            {
                "claimid": "SNF-1",
                "from_date": "2026-03-01T00:00:00",
                "thru_date": "2026-03-05T00:00:00",
                "billing_provider": VALID_BILLING_PROVIDER,
                "lines": [],
                "pdpmPriorDays": 7,
            }
        )


def test_snf_line_requires_hcpcs():
    with pytest.raises(ValidationError, match="hcpcs"):
        SNFClaim.model_validate(
            {
                "claimid": "SNF-1",
                "from_date": "2026-03-01T00:00:00",
                "thru_date": "2026-03-05T00:00:00",
                "billing_provider": VALID_BILLING_PROVIDER,
                "lines": [{"units": 1}],
                "pdpmPriorDays": 7,
            }
        )


def test_snf_line_rejects_blank_hcpcs():
    with pytest.raises(ValidationError, match="hcpcs is required"):
        SNFClaim.model_validate(
            {
                "claimid": "SNF-1",
                "from_date": "2026-03-01T00:00:00",
                "thru_date": "2026-03-05T00:00:00",
                "billing_provider": VALID_BILLING_PROVIDER,
                "lines": [{"hcpcs": " ", "units": 1}],
                "pdpmPriorDays": 7,
            }
        )


def test_snf_line_rejects_non_alphanumeric_hcpcs():
    with pytest.raises(ValidationError, match="hcpcs must be alphanumeric"):
        SNFClaim.model_validate(
            {
                "claimid": "SNF-1",
                "from_date": "2026-03-01T00:00:00",
                "thru_date": "2026-03-05T00:00:00",
                "billing_provider": VALID_BILLING_PROVIDER,
                "lines": [{"hcpcs": "A12-4", "units": 1}],
                "pdpmPriorDays": 7,
            }
        )


def test_snf_line_rejects_hcpcs_longer_than_five_characters():
    with pytest.raises(ValidationError, match="hcpcs must be at most 5 characters"):
        SNFClaim.model_validate(
            {
                "claimid": "SNF-1",
                "from_date": "2026-03-01T00:00:00",
                "thru_date": "2026-03-05T00:00:00",
                "billing_provider": VALID_BILLING_PROVIDER,
                "lines": [{"hcpcs": "A12345", "units": 1}],
                "pdpmPriorDays": 7,
            }
        )


def test_snf_line_requires_units():
    with pytest.raises(ValidationError, match="units"):
        SNFClaim.model_validate(
            {
                "claimid": "SNF-1",
                "from_date": "2026-03-01T00:00:00",
                "thru_date": "2026-03-05T00:00:00",
                "billing_provider": VALID_BILLING_PROVIDER,
                "lines": [{"hcpcs": "A1234"}],
                "pdpmPriorDays": 7,
            }
        )


def test_snf_line_rejects_non_positive_units():
    with pytest.raises(ValidationError, match="units must be greater than 0"):
        SNFClaim.model_validate(
            {
                "claimid": "SNF-1",
                "from_date": "2026-03-01T00:00:00",
                "thru_date": "2026-03-05T00:00:00",
                "billing_provider": VALID_BILLING_PROVIDER,
                "lines": [{"hcpcs": "A1234", "units": 0}],
                "pdpmPriorDays": 7,
            }
        )


def test_snf_claim_rejects_from_date_after_thru_date():
    with pytest.raises(ValidationError, match="From date cannot be after thru date"):
        SNFClaim.model_validate(
            {
                "claimid": "SNF-1",
                "from_date": "2026-03-06T00:00:00",
                "thru_date": "2026-03-05T00:00:00",
                "billing_provider": VALID_BILLING_PROVIDER,
                "lines": [VALID_SNF_LINE],
                "pdpmPriorDays": 7,
            }
        )


def test_snf_claim_rejects_line_service_date_outside_claim_dates():
    with pytest.raises(
        ValidationError,
        match="Line item service date must be within claim from and thru dates",
    ):
        SNFClaim.model_validate(
            {
                "claimid": "SNF-1",
                "from_date": "2026-03-01T00:00:00",
                "thru_date": "2026-03-05T00:00:00",
                "billing_provider": VALID_BILLING_PROVIDER,
                "lines": [
                    {
                        "hcpcs": "A1234",
                        "units": 1,
                        "service_date": "2026-03-06T00:00:00",
                    }
                ],
                "pdpmPriorDays": 7,
            }
        )


def test_hospice_claim_accepts_valid_payload():
    claim = HospiceClaim.model_validate(
        {
            "claimid": "HSP-1",
            "from_date": "2026-03-01T00:00:00",
            "thru_date": "2026-03-05T00:00:00",
            "los": 5,
            "billing_provider": VALID_BILLING_PROVIDER,
            "lines": [VALID_HOSPICE_LINE],
            "value_codes": [VALID_HOSPICE_VALUE_CODE],
        }
    )

    assert claim.from_date.isoformat() == "2026-03-01T00:00:00"
    assert claim.admit_date is None
    assert claim.lines[0].service_date.isoformat() == "2026-03-01T00:00:00"
    assert claim.lines[0].hcpcs == "Q5001"
    assert claim.lines[0].units == 1
    assert claim.value_codes[0].code == "61"


def test_hospice_claim_requires_from_date():
    with pytest.raises(ValidationError, match="from_date"):
        HospiceClaim.model_validate(
            {
                "claimid": "HSP-1",
                "thru_date": "2026-03-05T00:00:00",
                "los": 5,
                "billing_provider": VALID_BILLING_PROVIDER,
                "lines": [VALID_HOSPICE_LINE],
                "value_codes": [VALID_HOSPICE_VALUE_CODE],
            }
        )


def test_hospice_claim_allows_missing_admit_date():
    claim = HospiceClaim.model_validate(
        {
            "claimid": "HSP-1",
            "from_date": "2026-03-01T00:00:00",
            "thru_date": "2026-03-05T00:00:00",
            "los": 5,
            "billing_provider": VALID_BILLING_PROVIDER,
            "lines": [VALID_HOSPICE_LINE],
            "value_codes": [VALID_HOSPICE_VALUE_CODE],
        }
    )

    assert claim.admit_date is None


def test_hospice_claim_requires_los():
    with pytest.raises(ValidationError, match="los"):
        HospiceClaim.model_validate(
            {
                "claimid": "HSP-1",
                "from_date": "2026-03-01T00:00:00",
                "thru_date": "2026-03-05T00:00:00",
                "billing_provider": VALID_BILLING_PROVIDER,
                "lines": [VALID_HOSPICE_LINE],
                "value_codes": [VALID_HOSPICE_VALUE_CODE],
            }
        )


def test_hospice_claim_requires_at_least_one_line():
    with pytest.raises(ValidationError, match="lines"):
        HospiceClaim.model_validate(
            {
                "claimid": "HSP-1",
                "from_date": "2026-03-01T00:00:00",
                "thru_date": "2026-03-05T00:00:00",
                "los": 5,
                "billing_provider": VALID_BILLING_PROVIDER,
                "lines": [],
                "value_codes": [VALID_HOSPICE_VALUE_CODE],
            }
        )


def test_hospice_claim_requires_at_least_one_value_code():
    with pytest.raises(ValidationError, match="value_codes"):
        HospiceClaim.model_validate(
            {
                "claimid": "HSP-1",
                "from_date": "2026-03-01T00:00:00",
                "thru_date": "2026-03-05T00:00:00",
                "los": 5,
                "billing_provider": VALID_BILLING_PROVIDER,
                "lines": [VALID_HOSPICE_LINE],
                "value_codes": [],
            }
        )


def test_hospice_line_requires_service_date():
    with pytest.raises(ValidationError, match="service_date"):
        HospiceClaim.model_validate(
            {
                "claimid": "HSP-1",
                "from_date": "2026-03-01T00:00:00",
                "thru_date": "2026-03-05T00:00:00",
                "los": 5,
                "billing_provider": VALID_BILLING_PROVIDER,
                "lines": [{"hcpcs": "Q5001", "units": 1}],
                "value_codes": [VALID_HOSPICE_VALUE_CODE],
            }
        )


def test_hospice_line_requires_hcpcs():
    with pytest.raises(ValidationError, match="hcpcs"):
        HospiceClaim.model_validate(
            {
                "claimid": "HSP-1",
                "from_date": "2026-03-01T00:00:00",
                "thru_date": "2026-03-05T00:00:00",
                "los": 5,
                "billing_provider": VALID_BILLING_PROVIDER,
                "lines": [{"service_date": "2026-03-01T00:00:00", "units": 1}],
                "value_codes": [VALID_HOSPICE_VALUE_CODE],
            }
        )


def test_hospice_line_rejects_blank_hcpcs():
    with pytest.raises(ValidationError, match="hcpcs is required"):
        HospiceClaim.model_validate(
            {
                "claimid": "HSP-1",
                "from_date": "2026-03-01T00:00:00",
                "thru_date": "2026-03-05T00:00:00",
                "los": 5,
                "billing_provider": VALID_BILLING_PROVIDER,
                "lines": [
                    {
                        "service_date": "2026-03-01T00:00:00",
                        "hcpcs": " ",
                        "units": 1,
                    }
                ],
                "value_codes": [VALID_HOSPICE_VALUE_CODE],
            }
        )


def test_hospice_line_requires_units():
    with pytest.raises(ValidationError, match="units"):
        HospiceClaim.model_validate(
            {
                "claimid": "HSP-1",
                "from_date": "2026-03-01T00:00:00",
                "thru_date": "2026-03-05T00:00:00",
                "los": 5,
                "billing_provider": VALID_BILLING_PROVIDER,
                "lines": [
                    {
                        "service_date": "2026-03-01T00:00:00",
                        "hcpcs": "Q5001",
                    }
                ],
                "value_codes": [VALID_HOSPICE_VALUE_CODE],
            }
        )


def test_hospice_line_rejects_zero_units():
    with pytest.raises(ValidationError, match="units must be greater than 0"):
        HospiceClaim.model_validate(
            {
                "claimid": "HSP-1",
                "from_date": "2026-03-01T00:00:00",
                "thru_date": "2026-03-05T00:00:00",
                "los": 5,
                "billing_provider": VALID_BILLING_PROVIDER,
                "lines": [
                    {
                        "service_date": "2026-03-01T00:00:00",
                        "hcpcs": "Q5001",
                        "units": 0,
                    }
                ],
                "value_codes": [VALID_HOSPICE_VALUE_CODE],
            }
        )


def test_hospice_line_rejects_negative_units():
    with pytest.raises(ValidationError, match="units must be greater than 0"):
        HospiceClaim.model_validate(
            {
                "claimid": "HSP-1",
                "from_date": "2026-03-01T00:00:00",
                "thru_date": "2026-03-05T00:00:00",
                "los": 5,
                "billing_provider": VALID_BILLING_PROVIDER,
                "lines": [
                    {
                        "service_date": "2026-03-01T00:00:00",
                        "hcpcs": "Q5001",
                        "units": -1,
                    }
                ],
                "value_codes": [VALID_HOSPICE_VALUE_CODE],
            }
        )


def test_hospice_claim_rejects_line_service_date_outside_claim_dates():
    with pytest.raises(
        ValidationError,
        match="Line item service date must be within claim from and thru dates",
    ):
        HospiceClaim.model_validate(
            {
                "claimid": "HSP-1",
                "from_date": "2026-03-01T00:00:00",
                "thru_date": "2026-03-05T00:00:00",
                "los": 5,
                "billing_provider": VALID_BILLING_PROVIDER,
                "lines": [
                    {
                        "service_date": "2026-03-06T00:00:00",
                        "hcpcs": "Q5001",
                        "units": 1,
                    }
                ],
                "value_codes": [VALID_HOSPICE_VALUE_CODE],
            }
        )


def test_api_returns_502_when_orchestra_returns_pricing_service_error(monkeypatch, client):
    monkeypatch.setattr(
        "claim.api.Orchestra",
        lambda registry: FakeOrchestra(
            PricingServiceError(status="Error", error="pricing failed")
        ),
    )

    response = client.post(
        "/api/v1/price-claims",
        json=[
            {
                "claimid": "c1",
                "modules": ["SNF"],
                "billing_provider": VALID_BILLING_PROVIDER,
                "pdpmPriorDays": 7,
            }
        ],
    )

    assert response.status_code == 502
    assert response.json() == {"status": "Error", "error": "pricing failed"}


def test_api_returns_success_payload(monkeypatch, client):
    monkeypatch.setattr(
        "claim.api.Orchestra",
        lambda registry: FakeOrchestra(
            {
                "priced_claims": [{"claimid": "c1", "pricing": {"snf": {"rate": 100}}}],
                "validation_errors": [],
            }
        ),
    )

    response = client.post(
        "/api/v1/price-claims",
        json=[
            {
                "claimid": "c1",
                "modules": ["SNF"],
                "billing_provider": VALID_BILLING_PROVIDER,
                "pdpmPriorDays": 7,
            }
        ],
    )

    assert response.status_code == 200
    assert response.json() == {
        "success_count": 1,
        "failed_count": 0,
        "results": [{"claimid": "c1", "pricing": {"snf": {"rate": 100}}}],
        "errors": [],
    }


def test_api_returns_200_for_valid_snf_claim_payload(monkeypatch, client):
    monkeypatch.setattr(
        "claim.api.Orchestra",
        lambda registry: FakeOrchestra(
            {
                "priced_claims": [{"claimid": "c1", "pricing": {"snf": {"rate": 100}}}],
                "validation_errors": [],
            }
        ),
    )

    response = client.post(
        "/api/v1/price-claims",
        json=[
            {
                "claimid": "c1",
                "modules": ["SNF"],
                "billing_provider": {"other_id": "010001"},
                "from_date": "2024-05-13T00:00:00",
                "thru_date": "2024-05-25T00:00:00",
                "lines": [
                    {
                        "hcpcs": "BARD0",
                        "revenue_code": "0022",
                        "units": 11,
                    }
                ],
                "pdpmPriorDays": 15,
            }
        ],
    )

    assert response.status_code == 200
    assert response.json() == {
        "success_count": 1,
        "failed_count": 0,
        "results": [{"claimid": "c1", "pricing": {"snf": {"rate": 100}}}],
        "errors": [],
    }


def test_base_claim_accepts_billing_provider_with_npi():
    claim = BaseClaim.model_validate(
        {
            "claimid": "SNF-1",
            "billing_provider": {"npi": "1234567890"},
        }
    )

    assert claim.billing_provider.npi == "1234567890"


def test_base_claim_accepts_billing_provider_with_other_id():
    claim = BaseClaim.model_validate(
        {
            "claimid": "SNF-1",
            "billing_provider": {"other_id": "ALT-1"},
        }
    )

    assert claim.billing_provider.other_id == "ALT-1"


def test_base_claim_requires_billing_provider():
    with pytest.raises(ValueError, match="billing_provider"):
        BaseClaim.model_validate({"claimid": "SNF-1"})


def test_provider_requires_npi_or_other_id():
    with pytest.raises(ValueError, match="Provider requires either npi or other_id"):
        BaseClaim.model_validate(
            {
                "claimid": "SNF-1",
                "billing_provider": {"npi": " ", "other_id": ""},
            }
        )
