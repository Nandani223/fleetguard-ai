from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.core import Part
from app.schemas.rule import (
    CorrelationResponse, SignalCorrelationOut,
    RuleBuildRequest, RuleResponse,
)
from app.services.correlation import compute_correlations, InsufficientDataError
from app.services.rule_builder import build_and_persist_rule, get_persisted_rule

router = APIRouter(prefix="/parts", tags=["parts"])


@router.get("")
def list_parts(db: Session = Depends(get_db)):
    parts = db.query(Part).all()
    return [
        {
            "part_code": p.part_code, "part_name": p.part_name,
            "category": p.category, "design_life_km": p.design_life_km,
        }
        for p in parts
    ]


@router.get("/{part_code}/correlation", response_model=CorrelationResponse)
def get_correlation(part_code: str, db: Session = Depends(get_db)):
    part = db.query(Part).filter(Part.part_code == part_code).first()
    if part is None:
        raise HTTPException(status_code=404, detail=f"Unknown part_code: {part_code}")

    try:
        results, meta = compute_correlations(db, part_code)
    except InsufficientDataError as e:
        raise HTTPException(status_code=422, detail=str(e))

    return CorrelationResponse(
        part_code=part_code,
        part_name=part.part_name,
        n_vehicles=meta["n_vehicles"],
        n_failed=meta["n_failed"],
        n_not_failed=meta["n_not_failed"],
        signals=[
            SignalCorrelationOut(
                signal=r.signal,
                point_biserial_r=r.point_biserial_r,
                xgboost_importance=r.xgboost_importance,
            )
            for r in results
        ],
    )


@router.post("/{part_code}/rule", response_model=RuleResponse)
def build_rule(part_code: str, request: RuleBuildRequest, db: Session = Depends(get_db)):
    try:
        signals = build_and_persist_rule(db, part_code, request)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except InsufficientDataError as e:
        raise HTTPException(status_code=422, detail=str(e))

    return RuleResponse(part_code=part_code, method=request.method, signals=signals)


@router.get("/{part_code}/rule", response_model=RuleResponse)
def get_rule(
    part_code: str,
    method: str = Query(default="point_biserial", pattern="^(point_biserial|xgboost_importance)$"),
    db: Session = Depends(get_db),
):
    part = db.query(Part).filter(Part.part_code == part_code).first()
    if part is None:
        raise HTTPException(status_code=404, detail=f"Unknown part_code: {part_code}")

    signals = get_persisted_rule(db, part_code, method)
    if not signals:
        raise HTTPException(
            status_code=404,
            detail=f"No rule persisted yet for {part_code} with method={method}. "
                   f"POST /parts/{part_code}/rule first.",
        )
    return RuleResponse(part_code=part_code, method=method, signals=signals)
