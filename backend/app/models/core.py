"""
Core reference tables: Vehicle Master, Part Master.
These are the two tables everything else foreign-keys into.
"""
from sqlalchemy import Column, String, Integer, Date, ForeignKey
from sqlalchemy.orm import relationship

from app.core.database import Base


class Vehicle(Base):
    __tablename__ = "vehicles"

    vin = Column(String(17), primary_key=True)  # real VIN format, 17 chars
    model = Column(String(100), nullable=False)  # e.g. "Long-Haul Tractor"
    region = Column(String(50), nullable=False)  # e.g. "North", "South", "East", "West"
    registration_date = Column(Date, nullable=False)
    total_km_driven = Column(Integer, nullable=False)
    fleet_owner_id = Column(Integer, ForeignKey("fleet_owners.id"), nullable=True, index=True)

    fleet_owner = relationship("FleetOwner", back_populates="vehicles")
    failures = relationship("Failure", back_populates="vehicle")
    telematics = relationship("TelematicsWeekly", back_populates="vehicle")
    predictions = relationship("Prediction", back_populates="vehicle")

    def __repr__(self):
        return f"<Vehicle {self.vin} {self.model} ({self.region})>"


class Part(Base):
    __tablename__ = "parts"

    part_code = Column(String(20), primary_key=True)  # e.g. "ELC-0152"
    part_name = Column(String(100), nullable=False)  # e.g. "Alternator"
    category = Column(String(50), nullable=False)  # e.g. "Electrical", "Chassis", "Cooling"
    design_life_km = Column(Integer, nullable=False)

    failures = relationship("Failure", back_populates="part")
    rule_configs = relationship("RuleConfig", back_populates="part")
    predictions = relationship("Prediction", back_populates="part")

    def __repr__(self):
        return f"<Part {self.part_code} {self.part_name}>"
