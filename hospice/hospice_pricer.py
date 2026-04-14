from .hospice_utils import transform_hospiceClaimData_to_hospiceServiceRequest, _extract_hospice_provider_data, _build_hospice_provider_data_attr
from claim.base_pricer import BasePricer

class HospicePricer(BasePricer):

    def extract_provider_data(self, claim):
        return _extract_hospice_provider_data (claim)
    
    def build_provider_data_attr(self, provider_data):
        return _build_hospice_provider_data_attr (provider_data)

    def transform_input_to_service_request(self, claim, attr):

        request = transform_hospiceClaimData_to_hospiceServiceRequest(claim)

        return request