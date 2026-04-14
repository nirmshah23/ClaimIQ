from .snf_utils import transform_snfClaimData_to_snfServiceRequest, _extract_snf_provider_data, _build_snf_provider_data_attr
from claim.base_pricer import BasePricer


class SNFPricer(BasePricer):

    def extract_provider_data(self, claim):
        return _extract_snf_provider_data (claim)
    
    def build_provider_data_attr(self, provider_data):
        return _build_snf_provider_data_attr (provider_data)

    def transform_input_to_service_request(self, claim, attr):

        request = transform_snfClaimData_to_snfServiceRequest(claim)

        return request
    
