from datetime import datetime

from pydantic import Field, field_validator

from input.base_claim import BaseClaim, LineItem, ValueCode


class HospiceLineItem(LineItem):
    service_date: datetime
    hcpcs: str
    units: float

    @field_validator("hcpcs")
    @classmethod
    def validate_hcpcs(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("hcpcs is required")
        if not value.isalnum():
            raise ValueError("hcpcs must be alphanumeric")
        if len(value) > 5:
            raise ValueError("hcpcs must be at most 5 characters")
        return value

    @field_validator("units")
    @classmethod
    def validate_units(cls, value: float) -> float:
        if value <= 0:
            raise ValueError("units must be greater than 0")
        return value


class HospiceClaim(BaseClaim):
    from_date: datetime
    los: int
    lines: list[HospiceLineItem] = Field(min_length=1)
    value_codes: list[ValueCode] = Field(min_length=1)
