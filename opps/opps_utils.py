from .opps_model import OppsClaim

def transform_oppsClaimData_to_oppsServiceRequest(data):

    oppsServiceRequest = OppsClaim(**data.model_dump(mode='json'))

    return oppsServiceRequest.model_dump(mode='json')

def _extract_opps_provider_data (data):
    # extract provider data submitted by user
    return data 

def _build_opps_provider_data_attr (data):
    # build provider data attributes needed for service request
    return data
