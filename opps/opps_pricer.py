from .opps_utils import _extract_opps_provider_data, _build_opps_provider_data_attr, transform_oppsClaimData_to_oppsServiceRequest
from claim.base_pricer import BasePricer

class OPPSPricer(BasePricer):

    def extract_provider_data(self, claim):
        return _extract_opps_provider_data(claim)
    
    def build_provider_data_attr(self, provider_data):
        return _build_opps_provider_data_attr (provider_data)

    def transform_input_to_service_request (self, claim, attr):
        
        request = transform_oppsClaimData_to_oppsServiceRequest(claim)
        
        return request
    
