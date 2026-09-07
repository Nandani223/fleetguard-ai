"""
Import every model module here so that Base.metadata is fully populated
before Alembic's autogenerate (or Base.metadata.create_all) runs.
"""
from app.models.core import Vehicle, Part          # noqa: F401
from app.models.failure import Failure               # noqa: F401
from app.models.telematics import TelematicsWeekly   # noqa: F401
from app.models.rules import RuleConfig, Prediction  # noqa: F401
from app.models.fleet_owner import FleetOwner        # noqa: F401
from app.models.user import User                     # noqa: F401
