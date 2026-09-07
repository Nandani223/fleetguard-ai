from datetime import date
from typing import Optional

from pydantic import BaseModel


class RulDetailOut(BaseModel):
    vin: str
    part_code: str
    failure_probability: float
    risk_tier: str
    baseline_remaining_km: int
    baseline_remaining_days: Optional[int]
    rul_km: int
    rul_days: Optional[int]
    consistent: bool
    consistency_note: str


class RulRunRequest(BaseModel):
    part_code: str
    method: str = "point_biserial"
    as_of_date: Optional[date] = None


class RulRunResponse(BaseModel):
    part_code: str
    method: str
    computed_date: str
    n_updated: int
    n_missing_predictions: int
    avg_rul_days: Optional[float]
