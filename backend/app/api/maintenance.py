"""
Maintenance Calendar aggregate. Deliberately NOT a new computation —
it reads rul_days that Day 5's RUL Estimator already persisted onto
Prediction rows (via POST /rul/run), across every part, and buckets
them by how soon service is due. A vehicle/part combo that hasn't had
RUL computed yet (rul_days IS NULL) is simply absent rather than
guessed at, so this stays consistent with the rest of the app: the
calendar is a different LENS on the same live numbers RUL Explorer and
Failure Probability already show, not a second source of truth.
"""
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.core import Part, Vehicle
from app.models.rules import Prediction
from app.services.scoring import SIM_AS_OF_DATE
from app.core.auth import get_fleet_scope

router = APIRouter(prefix="/maintenance", tags=["maintenance"])


@router.get("/calendar")
def get_maintenance_calendar(
    db: Session = Depends(get_db),
    scope: Optional[int] = Depends(get_fleet_scope),
):
    query = (
        db.query(Prediction, Part, Vehicle)
        .join(Part, Prediction.part_code == Part.part_code)
        .join(Vehicle, Prediction.vin == Vehicle.vin)
        .filter(
            Prediction.computed_date == SIM_AS_OF_DATE,
            Prediction.rul_days.isnot(None),
        )
    )
    if scope is not None:
        query = query.filter(Vehicle.fleet_owner_id == scope)

    rows = query.order_by(Prediction.rul_days.asc()).all()

    return {
        "computed_date": str(SIM_AS_OF_DATE),
        "n_scheduled": len(rows),
        "items": [
            {
                "vin": pred.vin,
                "model": vehicle.model,
                "part_code": part.part_code,
                "part_name": part.part_name,
                "rul_days": pred.rul_days,
                "rul_km": pred.rul_km,
                "risk_tier": pred.risk_tier,
                "failure_probability": pred.failure_probability,
            }
            for pred, part, vehicle in rows
        ],
    }
