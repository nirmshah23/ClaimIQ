from input.base_claim import BaseClaim, DiagnosisCode, Patient
from typing import Literal

class IppsPatient(Patient):
    age: int
    sex: Literal['Male', 'Female']

class IppsClaim(BaseClaim):
    patient_status: str = "01"
    principal_dx: DiagnosisCode
    los: int
