"""
FleetGuard AI — synthetic data generator (Day 2)

Populates: parts, vehicles, telematics_weekly, failures.
Does NOT touch rule_config / predictions — those are produced by the app
in Day 3/4, not seeded here.

Design principles (see reference_data.py for tunable constants):
  1. Primary signal: each vehicle has a latent "alternator degradation rate".
     That single latent variable drives BOTH the alternator-relevant telematics
     signals (coolant_temp_variance, oil_pressure_dips, battery_voltage_sag,
     dtc_recurrence_rate) AND the alternator failure probability. This is a
     genuine common-cause relationship, not a label copied into a feature.
  2. Confounder: each vehicle's region sets a "road roughness" multiplier that
     drives BOTH harsh-braking/overload telematics AND wear-based failure
     probability for chassis/engine parts (brake pads, suspension, turbo) —
     so the effect shows up across multiple parts, not just one.
  3. Seasonality: coolant_temp_variance carries a seasonal bump in summer
     months, independent of vehicle-level degradation.
  4. Heterogeneity: usage intensity and registration age vary per vehicle,
     producing realistic spread in odometer readings.

Run: python scripts/generate_data.py
Reproducible: fixed SEED in reference_data.py.
"""
import random
import sys
from datetime import date, timedelta
from pathlib import Path

import numpy as np

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.core.database import SessionLocal, engine, Base
import app.models  # noqa: F401 populate metadata
from app.models.core import Vehicle, Part
from app.models.fleet_owner import FleetOwner
from app.models.failure import Failure
from app.models.rules import Prediction, RuleConfig
from app.models.user import User
from app.models.telematics import TelematicsWeekly

from scripts.reference_data import (
    FLEET_OWNERS,
    SEED, N_VEHICLES, SIM_START, SIM_WEEKS, PARTS, MODELS, REGIONS,
    REGION_ROAD_ROUGHNESS, USAGE_INTENSITY_MEAN, USAGE_INTENSITY_STD,
    USAGE_INTENSITY_MIN, USAGE_INTENSITY_MAX, BASE_MONTHLY_KM, VIN_ALPHABET,
    WEAR_K, WEAR_RAW_CAP, WEAR_EXPONENT, ALTERNATOR_INTERCEPT, ALTERNATOR_DEGRADATION_COEF,
)


def sigmoid(z):
    return 1.0 / (1.0 + np.exp(-z))


def seasonal_coolant_bump(month: int) -> float:
    """Peaks in summer (Jun-Aug), lowest in winter (Dec-Feb)."""
    # cosine centered so July (month=7) is the peak
    return 0.12 * np.cos((month - 7) * (2 * np.pi / 12)) + 0.03


def make_vin(rng: random.Random, index: int) -> str:
    body = "".join(rng.choice(VIN_ALPHABET) for _ in range(11))
    return f"1FL{body}{index:03d}"[:17]


def random_registration_date(rng: random.Random) -> date:
    # vehicles registered between ~6 years and ~4 months before SIM_START
    days_back = rng.randint(120, 6 * 365)
    return SIM_START - timedelta(days=days_back)


def build_vehicles(rng: random.Random, np_rng: np.random.Generator):
    vehicles = []
    for i in range(N_VEHICLES):
        region = rng.choice(REGIONS)
        model = rng.choice(MODELS)
        reg_date = random_registration_date(rng)
        usage_intensity = float(np.clip(
            np_rng.normal(USAGE_INTENSITY_MEAN, USAGE_INTENSITY_STD),
            USAGE_INTENSITY_MIN, USAGE_INTENSITY_MAX,
        ))
        age_days_at_window_end = (SIM_START + timedelta(days=SIM_WEEKS * 7) - reg_date).days
        age_months = age_days_at_window_end / 30.44
        total_km = max(1000, int(age_months * BASE_MONTHLY_KM * usage_intensity
                                  + np_rng.normal(0, 800)))
        degradation_rate = float(max(0.0, np_rng.normal(1.0, 0.6)))

        vehicles.append({
            "vin": make_vin(rng, i),
            "model": model,
            "region": region,
            "registration_date": reg_date,
            "total_km_driven": total_km,
            "usage_intensity": usage_intensity,     # not persisted; used for telematics
            "degradation_rate": degradation_rate,    # not persisted; latent driver
        })
    return vehicles


