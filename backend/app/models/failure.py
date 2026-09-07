"""
Job Card / Failure History — one row per part failure/replacement event.
This is the ground truth the correlation engine (Day 3) learns from.
"""
from sqlalchemy import Column, String, Integer, Date, Boolean, ForeignKey
from sqlalchemy.orm import relationship

from app.core.database import Base


class Failure(Base):
    __tablename__ = "failures"

    job_card_id = Column(String(30), primary_key=True)  # e.g. "JC-2025-000431"
    vin = Column(String(17), ForeignKey("vehicles.vin"), nullable=False, index=True)
    part_code = Column(String(20), ForeignKey("parts.part_code"), nullable=False, index=True)
    failure_date = Column(Date, nullable=False)
    odometer_at_failure_km = Column(Integer, nullable=False)
    replaced = Column(Boolean, nullable=False, default=True)

    vehicle = relationship("Vehicle", back_populates="failures")
    part = relationship("Part", back_populates="failures")

    def __repr__(self):
        return f"<Failure {self.job_card_id} {self.vin}/{self.part_code} on {self.failure_date}>"
