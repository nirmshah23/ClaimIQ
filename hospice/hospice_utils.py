from .hospice_model import HospiceClaim

def transform_hospiceClaimData_to_hospiceServiceRequest(data):
    hospiceServiceRequest = HospiceClaim(**data.model_dump(mode='json'))
   
    return hospiceServiceRequest.model_dump(mode='json')

def _extract_hospice_provider_data (data):
    # extract provider data submitted by user
    return data

def _build_hospice_provider_data_attr (data):
    # extracted provider data will be used to build service reqeust
    return data