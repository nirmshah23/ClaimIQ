from .utils import _call_pricing_service
from abc import ABC, abstractmethod
from service.response import PricingServiceError

class BasePricer(ABC):

    @abstractmethod
    def extract_provider_data (self, claim):
        "Extract provider data submitted by user."
        pass

    @abstractmethod
    def build_provider_data_attr (self, claim):
        """create attr key using extracted provider data."""
        pass

    @abstractmethod
    def transform_input_to_service_request(self, claim, override_provider_data):
        """Build service payload."""
        pass

    def transform_service_response_to_output(self, response, claims):
        """Transform service response to claim output."""
        if not response:
            return claims

        payment_map = {}
        for item in response:
            claim_input = getattr(item, "input", None)
            if claim_input is None and isinstance(item, dict):
                claim_input = item.get("input")

            if not isinstance(claim_input, dict):
                continue

            claim_id = claim_input.get("claimid")
            if not claim_id:
                continue

            output = getattr(item, "output", None)
            if output is None and isinstance(item, dict):
                output = item.get("output")
            if output is None:
                continue

            if hasattr(output, "model_dump"):
                output_data = output.model_dump(mode="json")
            elif isinstance(output, dict):
                output_data = output
            else:
                continue

            filtered_output = {
                key: value for key, value in output_data.items() if value is not None
            }
            payment_map[claim_id] = filtered_output

        for claim in claims:
            if claim.claimid in payment_map:
                claim.claim_payment_data = payment_map[claim.claimid]

        return claims

    def price(self, claims, claim_type):

        payloads = []

        for claim in claims:
            provider_data = self.extract_provider_data(claim)
            attr = self.build_provider_data_attr(provider_data)
            payloads.append(self.transform_input_to_service_request(claim, attr))

        response = _call_pricing_service(
            payloads=payloads,
            claim_type=claim_type,
        )

        if isinstance(response, PricingServiceError):
            return response

        output = self.transform_service_response_to_output(response.results, claims)

        return output
