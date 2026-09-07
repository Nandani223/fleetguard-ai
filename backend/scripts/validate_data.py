"""
FleetGuard AI — Day 2 validation checkpoint.

Run this after generate_data.py to confirm the synthetic data actually
has a discoverable signal, not just a name suggesting one. Checks:
  1. Primary signal: alternator failure correlates with coolant/oil/battery
     telematics (point-biserial correlation, should be moderate-strong,
     ~0.4-0.6, with p < 0.001 — not near-1.0, which would mean the data
     is trivially "rigged" rather than realistically noisy).
  2. Confounder: North region has a visibly higher failure RATE for
     roughness-affected parts (brake pads, suspension, turbo) than other
     regions, while the radiator (control part, no regional effect coded)
     stays roughly flat across regions.

Run: python scripts/validate_data.py
"""
import sys
from pathlib import Path

import pandas as pd
from scipy.stats import pointbiserialr

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.core.database import SessionLocal
from app.models.core import Vehicle
from app.models.failure import Failure
from app.models.telematics import TelematicsWeekly


def check_primary_signal(db):
    print("=" * 70)
    print("CHECK 1: Primary signal — alternator failure vs. telematics")
    print("=" * 70)
    alt_failed_vins = set(v[0] for v in db.query(Failure.vin)
                           .filter(Failure.part_code == "ELC-0152").all())
    vehicles = db.query(Vehicle.vin).all()

    rows = []
    for (vin,) in vehicles:
        tele = (db.query(TelematicsWeekly)
                .filter(TelematicsWeekly.vin == vin)
                .order_by(TelematicsWeekly.week_start_date.desc())
                .limit(8).all())
        if not tele:
            continue
        rows.append({
            "alt_failed": 1 if vin in alt_failed_vins else 0,
            "avg_coolant": sum(t.coolant_temp_variance for t in tele) / len(tele),
            "avg_oil_dips": sum(t.oil_pressure_dips for t in tele) / len(tele),
            "avg_battery": sum(t.battery_voltage_sag for t in tele) / len(tele),
        })
    df = pd.DataFrame(rows)

    ok = True
    for col in ["avg_coolant", "avg_oil_dips", "avg_battery"]:
        r, p = pointbiserialr(df["alt_failed"], df[col])
        status = "OK" if (0.25 <= abs(r) <= 0.85 and p < 0.01) else "CHECK"
        if status == "CHECK":
            ok = False
        print(f"  {col:15s} r={r:+.3f}  p={p:.5f}  [{status}]")
    print(f"  alternator failure rate: {df['alt_failed'].mean():.3f}")
    print()
    return ok


def check_confounder(db):
    print("=" * 70)
    print("CHECK 2: Regional confounder — North vs. other regions")
    print("=" * 70)
    vehicles = db.query(Vehicle.vin, Vehicle.region).all()
    vdf = pd.DataFrame(vehicles, columns=["vin", "region"])
    region_counts = vdf.groupby("region").size()

    failures = db.query(Failure.vin, Failure.part_code).all()
    fdf = pd.DataFrame(failures, columns=["vin", "part_code"]).merge(vdf, on="vin")

    pivot = fdf.groupby(["region", "part_code"]).size().unstack(fill_value=0)
    rate = pivot.div(region_counts, axis=0)
    print(rate.round(3))
    print()

    roughness_parts = ["CHS-0330", "CHS-0410", "ENG-0500"]
    control_part = "COL-0210"

    ok = True
    for part in roughness_parts:
        if part not in rate.columns:
            continue
        north_rate = rate.loc["North", part]
        other_rate = rate.drop("North")[part].mean()
        status = "OK" if north_rate > other_rate else "CHECK"
        if status == "CHECK":
            ok = False
        print(f"  {part}: North={north_rate:.3f} vs. others avg={other_rate:.3f}  [{status}]")

    if control_part in rate.columns:
        spread = rate[control_part].max() - rate[control_part].min()
        status = "OK" if spread < 0.06 else "CHECK"
        print(f"  {control_part} (control, should be flat): spread={spread:.3f}  [{status}]")
        if status == "CHECK":
            ok = False
    print()
    return ok


def main():
    db = SessionLocal()
    try:
        r1 = check_primary_signal(db)
        r2 = check_confounder(db)
        print("=" * 70)
        if r1 and r2:
            print("✅ All checks passed — data has real, discoverable signal.")
        else:
            print("⚠️  Some checks flagged — review reference_data.py constants.")
        print("=" * 70)
    finally:
        db.close()


if __name__ == "__main__":
    main()
