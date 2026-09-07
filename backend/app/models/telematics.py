"""
Telematics Signals — weekly aggregate per vehicle. This is vehicle-level
(not part-level) per the agreed schema; the correlation engine joins it
against Failure History on VIN + a lookback window.
"""
from sqlalchemy import Column, String, Integer, Date, Float, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship

from app.core.database import Base


class TelematicsWeekly(Base):
    __tablename__ = "telematics_weekly"

    id = Column(Integer, primary_key=True, autoincrement=True)
    vin = Column(String(17), ForeignKey("vehicles.vin"), nullable=False, index=True)
    week_start_date = Column(Date, nullable=False, index=True)

    coolant_temp_variance = Column(Float, nullable=False)      # normalised 0-1
    oil_pressure_dips = Column(Integer, nullable=False)        # count in the week
    battery_voltage_sag = Column(Float, nullable=False)        # normalised 0-1
    dtc_recurrence_rate = Column(Float, nullable=False)        # normalised 0-1
    harsh_braking_frequency = Column(Float, nullable=False)    # normalised 0-1
    overload_duty_share = Column(Float, nullable=False)        # % of trips overloaded
    high_rpm_dwell_time = Column(Float, nullable=False)        # % of runtime
    short_trip_ratio = Column(Float, nullable=False)           # % of trips under 10km
    idle_time_pct = Column(Float, nullable=False)              # % of runtime idling

    __table_args__ = (
        UniqueConstraint("vin", "week_start_date", name="uq_telematics_vin_week"),
    )

    vehicle = relationship("Vehicle", back_populates="telematics")

    def __repr__(self):
        return f"<TelematicsWeekly {self.vin} week={self.week_start_date}>"
