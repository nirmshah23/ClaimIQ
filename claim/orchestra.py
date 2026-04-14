from pydantic import ValidationError

from .validation_service import ClaimValidationService
from service.response import PricingServiceError


class Orchestra:
    def __init__(self, registry):
        self.registry = registry
        self.routable_claim_types = set(registry)
        self.pricing_service = ClaimPricingService(registry)

    def _error_entry(self, claim, index, errors):
        return {
            "claimid": claim.claimid or "unknown",
            "index": index,
            "schema_errors": errors,
        }

    def _normalize_modules(self, modules):
        if not modules:
            return []

        return [module.value.lower() for module in modules]

    def process(self, claims):
        claim_groups = {}
        schema_validation_errors = []

        for index, claim_data in enumerate(claims):
            normalized_modules = self._normalize_modules(claim_data.modules)
            if not normalized_modules:
                schema_validation_errors.append(
                    self._error_entry(
                        claim=claim_data,
                        index=index,
                        errors=[{"msg": "Unsupported modules; unable to price claim"}],
                    )
                )
                continue

            claim_type = next(
                (module for module in normalized_modules if module in self.routable_claim_types),
                None,
            )
            if not claim_type:
                schema_validation_errors.append(
                    self._error_entry(
                        claim=claim_data,
                        index=index,
                        errors=[
                            {
                                "msg": (
                                    "Unknown module(s); unable to route claim: "
                                    f"{', '.join(normalized_modules)}"
                                )
                            }
                        ],
                    )
                )
                continue

            claim_groups.setdefault(claim_type, []).append((index, claim_data))

        priced_claims = []

        for claim_type, claim_list in claim_groups.items():
            config = self.registry[claim_type]
            claim_schema = config["model"]

            valid_claims = []
            for index, claim_data in claim_list:
                try:
                    valid_claims.append(
                        claim_schema.model_validate(claim_data.model_dump(mode="python"))
                    )
                except ValidationError as exc:
                    print (f"Validation error for claim at index {index}: {exc.errors()}")
                    schema_validation_errors.append(
                        self._error_entry(
                            claim=claim_data,
                            index=index,
                            errors=exc.errors(),
                        )
                    )

            validation_service = ClaimValidationService(
                claim_type=claim_type,
                registry=self.registry,
            )

            business_validation_results, business_valid_claims = (
                validation_service.validate_claims(valid_claims)
            )

            pricing_lookup = self.pricing_service.price_claims(
                claim_type=claim_type,
                claims=business_valid_claims,
            )

            if isinstance(pricing_lookup, PricingServiceError):
                return pricing_lookup

            priced_claims.extend([
                {
                    **result,
                    "pricing": pricing_lookup.get(result.get("claimid")),
                }
                for result in business_validation_results
            ])

        return {
            "priced_claims": priced_claims,
            "validation_errors": schema_validation_errors,
        }

class ClaimPricingService:
    def __init__(self, registry):
        self.registry = registry

    def price_claims(self, claim_type, claims):

        config = self.registry[claim_type]
        PricingLogic = config["pricing_logic"]

        pricer = PricingLogic()
        pricing_results = pricer.price(claims, claim_type=claim_type)

        if isinstance(pricing_results, PricingServiceError):
            return pricing_results

        pricing_lookup = {}
        for item in pricing_results:
            if hasattr(item, "claimid"):
                claim_id = item.claimid
            elif isinstance(item, dict):
                claim_id = item.get("claimid")
            else:
                claim_id = None

            if claim_id is None:
                continue

            if hasattr(item, "model_dump"):
                pricing_lookup[claim_id] = item.model_dump(mode="json")
            else:
                pricing_lookup[claim_id] = item

        return pricing_lookup
