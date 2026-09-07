"""
Failure Probability Scoring Engine (Day 4 — brief section 4.3).

Applies a part's PERSISTED rule (from Day 3's Rule Builder) across the
whole fleet to produce, per VIN/part: failure probability %, risk tier
(Green/Amber/Red), top contributing signals, and a probability trend
over recent weeks.

Scoring method:
  1. z-score each included signal against the fleet population (mean/std
     computed from every vehicle's current 8-week-average feature vector
     — the same feature representation the correlation engine trained on,
     so scoring and correlation never disagree about what "the data" says).
  2. weighted sum of z-scores using the rule's persisted weights (signed
     for point_biserial, unsigned for xgboost_importance — see the
     limitation noted in rule_builder.py).
  3. squash through a scaled sigmoid to get a 0-1 probability.
  4. risk tier from fixed, documented thresholds.
  5. trend: repeat steps 1-3 using each of the last TREND_WEEKS individual
     weeks (not the 8-week average) so the trend line shows week-to-week
     movement, not a flat average repeated.
"""
from dataclasses import dataclass, field
from datetime import date

import numpy as np
from sqlalchemy.orm import Session

from app.models.core import Vehicle
from app.models.telematics import TelematicsWeekly
from app.models.rules import RuleConfig, Prediction
from app.services.features import TELEMATICS_SIGNALS, build_part_dataset

# Fixed "as of" date matching the end of our synthetic 12-month telematics
# window (SIM_START=2025-01-01 + 52 weeks). All scoring — predictions and
# RUL alike — is computed relative to the synthetic data's own timeline,
# not wall-clock "today", since the data itself doesn't extend past this
# date. Defined once here and imported everywhere else that needs it
# (app/api/predictions.py, app/services/rul.py) so they can't drift apart.
SIM_AS_OF_DATE = date(2025, 12, 29)

# --- Tunable constants (documented here, not scattered) ---
SCORE_SCALE = 3.5          # spreads weighted z-sum into a usable probability range
RISK_THRESHOLDS = {        # inclusive lower bound, exclusive upper bound
    "Green": (0.0, 0.30),
    "Amber": (0.30, 0.60),
    "Red": (0.60, 1.01),
}
TREND_WEEKS = 6
TREND_ROLL_WINDOW = 3  # each trend point is a rolling average over this many
                        # raw weeks, not a single noisy week — a single week's
                        # count-based signals (e.g. oil_pressure_dips) swing
                        # too much on their own to make a readable trend line
                        # (verified: raw single-week trend jumped 0.69→0.11→
                        # 0.94→0.24 week to week for a real Amber-tier vehicle,
                        # which is unusable for a demo or a human reading it)


def risk_tier_for(probability: float) -> str:
    for tier, (lo, hi) in RISK_THRESHOLDS.items():
        if lo <= probability < hi:
            return tier
    return "Red"  # probability == 1.0 edge case


@dataclass
class PopulationStats:
    mean: dict = field(default_factory=dict)
    std: dict = field(default_factory=dict)


def compute_population_stats(db: Session) -> PopulationStats:
    """Fleet-wide mean/std per telematics signal, from every vehicle's
    current 8-week-average feature vector. Signal ranges don't depend on
    which part we're scoring, so this is computed once and reused."""
    # build_part_dataset needs a part_code purely to compute the label column,
    # which we ignore here — features are identical regardless of part.
    from app.models.core import Part
    first_part = db.query(Part).first()
    df = build_part_dataset(db, first_part.part_code)

    stats = PopulationStats()
    for signal in TELEMATICS_SIGNALS:
        stats.mean[signal] = float(df[signal].mean())
        stats.std[signal] = float(df[signal].std()) or 1.0  # guard div-by-zero
    return stats


def _weighted_z_sum(values: dict, weights: dict, stats: PopulationStats) -> float:
    total = 0.0
    for signal, weight in weights.items():
        z = (values[signal] - stats.mean[signal]) / stats.std[signal]
        total += weight * z
    return total


def _probability_from_z_sum(z_sum: float, base_rate_intercept: float) -> float:
    return float(1.0 / (1.0 + np.exp(-(SCORE_SCALE * z_sum + base_rate_intercept))))


