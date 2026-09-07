from datetime import date
from typing import Optional

from pydantic import BaseModel, Field


class SignalCorrelationOut(BaseModel):
    signal: str
    point_biserial_r: float
    xgboost_importance: float


class CorrelationResponse(BaseModel):
    part_code: str
    part_name: str
    n_vehicles: int
    n_failed: int
    n_not_failed: int
    signals: list[SignalCorrelationOut]


class RuleSignalIn(BaseModel):
    signal: str
    included: bool = True


class RuleBuildRequest(BaseModel):
    method: str = Field(default="point_biserial", pattern="^(point_biserial|xgboost_importance)$")
    signals: list[RuleSignalIn]


class RuleSignalOut(BaseModel):
    signal: str
    weight: float          # normalized, sums to 1 across included signals
    raw_score: float        # the underlying point_biserial_r or xgboost_importance
    included: bool
    method: str


class RuleResponse(BaseModel):
    part_code: str
    method: str
    signals: list[RuleSignalOut]
