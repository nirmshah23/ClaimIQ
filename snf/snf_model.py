from datetime import datetime

from pydantic import Field, field_validator, model_validator

from input.base_claim import BaseClaim, LineItem


class SNFLineItem(LineItem):
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


class SNFClaim(BaseClaim):
    from_date: datetime
    thru_date: datetime
    lines: list[SNFLineItem] = Field(min_length=1)
    pdpmPriorDays: int

    @model_validator(mode="after")
    def populate_line_service_dates(self):
        for line in self.lines:
            if line.service_date is None:
                line.service_date = self.from_date
        return self

    @model_validator(mode="after")
    def validate_required_revenue_code(self):
        if not any(line.revenue_code == "0022" for line in self.lines):
            raise ValueError(
                "SNFClaim must include at least one line with revenue_code 0022"
            )
        return self
