"""
Rule Builder (Day 3) — takes a chosen correlation method + an include/exclude
selection over signals, computes normalized weights, and persists them as
the part's active scoring rule (Day 4's scoring engine reads this back).

Weight convention (read by the scoring engine in Day 4):
  - method="point_biserial": raw_score is the signed correlation (-1..1).
    weight = raw_score / sum(|raw_score| for included signals) — sign is
    preserved, so a signal that's *negatively* correlated with failure
    (higher value -> lower risk) still pulls the score down, not up.
  - method="xgboost_importance": raw_score is unsigned gain importance
    (0..1). weight = raw_score / sum(included importances) — all positive,
    since gain importance alone doesn't carry direction. The scoring engine
    treats "higher signal value" as "higher risk" under this method, which
    is a simplification worth noting in the design note.
"""
from sqlalchemy.orm import Session

from app.models.core import Part
from app.models.rules import RuleConfig
from app.schemas.rule import RuleBuildRequest, RuleSignalOut
from app.services.correlation import compute_correlations


def build_and_persist_rule(db: Session, part_code: str, request: RuleBuildRequest) -> list[RuleSignalOut]:
    part = db.query(Part).filter(Part.part_code == part_code).first()
    if part is None:
        raise ValueError(f"Unknown part_code: {part_code}")

    correlations, _meta = compute_correlations(db, part_code)
    score_by_signal = {
        c.signal: (c.point_biserial_r if request.method == "point_biserial" else c.xgboost_importance)
        for c in correlations
    }

    included_signals = {s.signal for s in request.signals if s.included}
    unknown = included_signals - set(score_by_signal.keys())
    if unknown:
        raise ValueError(f"Unknown signal(s): {sorted(unknown)}")

    denom = sum(abs(score_by_signal[s]) for s in included_signals)

    # wipe existing rows for this part+method, then insert the fresh set
    db.query(RuleConfig).filter(
        RuleConfig.part_code == part_code, RuleConfig.method == request.method
    ).delete()

    outputs = []
    all_requested = {s.signal: s.included for s in request.signals}
    for signal, included in all_requested.items():
        raw = score_by_signal[signal]
        weight = (raw / denom) if (included and denom > 0) else 0.0
        db.add(RuleConfig(
            part_code=part_code, signal=signal, correlation_weight=weight,
            raw_score=raw, included=included, method=request.method,
        ))
        outputs.append(RuleSignalOut(
            signal=signal, weight=round(weight, 4), raw_score=round(raw, 4),
            included=included, method=request.method,
        ))
    db.commit()

    outputs.sort(key=lambda o: abs(o.weight), reverse=True)
    return outputs


def get_persisted_rule(db: Session, part_code: str, method: str) -> list[RuleSignalOut]:
    rows = (
        db.query(RuleConfig)
        .filter(RuleConfig.part_code == part_code, RuleConfig.method == method)
        .all()
    )
    outputs = [
        RuleSignalOut(
            signal=r.signal, weight=round(r.correlation_weight, 4),
            raw_score=round(r.raw_score, 4),
            included=r.included, method=r.method,
        )
        for r in rows
    ]
    outputs.sort(key=lambda o: abs(o.weight), reverse=True)
    return outputs
