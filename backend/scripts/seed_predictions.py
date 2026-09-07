"""
Runs the full rule -> score -> RUL pipeline for every part in one go.

Needed after every generate_data.py run: that script wipes the
predictions and rule_config tables (to avoid stale FK references to
regenerated vehicles), so Failure Probability / RUL Explorer are empty
until this is re-run. Clicking "Run Scoring" / "Run RUL" in the UI does
the same thing, but one part at a time — this does all 5 at once.

Run: python scripts/seed_predictions.py
"""
import sys
from datetime import date
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.core.database import SessionLocal
from app.models.core import Part
from app.services.correlation import compute_correlations
from app.services.rule_builder import build_and_persist_rule
from app.services.scoring import run_and_persist, SIM_AS_OF_DATE
from app.services.rul import run_rul_for_part
from app.schemas.rule import RuleBuildRequest, RuleSignalIn

METHOD = "point_biserial"
INCLUSION_THRESHOLD = 0.08  # matches the frontend's default pre-checked signals


def main():
    db = SessionLocal()
    try:
        parts = db.query(Part).all()
        if not parts:
            print("No parts found — run scripts/generate_data.py first.")
            return

        for part in parts:
            print(f"\n=== {part.part_code} ({part.part_name}) ===")

            results, meta = compute_correlations(db, part.part_code)
            signals = [
                RuleSignalIn(signal=r.signal, included=abs(r.point_biserial_r) > INCLUSION_THRESHOLD)
                for r in results
            ]
            build_and_persist_rule(db, part.part_code, RuleBuildRequest(method=METHOD, signals=signals))
            n_included = sum(1 for s in signals if s.included)
            print(f"  Rule built: {n_included} signals included")

            pred_result = run_and_persist(db, part.part_code, METHOD, SIM_AS_OF_DATE)
            print(f"  Predictions: {pred_result['tier_counts']}")

            rul_result = run_rul_for_part(db, part.part_code, METHOD, SIM_AS_OF_DATE)
            print(f"  RUL: updated {rul_result['n_updated']} predictions, "
                  f"avg {rul_result['avg_rul_days']} days")

        print("\nAll 5 parts scored. Failure Probability and RUL Explorer should now show data.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
