import sys
sys.path.append('.')
from app.core.database import SessionLocal
from app.models.fleet_owner import FleetOwner
db = SessionLocal()
o = db.query(FleetOwner).filter(FleetOwner.name == 'Harborline Transport').first()
if o is None:
    already = db.query(FleetOwner).filter(FleetOwner.name == 'Nandani AAYS').first()
    if already:
        print("Nothing to do — a fleet owner is already named 'Nandani AAYS'. "
              "(As of the reference_data.py fix, scripts/generate_data.py creates "
              "it with this name directly, so this script shouldn't be needed anymore.)")
    else:
        print("No fleet owner named 'Harborline Transport' or 'Nandani AAYS' found. "
              "Run scripts/generate_data.py first.")
else:
    o.name = 'Nandani AAYS'
    db.commit()
    print('renamed to', o.name)
