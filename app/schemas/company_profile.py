from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class CompanyProfilePayload(BaseModel):
    company_name: Optional[str] = None
    industry: Optional[str] = None
    employees_range: Optional[str] = None
    annual_sales_range: Optional[str] = None
    location_prefecture: Optional[str] = None
    years_in_business: Optional[int] = None


class CompanyProfileResponse(CompanyProfilePayload):
    user_id: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
