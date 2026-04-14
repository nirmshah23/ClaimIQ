from opps.opps_model import OppsClaim

def transform_ioceClaimData_to_ioceServiceRequest(data):
    
    ioceServiceRequest = OppsClaim(**data.model_dump(mode='json'))
    
    return ioceServiceRequest.model_dump(mode='json')

def _extract_ioce_provider_data (data):
    # extract provider data submitted by user
    return data

def _build_ioce_provider_data_attr (data):
    # build provider data attributes needed for service request
    return data
