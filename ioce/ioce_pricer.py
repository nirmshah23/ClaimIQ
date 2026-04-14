from .ioce_utils import _extract_ioce_provider_data, _build_ioce_provider_data_attr, transform_ioceClaimData_to_ioceServiceRequest
from claim.base_pricer import BasePricer

class IOCEPricer(BasePricer):

    def extract_provider_data(self, claim):
        return _extract_ioce_provider_data(claim)
    
    def build_provider_data_attr(self, provider_data):
        return _build_ioce_provider_data_attr (provider_data)

    def transform_input_to_service_request (self, claim, attr):
        
        request = transform_ioceClaimData_to_ioceServiceRequest(claim)
        
        return request
    
