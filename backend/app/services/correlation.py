"""
Correlation engine (Day 3) — for a given part, computes how strongly each
telematics signal relates to that part's failure, using two methods so
they can be compared side by side (per the brief: "you choose and
justify the method" — comparing two is the justification):

  1. Point-biserial correlation — a marginal (signal-by-signal) statistic:
     each signal's relationship with failure is computed independently of
     every other signal. This matters for the Rule Builder UX specifically:
     the user includes/excludes signals one at a time, so each signal's
     weight needs to stay meaningful regardless of what else is toggled.
     A multivariate coefficient (see note below) does NOT have that property.
  2. XGBoost feature importance (gain-based) — a non-linear view that can
     pick up interactions/thresholds a linear statistic would miss.

  NOTE ON A REJECTED THIRD METHOD: logistic regression coefficients were
  tried first and dropped. coolant_temp_variance, battery_voltage_sag, and
  dtc_recurrence_rate are 85-98% correlated with each other (all driven by
  the same latent alternator-degradation variable in the synthetic data),
  so an unregularized multivariate model can't tell them apart and assigns
  large, unstable coefficients to whichever one it latches onto — even for
  parts with zero true relationship to those signals (verified: raw
  point-biserial r≈0.00 for coolant_temp_variance vs. brake-pad failure,
  while logistic regression gave it the single largest coefficient). This
  is a textbook multicollinearity artifact, not a real finding, so it was
  replaced with point-biserial correlation above.

Where the two retained methods agree on which signals matter most, that's
the strongest evidence of a real relationship. Where they disagree, that's
worth calling out in the design note rather than papering over.
"""
from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy.stats import pointbiserialr
from xgboost import XGBClassifier

from app.services.features import TELEMATICS_SIGNALS, build_part_dataset


@dataclass
class SignalCorrelation:
    signal: str
    point_biserial_r: float      # marginal correlation, signed, -1..1
    xgboost_importance: float    # gain-based importance, 0-1, unsigned


class InsufficientDataError(Exception):
    """Raised when a part doesn't have enough failure/non-failure examples
    to fit a model (e.g. brand new part with 0 failures)."""
    pass


def compute_correlations(db, part_code: str) -> tuple[list[SignalCorrelation], dict]:
    df = build_part_dataset(db, part_code)

    n_pos = int(df["label"].sum()) if not df.empty else 0
    n_neg = int((df["label"] == 0).sum()) if not df.empty else 0
    meta = {"n_vehicles": len(df), "n_failed": n_pos, "n_not_failed": n_neg}

    if n_pos < 5 or n_neg < 5:
        raise InsufficientDataError(
            f"Part {part_code} has only {n_pos} failed / {n_neg} non-failed "
            f"vehicles — need at least 5 of each to fit a reliable model."
        )

    X = df[TELEMATICS_SIGNALS].values
    y = df["label"].values

    # --- Method 1: point-biserial correlation (marginal, per signal) ---
    pb_weights = {}
    for i, signal in enumerate(TELEMATICS_SIGNALS):
        r, _p = pointbiserialr(y, X[:, i])
        pb_weights[signal] = 0.0 if np.isnan(r) else r

    # --- Method 2: XGBoost gain-based feature importance ---
    # Conservative hyperparameters given modest sample size (as few as ~30-80
    # positive examples per part) — a deep/large ensemble overfits noise in
    # the correlated signals and produces misleadingly high importances for
    # irrelevant features, the same failure mode as the dropped logistic model.
    n_pos_count = int(y.sum())
    n_neg_count = int(len(y) - n_pos_count)
    xgb = XGBClassifier(
        n_estimators=40, max_depth=2, learning_rate=0.1,
        reg_lambda=5.0, subsample=0.8, colsample_bytree=0.8,
        scale_pos_weight=n_neg_count / max(n_pos_count, 1),
        eval_metric="logloss", random_state=42,
    )
    xgb.fit(X, y)
    xgb_weights = dict(zip(TELEMATICS_SIGNALS, xgb.feature_importances_))

    results = [
        SignalCorrelation(
            signal=s,
            point_biserial_r=round(float(pb_weights[s]), 4),
            xgboost_importance=round(float(xgb_weights[s]), 4),
        )
        for s in TELEMATICS_SIGNALS
    ]
    # sort by absolute point-biserial r, strongest first (default view)
    results.sort(key=lambda r: abs(r.point_biserial_r), reverse=True)
    return results, meta
