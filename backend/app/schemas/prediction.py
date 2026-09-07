from datetime import date
from typing import Optional

from pydantic import BaseModel


class RunPredictionsRequest(BaseModel):
    part_code: str
    method: str = "point_biserial"
    as_of_date: Optional[date] = None  # defaults to today if omitted


class RunPredictionsResponse(BaseModel):
    part_code: str
    method: str
    computed_date: str
    n_scored: int
    tier_counts: dict


class PredictionOut(BaseModel):
    vin: str
    part_code: str
    failure_probability: float
    risk_tier: str
    estimated_window_days: Optional[int]
    top_signals: str
    computed_date: date

    class Config:
        from_attributes = True


class SignalContribution(BaseModel):
    signal: str
    contribution: float


class PredictionDetailOut(PredictionOut):
    trend: list[float]  # week-by-week probability, oldest -> newest
    top_signal_contributions: list[SignalContribution] = []
