"""
Vehicle search — REST wrapper around the same lookup the Insight Agent's
find_vehicle tool uses (app.agent.tools._find_vehicle), so VIN Search in
the UI and the agent's own vehicle resolution never disagree about what
counts as a match. Unlike the agent tool, this respects fleet scoping
(a fleet_owner should never see another fleet's VINs in the search bar).
"""
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.core import Vehicle
from app.core.auth import get_fleet_scope

router = APIRouter(prefix="/vehicles", tags=["vehicles"])


@router.get("/search")
def search_vehicles(
    q: str = Query(..., min_length=2, description="full or partial VIN"),
    limit: int = Query(default=8, le=25),
    db: Session = Depends(get_db),
    scope: Optional[int] = Depends(get_fleet_scope),
):
    query = q.strip().upper()
    filtered = db.query(Vehicle).filter(Vehicle.vin.like(f"%{query}%"))
    if scope is not None:
        filtered = filtered.filter(Vehicle.fleet_owner_id == scope)
    matches = filtered.order_by(Vehicle.vin).limit(limit).all()
    return {
        "query": q,
        "matches": [
            {
                "vin": v.vin,
                "model": v.model,
                "region": v.region,
                "total_km_driven": v.total_km_driven,
            }
            for v in matches
        ],
    }
