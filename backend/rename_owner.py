import sys
sys.path.append('.')
from app.core.database import SessionLocal
from app.models.fleet_owner import FleetOwner
db = SessionLocal()
o = db.query(FleetOwner).filter(FleetOwner.name=='Harborline Transport').first()
o.name = 'Nandani AAYS'
db.commit()
print('renamed to', o.name)
