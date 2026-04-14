from claim.base_pricer import BasePricer
from .ipps_utils import _extract_ipps_provider_data, _build_ipps_provider_data_attr, transform_ippsClaimData_to_ippsServiceRequest

class IPPSPricer(BasePricer):

    def extract_provider_data(self, claim):
        return _extract_ipps_provider_data(claim)
    
    def build_provider_data_attr(self, provider_data):
        return _build_ipps_provider_data_attr (provider_data)
    
    def transform_input_to_service_request (self, claim, attr):
        
        request = transform_ippsClaimData_to_ippsServiceRequest(claim)
        
        return request
    