def build_telematics_for_vehicle(vehicle: dict, np_rng: np.random.Generator):
    rows = []
    roughness = REGION_ROAD_ROUGHNESS[vehicle["region"]]
    degr = vehicle["degradation_rate"]
    usage = vehicle["usage_intensity"]

    for week in range(SIM_WEEKS):
        week_start = SIM_START + timedelta(days=week * 7)
        week_frac = week / (SIM_WEEKS - 1)
        month = week_start.month

        coolant = 0.15 + seasonal_coolant_bump(month) + 0.35 * degr * week_frac \
            + np_rng.normal(0, 0.05)
        oil_dips_lambda = max(0.05, 0.5 + 2.0 * degr * week_frac)
        battery_sag = 0.10 + 0.25 * degr * week_frac + np_rng.normal(0, 0.04)
        dtc_rate = 0.05 + 0.20 * degr * week_frac + np_rng.normal(0, 0.03)

        harsh_braking = 0.18 * roughness + np_rng.normal(0, 0.05)
        overload_share = 0.13 * roughness + np_rng.normal(0, 0.05)
        high_rpm_dwell = 0.20 + 0.08 * usage + np_rng.normal(0, 0.05)
        short_trip_ratio = 0.30 - 0.04 * usage + np_rng.normal(0, 0.05)
        idle_pct = 0.10 + np_rng.normal(0, 0.04)

        rows.append(TelematicsWeekly(
            vin=vehicle["vin"],
            week_start_date=week_start,
            coolant_temp_variance=float(np.clip(coolant, 0, 1)),
            oil_pressure_dips=int(np_rng.poisson(oil_dips_lambda)),
            battery_voltage_sag=float(np.clip(battery_sag, 0, 1)),
            dtc_recurrence_rate=float(np.clip(dtc_rate, 0, 1)),
            harsh_braking_frequency=float(np.clip(harsh_braking, 0, 1)),
            overload_duty_share=float(np.clip(overload_share, 0, 1)),
            high_rpm_dwell_time=float(np.clip(high_rpm_dwell, 0, 1)),
            short_trip_ratio=float(np.clip(short_trip_ratio, 0, 1)),
            idle_time_pct=float(np.clip(idle_pct, 0, 1)),
        ))
    return rows


def decide_alternator_failure(vehicle: dict, rng: random.Random, np_rng: np.random.Generator):
    """Primary signal relationship: driven by the same latent degradation_rate
    that shapes the telematics above (common cause, not a copied label)."""
    z = ALTERNATOR_INTERCEPT + ALTERNATOR_DEGRADATION_COEF * vehicle["degradation_rate"] \
        + np_rng.normal(0, 1.0)
    p = sigmoid(z)
    if rng.random() < p:
        fail_week = rng.randint(12, SIM_WEEKS - 1)
        return fail_week
    return None


def decide_wear_failure(vehicle: dict, part: dict, rng: random.Random, np_rng: np.random.Generator):
    """Wear-based failure for non-alternator parts. Chassis/Engine parts get
    the region-roughness confounder applied; Cooling (radiator) does not,
    so it acts as a 'control' part with no regional effect."""
    raw_wear = min(vehicle["total_km_driven"] / part["design_life_km"], WEAR_RAW_CAP)
    if part["category"] in ("Chassis", "Engine"):
        wear_ratio = raw_wear * REGION_ROAD_ROUGHNESS[vehicle["region"]]
    else:
        wear_ratio = raw_wear  # Cooling/Radiator: control part, no regional effect

    k = WEAR_K[part["part_code"]]
    p = float(np.clip(k * (wear_ratio ** WEAR_EXPONENT), 0, 0.6))
    if rng.random() < p:
        # bias toward later weeks (more accumulated wear by then)
        weights = np.arange(1, SIM_WEEKS + 1, dtype=float)
        fail_week = int(np_rng.choice(np.arange(SIM_WEEKS), p=weights / weights.sum()))
        return fail_week
    return None


def odometer_at_week(vehicle: dict, fail_week: int) -> int:
    km_per_week = vehicle["total_km_driven"] / max(SIM_WEEKS, 1)
    remaining_weeks = SIM_WEEKS - fail_week
    return max(0, int(vehicle["total_km_driven"] - km_per_week * remaining_weeks))


