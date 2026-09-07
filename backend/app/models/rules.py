"""
Rule Config — the persisted, per-part weighted scoring rule produced by
the Rule Builder (Day 3). Predictions — the fleet-wide scoring output
produced by applying a rule (Day 4) plus the RUL estimate (Day 5).
"""
from sqlalchemy import (
    Column, String, Integer, Float, Date, Boolean, ForeignKey,
    UniqueConstraint, CheckConstraint,
)
from sqlalchemy.orm import relationship

from app.core.database import Base


class RuleConfig(Base):
    __tablename__ = "rule_config"

    id = Column(Integer, primary_key=True, autoincrement=True)
    part_code = Column(String(20), ForeignKey("parts.part_code"), nullable=False, index=True)
    signal = Column(String(50), nullable=False)  # e.g. "coolant_temp_variance"
    correlation_weight = Column(Float, nullable=False)  # normalized weight, sums to 1 across included signals
    raw_score = Column(Float, nullable=False, default=0.0)  # the underlying point_biserial_r or xgboost_importance, unnormalized
    included = Column(Boolean, nullable=False, default=True)
    method = Column(String(30), nullable=False, default="logistic_regression")
    # "logistic_regression" or "xgboost_importance" — which method produced this weight (Day 3)

    __table_args__ = (
        UniqueConstraint("part_code", "signal", "method", name="uq_rule_part_signal_method"),
    )

    part = relationship("Part", back_populates="rule_configs")

    def __repr__(self):
        return f"<RuleConfig {self.part_code}:{self.signal} w={self.correlation_weight}>"


class Prediction(Base):
    __tablename__ = "predictions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    vin = Column(String(17), ForeignKey("vehicles.vin"), nullable=False, index=True)
    part_code = Column(String(20), ForeignKey("parts.part_code"), nullable=False, index=True)
    failure_probability = Column(Float, nullable=False)  # 0-1
    risk_tier = Column(String(10), nullable=False)  # "Green" | "Amber" | "Red"
    estimated_window_days = Column(Integer, nullable=True)  # rough failure window
    rul_km = Column(Integer, nullable=True)
    rul_days = Column(Integer, nullable=True)
    top_signals = Column(String(255), nullable=True)  # comma-separated, e.g. top 3 contributing signals
    computed_date = Column(Date, nullable=False)

    __table_args__ = (
        UniqueConstraint("vin", "part_code", "computed_date", name="uq_prediction_vin_part_date"),
        CheckConstraint("risk_tier in ('Green','Amber','Red')", name="ck_risk_tier_valid"),
    )

    vehicle = relationship("Vehicle", back_populates="predictions")
    part = relationship("Part", back_populates="predictions")

    def __repr__(self):
        return f"<Prediction {self.vin}/{self.part_code} {self.risk_tier} {self.failure_probability:.2f}>"
