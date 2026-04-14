from .ipps_model import IppsClaim

def transform_ippsClaimData_to_ippsServiceRequest(data):

    ippsServiceRequest = IppsClaim(**data.model_dump(mode='json'))

    return ippsServiceRequest.model_dump(mode='json')

def _extract_ipps_provider_data (data):
    # extract provider data submitted by user
    return data

def _build_ipps_provider_data_attr (data):
    # build provider data attributes needed for service request
    return data