def main():
    rng = random.Random(SEED)
    np_rng = np.random.default_rng(SEED)

    print("Creating tables if missing (safety net; alembic should already have done this)...")
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        print("Wiping existing generated data (failures, telematics, vehicles, parts, fleet owners)...")
        db.query(Failure).delete()
        db.query(Prediction).delete()   # FK -> vehicles, parts (added Day 4)
        db.query(RuleConfig).delete()   # FK -> parts (added Day 3)
        db.query(TelematicsWeekly).delete()
        db.query(User).update({User.fleet_owner_id: None})  # FK -> fleet_owners
        db.query(Vehicle).delete()
        db.query(Part).delete()
        db.query(FleetOwner).delete()
        db.commit()

        print(f"Inserting {len(PARTS)} parts...")
        for p in PARTS:
            db.add(Part(**p))
        db.commit()

        print(f"Creating {len(FLEET_OWNERS)} fleet owners...")
        owners = [FleetOwner(name=n) for n in FLEET_OWNERS]
        db.add_all(owners)
        db.commit()
        for o in owners:
            db.refresh(o)

        # Re-link any already-seeded demo users to the fresh fleet_owner
        # rows we just created, matching on the User.name each account was
        # seeded with (scripts/seed_demo_users.py sets User.name to the
        # fleet owner's name). Without this, re-running this script leaves
        # every fleet_owner user's fleet_owner_id permanently None (nulled
        # a few lines above, and the old FleetOwner rows they pointed at
        # are gone) — which get_fleet_scope now treats as "no fleet
        # assigned" and blocks with a 403, rather than the old silent
        # "see every fleet" bug. Re-linking here means a re-run of this
        # script doesn't break the demo accounts at all.
        owners_by_name = {o.name: o for o in owners}
        existing_users = db.query(User).filter(User.role == "fleet_owner").all()
        if existing_users:
            relinked = 0
            for u in existing_users:
                match = owners_by_name.get(u.name)
                if match:
                    u.fleet_owner_id = match.id
                    relinked += 1
            db.commit()
            print(f"Re-linked {relinked}/{len(existing_users)} existing fleet_owner "
                  f"users to their (recreated) fleet owner. Any not matched by name "
                  f"need scripts/seed_demo_users.py re-run.")

        print(f"Generating {N_VEHICLES} vehicles...")
        vehicles = build_vehicles(rng, np_rng)
        for i, v in enumerate(vehicles):
            db.add(Vehicle(
                vin=v["vin"], model=v["model"], region=v["region"],
                registration_date=v["registration_date"],
                total_km_driven=v["total_km_driven"],
                fleet_owner_id=owners[i % len(owners)].id,  # even round-robin split
            ))
        db.commit()
        print("Vehicles committed.")

        print(f"Generating {SIM_WEEKS} weeks of telematics per vehicle "
              f"({N_VEHICLES * SIM_WEEKS} rows total)...")
        batch = []
        for v in vehicles:
            batch.extend(build_telematics_for_vehicle(v, np_rng))
            if len(batch) >= 5000:
                db.bulk_save_objects(batch)
                db.commit()
                batch = []
        if batch:
            db.bulk_save_objects(batch)
            db.commit()
        print("Telematics committed.")

        print("Sampling failures per vehicle/part...")
        failure_rows = []
        job_counter = 1
        counts_by_part = {p["part_code"]: 0 for p in PARTS}

        for v in vehicles:
            for part in PARTS:
                if part["part_code"] == "ELC-0152":
                    fail_week = decide_alternator_failure(v, rng, np_rng)
                else:
                    fail_week = decide_wear_failure(v, part, rng, np_rng)

                if fail_week is not None:
                    failure_date = SIM_START + timedelta(days=fail_week * 7)
                    odometer = odometer_at_week(v, fail_week)
                    job_card_id = f"JC-2025-{job_counter:06d}"
                    job_counter += 1
                    failure_rows.append(Failure(
                        job_card_id=job_card_id,
                        vin=v["vin"],
                        part_code=part["part_code"],
                        failure_date=failure_date,
                        odometer_at_failure_km=odometer,
                        replaced=True,
                    ))
                    counts_by_part[part["part_code"]] += 1

        db.bulk_save_objects(failure_rows)
        db.commit()

        total_failures = len(failure_rows)
        print(f"\nFailures committed. Total: {total_failures}")
        for code, cnt in counts_by_part.items():
            name = next(p["part_name"] for p in PARTS if p["part_code"] == code)
            print(f"  {code} ({name}): {cnt}")

        if not (150 <= total_failures <= 250):
            print(f"\n⚠️  Total failures ({total_failures}) is outside the target "
                  f"150-250 range — see scripts/reference_data.py base_k / degradation "
                  f"constants to tune.")
        else:
            print(f"\n✅ Total failures ({total_failures}) within target range (150-250).")

    finally:
        db.close()


if __name__ == "__main__":
    main()
