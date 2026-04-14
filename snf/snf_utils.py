from .snf_model import SNFClaim

def transform_snfClaimData_to_snfServiceRequest(data):
   
    snfServiceRequest = SNFClaim(**data.model_dump(mode='json'))
   
    return snfServiceRequest.model_dump(mode='json')
    
def _extract_snf_provider_data (data):
    # extract provider data submitted by user
    return data

def _build_snf_provider_data_attr (data):
    # extracted provider data will be used to build service reqeust
    return data