def _base_rate_intercept(db: Session, part_code: str) -> float:
    """
    Logit of the part's true historical failure rate, used as a bias term
    so a 'typical' (average, z=0) vehicle scores near the part's real base
    rate instead of a flat 50%. Without this, a symmetric sigmoid centered
    at zero over-assigns Red tier across the board — verified: before this
    fix, AUC was already good (0.79-0.86 for alternator/turbo, confirming
    the ranking was sound) but 40-48% of the whole fleet landed in Red
    despite true failure rates of 7-20%. This is a calibration problem, not
    a discrimination problem, and this intercept is the standard fix for it
    (equivalent to what a properly-fit logistic regression's intercept term
    would supply automatically).
    """
    from app.models.failure import Failure
    n_failed = db.query(Failure).filter(Failure.part_code == part_code).count()
    n_total = db.query(Vehicle).count()
    base_rate = max(min(n_failed / n_total, 0.99), 0.01) if n_total else 0.10
    return float(np.log(base_rate / (1 - base_rate)))


def _rolling_trend(weekly_rows: list, weights: dict, stats: PopulationStats, intercept: float) -> list[float]:
    """weekly_rows must be ordered oldest -> newest and have at least
    TREND_WEEKS + TREND_ROLL_WINDOW - 1 entries. Returns TREND_WEEKS
    probabilities, each a rolling TREND_ROLL_WINDOW-week average."""
    trend = []
    n = len(weekly_rows)
    for i in range(n - TREND_WEEKS, n):
        window = weekly_rows[max(0, i - TREND_ROLL_WINDOW + 1): i + 1]
        window_values = {
            signal: sum(getattr(r, signal) for r in window) / len(window)
            for signal in TELEMATICS_SIGNALS
        }
        wz = _weighted_z_sum(window_values, weights, stats)
        trend.append(round(_probability_from_z_sum(wz, intercept), 4))
    return trend


def score_fleet_for_part(db: Session, part_code: str, method: str, as_of_date: date) -> list[Prediction]:
    all_rule_rows = (
        db.query(RuleConfig)
        .filter(RuleConfig.part_code == part_code, RuleConfig.method == method)
        .all()
    )
    if not all_rule_rows:
        raise ValueError(
            f"No rule persisted yet for {part_code} (method={method}). "
            f"POST /parts/{part_code}/rule first."
        )

    included_rows = [r for r in all_rule_rows if r.included]
    weights = {r.signal: r.correlation_weight for r in included_rows}

    vehicles = db.query(Vehicle.vin).all()

    if not weights:
        # Graceful degradation: some parts (e.g. brake pads in our data)
        # genuinely have no telematics signal strong enough to be useful —
        # wear is driven by mileage/region, which aren't telematics fields.
        # Rather than hard-failing the whole fleet scoring run, fall back to
        # the part's overall historical failure rate as a flat baseline
        # probability, tier Green (not confident enough to escalate), and
        # flag it clearly so the frontend/agent don't present this as a
        # real per-vehicle signal.
        from app.models.failure import Failure
        n_failed = db.query(Failure).filter(Failure.part_code == part_code).count()
        n_total = len(vehicles)
        base_rate = round(n_failed / n_total, 4) if n_total else 0.0

        return [
            Prediction(
                vin=vin, part_code=part_code,
                failure_probability=base_rate,
                risk_tier="Green",
                estimated_window_days=None,
                rul_km=None, rul_days=None,
                top_signals="insufficient_signal",
                computed_date=as_of_date,
            )
            for (vin,) in vehicles
        ]

    stats = compute_population_stats(db)
    intercept = _base_rate_intercept(db, part_code)

    predictions = []
    for (vin,) in vehicles:
        rows = (
            db.query(TelematicsWeekly)
            .filter(TelematicsWeekly.vin == vin)
            .order_by(TelematicsWeekly.week_start_date.desc())
            .limit(8)
            .all()
        )
        if not rows:
            continue

        current_values = {
            signal: sum(getattr(r, signal) for r in rows) / len(rows)
            for signal in TELEMATICS_SIGNALS
        }
        z_sum = _weighted_z_sum(current_values, weights, stats)
        probability = _probability_from_z_sum(z_sum, intercept)
        tier = risk_tier_for(probability)

        contributions = {
            signal: weight * ((current_values[signal] - stats.mean[signal]) / stats.std[signal])
            for signal, weight in weights.items()
        }
        top_signals = sorted(contributions, key=lambda s: abs(contributions[s]), reverse=True)[:3]

        trend_rows = (
            db.query(TelematicsWeekly)
            .filter(TelematicsWeekly.vin == vin)
            .order_by(TelematicsWeekly.week_start_date.desc())
            .limit(TREND_WEEKS + TREND_ROLL_WINDOW - 1)
            .all()
        )
        trend_rows = list(reversed(trend_rows))  # oldest -> newest
        trend_probs = _rolling_trend(trend_rows, weights, stats, intercept)

        # lightweight estimated window: weeks of trend-slope until crossing
        # into Red (0.60), floor at 0 (already Red / already crossed).
        # This is a rough heuristic pending Day 5's proper RUL cross-check.
        estimated_window_days = None
        if len(trend_probs) >= 2:
            slope_per_week = (trend_probs[-1] - trend_probs[0]) / (len(trend_probs) - 1)
            if slope_per_week > 0.001 and trend_probs[-1] < 0.60:
                weeks_to_red = (0.60 - trend_probs[-1]) / slope_per_week
                estimated_window_days = max(0, int(weeks_to_red * 7))
            elif trend_probs[-1] >= 0.60:
                estimated_window_days = 0

        predictions.append(Prediction(
            vin=vin, part_code=part_code,
            failure_probability=round(probability, 4),
            risk_tier=tier,
            estimated_window_days=estimated_window_days,
            rul_km=None, rul_days=None,  # filled in Day 5
            top_signals=",".join(top_signals),
            computed_date=as_of_date,
        ))

    return predictions


