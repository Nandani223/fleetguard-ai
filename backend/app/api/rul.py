from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.core import Vehicle, Part
from app.schemas.rul import RulDetailOut, RulRunRequest, RulRunResponse
from app.services.rul import estimate_rul, run_rul_for_part
from app.core.auth import require_admin, get_fleet_scope
from typing import Optional

router = APIRouter(tags=["rul"])


@router.get("/vins/{vin}/parts/{part_code}/rul", response_model=RulDetailOut)
def get_rul_detail(
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
    if db.query(Part).filter(Part.part_code == part_code).first() is None:
        raise HTTPException(status_code=404, detail=f"Unknown part_code: {part_code}")

    try:
        return estimate_rul(db, vin, part_code, method)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))


@router.post("/rul/run", response_model=RulRunResponse)
def run_rul(request: RulRunRequest, db: Session = Depends(get_db), _admin=Depends(require_admin)):
    if db.query(Part).filter(Part.part_code == request.part_code).first() is None:
        raise HTTPException(status_code=404, detail=f"Unknown part_code: {request.part_code}")

    result = run_rul_for_part(db, request.part_code, request.method, request.as_of_date)
    if result.get("error"):
        raise HTTPException(status_code=422, detail=result["error"])
    return RulRunResponse(**{k: v for k, v in result.items() if k != "error"})
