from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.core import Part, Vehicle
from app.models.rules import Prediction
from app.schemas.prediction import (
    RunPredictionsRequest, RunPredictionsResponse,
    PredictionOut, PredictionDetailOut,
)
from app.services.scoring import run_and_persist, score_single_vehicle, SIM_AS_OF_DATE
from app.core.auth import require_admin, get_current_user, get_fleet_scope

router = APIRouter(prefix="/predictions", tags=["predictions"])


@router.post("/run", response_model=RunPredictionsResponse)
def run_predictions(request: RunPredictionsRequest, db: Session = Depends(get_db),
                     _admin=Depends(require_admin)):
    part = db.query(Part).filter(Part.part_code == request.part_code).first()
    if part is None:
        raise HTTPException(status_code=404, detail=f"Unknown part_code: {request.part_code}")

    as_of = request.as_of_date or SIM_AS_OF_DATE
    try:
        result = run_and_persist(db, request.part_code, request.method, as_of)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    return RunPredictionsResponse(**result)


@router.get("", response_model=list[PredictionOut])
def list_predictions(
    part_code: Optional[str] = Query(default=None),
    risk_tier: Optional[str] = Query(default=None, pattern="^(Green|Amber|Red)$"),
    computed_date: Optional[date] = Query(default=None),
    limit: int = Query(default=100, le=500),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    scope: Optional[int] = Depends(get_fleet_scope),
):
    query = db.query(Prediction)
    if scope is not None:
        # fleet_owner: only vehicles they own — the actual data-isolation fix.
        # admin (scope is None): no filter, sees everything, as before.
        owned_vins = db.query(Vehicle.vin).filter(Vehicle.fleet_owner_id == scope)
        query = query.filter(Prediction.vin.in_(owned_vins))
    if part_code:
        query = query.filter(Prediction.part_code == part_code)
    if risk_tier:
        query = query.filter(Prediction.risk_tier == risk_tier)
    query = query.filter(Prediction.computed_date == (computed_date or SIM_AS_OF_DATE))

    # Red first, then Amber, then Green; highest probability first within a tier
    tier_order = {"Red": 0, "Amber": 1, "Green": 2}
    rows = query.all()
    rows.sort(key=lambda p: (tier_order.get(p.risk_tier, 3), -p.failure_probability))
    return rows[offset: offset + limit]


@router.get("/{vin}/{part_code}", response_model=PredictionDetailOut)
def get_prediction_detail(
    vin: str, part_code: str,
    method: str = Query(default="point_biserial", pattern="^(point_biserial|xgboost_importance)$"),
    db: Session = Depends(get_db),
    scope: Optional[int] = Depends(get_fleet_scope),
):
    vehicle = db.query(Vehicle).filter(Vehicle.vin == vin).first()
    if vehicle is None:
        raise HTTPException(status_code=404, detail=f"Unknown VIN: {vin}")
    if scope is not None and vehicle.fleet_owner_id != scope:
        raise HTTPException(status_code=403, detail="This vehicle does not belong to your fleet.")
    part = db.query(Part).filter(Part.part_code == part_code).first()
    if part is None:
        raise HTTPException(status_code=404, detail=f"Unknown part_code: {part_code}")

    try:
        detail = score_single_vehicle(db, vin, part_code, method)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    persisted = (
        db.query(Prediction)
        .filter(Prediction.vin == vin, Prediction.part_code == part_code)
        .order_by(Prediction.computed_date.desc())
        .first()
    )

    return PredictionDetailOut(
        vin=vin, part_code=part_code,
        failure_probability=detail["failure_probability"],
        risk_tier=detail["risk_tier"],
        estimated_window_days=persisted.estimated_window_days if persisted else None,
        top_signals=",".join(detail["top_signals"]) if isinstance(detail["top_signals"], list) else detail["top_signals"],
        computed_date=persisted.computed_date if persisted else SIM_AS_OF_DATE,
        trend=detail["trend"],
        top_signal_contributions=detail.get("top_signal_contributions", []),
    )