def score_single_vehicle(db: Session, vin: str, part_code: str, method: str) -> dict:
    """Live detail view for one VIN/part — same scoring logic as the fleet
    run, but computed on demand (not persisted) so the trend array doesn't
    need its own DB column. Used by the drill-down endpoint and, later,
    the Insight Agent's tool calls."""
    all_rule_rows = (
        db.query(RuleConfig)
        .filter(RuleConfig.part_code == part_code, RuleConfig.method == method)
        .all()
    )
    if not all_rule_rows:
        raise ValueError(
            f"No rule persisted yet for {part_code} (method={method}). "
            f"POST /parts/{part_code}/rule first."
        )
    weights = {r.signal: r.correlation_weight for r in all_rule_rows if r.included}

    rows = (
        db.query(TelematicsWeekly)
        .filter(TelematicsWeekly.vin == vin)
        .order_by(TelematicsWeekly.week_start_date.desc())
        .limit(8)
        .all()
    )
    if not rows:
        raise ValueError(f"No telematics data found for VIN {vin}.")

    if not weights:
        from app.models.failure import Failure
        n_failed = db.query(Failure).filter(Failure.part_code == part_code).count()
        n_total = db.query(Vehicle).count()
        base_rate = round(n_failed / n_total, 4) if n_total else 0.0
        return {
            "vin": vin, "part_code": part_code, "failure_probability": base_rate,
            "risk_tier": "Green", "top_signals": ["insufficient_signal"],
            "trend": [base_rate] * TREND_WEEKS,
        }

    stats = compute_population_stats(db)
    intercept = _base_rate_intercept(db, part_code)

    current_values = {
        signal: sum(getattr(r, signal) for r in rows) / len(rows)
        for signal in TELEMATICS_SIGNALS
    }
    z_sum = _weighted_z_sum(current_values, weights, stats)
    probability = _probability_from_z_sum(z_sum, intercept)
    tier = risk_tier_for(probability)

    contributions = {
        signal: weight * ((current_values[signal] - stats.mean[signal]) / stats.std[signal])
        for signal, weight in weights.items()
    }
    top_signals = sorted(contributions, key=lambda s: abs(contributions[s]), reverse=True)[:3]

    trend_rows = list(reversed(
        db.query(TelematicsWeekly)
        .filter(TelematicsWeekly.vin == vin)
        .order_by(TelematicsWeekly.week_start_date.desc())
        .limit(TREND_WEEKS + TREND_ROLL_WINDOW - 1)
        .all()
    ))
    trend = _rolling_trend(trend_rows, weights, stats, intercept)

    return {
        "vin": vin, "part_code": part_code, "failure_probability": round(probability, 4),
        "risk_tier": tier, "top_signals": top_signals, "trend": trend,
        "top_signal_contributions": [
            {"signal": s, "contribution": round(contributions[s], 4)} for s in top_signals
        ],
    }


def run_and_persist(db: Session, part_code: str, method: str, as_of_date: date) -> dict:
    predictions = score_fleet_for_part(db, part_code, method, as_of_date)

    db.query(Prediction).filter(
        Prediction.part_code == part_code, Prediction.computed_date == as_of_date
    ).delete()
    db.bulk_save_objects(predictions)
    db.commit()

    tier_counts = {"Green": 0, "Amber": 0, "Red": 0}
    for p in predictions:
        tier_counts[p.risk_tier] += 1

    return {
        "part_code": part_code, "method": method, "computed_date": str(as_of_date),
        "n_scored": len(predictions), "tier_counts": tier_counts,
    }
