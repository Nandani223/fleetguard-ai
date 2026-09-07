"""
Feature engineering — builds a per-vehicle feature/label dataset for a
given part. Shared by the correlation engine (Day 3), the scoring engine
(Day 4), and the RUL estimator (Day 5) so all three read signals the same
way and never disagree about what "the data" says for a given VIN.

For each vehicle:
  - label = 1 if that vehicle had a failure of this part in the window, else 0
  - features = average of each telematics signal over the vehicle's most
    recent 8 weeks of the observation window — for EVERY vehicle, regardless
    of whether/when they failed.

    This was not the first design tried. An earlier version used "the 8
    weeks immediately before failure_date" for failed vehicles, on the
    theory that signals right before a failure are most informative. That
    turned out to be wrong for this dataset: failure timing is sampled
    independently of how far a vehicle's degradation had actually
    progressed (see generate_data.py), so a high-risk vehicle could be
    randomly assigned an early failure week, before its signals had ramped
    up — which diluted the measured correlation for no real reason
    (verified: point-biserial r for coolant_temp_variance vs. alternator
    failure dropped from ~0.50 to ~0.28 under the failure-conditional
    window). Using the end of the observation window for every vehicle
    also matches how the model is actually applied at inference time
    (score current telematics -> predict risk), so training and scoring
    are aligned rather than using different temporal logic.
"""
from datetime import date, timedelta

import pandas as pd
from sqlalchemy.orm import Session

from app.models.core import Vehicle
from app.models.failure import Failure
from app.models.telematics import TelematicsWeekly

TELEMATICS_SIGNALS = [
    "coolant_temp_variance",
    "oil_pressure_dips",
    "battery_voltage_sag",
    "dtc_recurrence_rate",
    "harsh_braking_frequency",
    "overload_duty_share",
    "high_rpm_dwell_time",
    "short_trip_ratio",
    "idle_time_pct",
]

LOOKBACK_WEEKS = 8


def build_part_dataset(db: Session, part_code: str) -> pd.DataFrame:
    """
    Returns a DataFrame: one row per vehicle, columns = TELEMATICS_SIGNALS + ['vin','label'].
    Features are always the vehicle's most recent LOOKBACK_WEEKS of telematics
    (see module docstring for why failure-date-conditional windows were dropped).
    """
    failed_vins = {
        vin for (vin,) in
        db.query(Failure.vin).filter(Failure.part_code == part_code).all()
    }
    vins = [v[0] for v in db.query(Vehicle.vin).all()]

    records = []
    for vin in vins:
        rows = (
            db.query(TelematicsWeekly)
            .filter(TelematicsWeekly.vin == vin)
            .order_by(TelematicsWeekly.week_start_date.desc())
            .limit(LOOKBACK_WEEKS)
            .all()
        )
        if not rows:
            continue

        record = {"vin": vin, "label": 1 if vin in failed_vins else 0}
        for signal in TELEMATICS_SIGNALS:
            values = [getattr(r, signal) for r in rows]
            record[signal] = sum(values) / len(values)
        records.append(record)

    return pd.DataFrame.from_records(records)
