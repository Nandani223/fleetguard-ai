"""FleetOwner: the organizational grouping vehicles belong to. A small
number of these (not one per vehicle) — real fleets are owned by
companies, not individually. Demo scope: 3 fleet owners, ~130 vehicles each."""
from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship
from app.core.database import Base


class FleetOwner(Base):
    __tablename__ = "fleet_owners"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)

    vehicles = relationship("Vehicle", back_populates="fleet_owner")
