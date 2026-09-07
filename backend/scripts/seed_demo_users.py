"""
Seeds the demo login accounts.

- admin@fleetguard-demo.com  -> admin, sees ALL 400 vehicles (password login)
- owner1@fleetguard-demo.com -> fleet_owner, sees ONLY Fleet Owner 1's vehicles (password)
- owner2@fleetguard-demo.com -> fleet_owner, sees ONLY Fleet Owner 2's vehicles (password)
- nandanik@aaysinsight.com  -> fleet_owner, sees ONLY Fleet Owner 3's vehicles (SSO only)
  This proves the Microsoft login button genuinely works on stage, and
  as a bonus also proves scoping works through the SSO path too.

Edit MY_MICROSOFT_EMAIL below, then run:
    python scripts/seed_demo_users.py

Re-runnable: wipes and re-seeds the users table each time.
"""
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.core.database import SessionLocal
from app.core.auth import hash_password
from app.models.user import User
from app.models.fleet_owner import FleetOwner

# ---- EDIT THIS with your real Microsoft account email ----
MY_MICROSOFT_EMAIL = "nandanik@aaysinsight.com"
# ------------------------------------------------------------

ADMIN_EMAIL = "admin@fleetguard-demo.com"
ADMIN_PASSWORD = "Admin#2026"

PASSWORD_OWNERS = [
    {"owner_name": "Continental Freight Co.", "email": "owner1@fleetguard-demo.com", "password": "Owner1#2026"},
    {"owner_name": "Summit Logistics Group", "email": "owner2@fleetguard-demo.com", "password": "Owner2#2026"},
]
SSO_OWNER_NAME = "Nandani AAYS"  # mapped to your real Microsoft email


def main():
    db = SessionLocal()
    try:
        db.query(User).delete()
        db.commit()

        owners = {o.name: o for o in db.query(FleetOwner).all()}
        if not owners:
            print("No fleet owners found - run scripts/generate_data.py first.")
            return

        db.add(User(email=ADMIN_EMAIL, name="Admin", role="admin",
                     fleet_owner_id=None, hashed_password=hash_password(ADMIN_PASSWORD)))

        for acct in PASSWORD_OWNERS:
            owner = owners.get(acct["owner_name"])
            if not owner:
                print(f"WARNING: fleet owner '{acct['owner_name']}' not found, skipping")
                continue
            db.add(User(email=acct["email"], name=acct["owner_name"], role="fleet_owner",
                         fleet_owner_id=owner.id, hashed_password=hash_password(acct["password"])))

        sso_owner = owners.get(SSO_OWNER_NAME)
        if sso_owner:
            db.add(User(email=MY_MICROSOFT_EMAIL, name=SSO_OWNER_NAME, role="fleet_owner",
                         fleet_owner_id=sso_owner.id, hashed_password=None))

        db.commit()
        print("Seeded users:\n")
        print(f"  ADMIN (sees all 400 vehicles):")
        print(f"    {ADMIN_EMAIL} / {ADMIN_PASSWORD}\n")
        print(f"  FLEET OWNERS (each sees only their own ~133 vehicles):")
        for acct in PASSWORD_OWNERS:
            print(f"    {acct['email']} / {acct['password']}  ({acct['owner_name']})")
        print(f"    {MY_MICROSOFT_EMAIL}  (Microsoft SSO only, {SSO_OWNER_NAME})")
    finally:
        db.close()


if __name__ == "__main__":
    main()
