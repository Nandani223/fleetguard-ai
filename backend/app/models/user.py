"""
App users, mapped from Microsoft SSO identity to a role.

Adapted from the Meridian ESOP portal's auth pattern, but intentionally
STRICTER: Meridian auto-provisioned any Microsoft login in the tenant as
a new "Employee". FleetGuard does NOT do that — only pre-provisioned
emails (seeded via scripts/seed_demo_users.py) can log in. An unknown
email gets a 403, not a free account. This matters here because
"fleet_owner" grants real data-scoping rights; auto-provisioning would
let anyone see SOME fleet's data by just being able to sign into Azure.
"""
from sqlalchemy import Column, Integer, String, ForeignKey, CheckConstraint
from sqlalchemy.orm import relationship
from app.core.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String(255), nullable=False, unique=True, index=True)
    name = Column(String(150), nullable=True)
    role = Column(String(20), nullable=False)  # "admin" | "fleet_owner"
    fleet_owner_id = Column(Integer, ForeignKey("fleet_owners.id"), nullable=True)
    hashed_password = Column(String(255), nullable=True)  # NULL = SSO-only account,
                                                            # can never log in with a password

    fleet_owner = relationship("FleetOwner")

    __table_args__ = (
        CheckConstraint("role in ('admin','fleet_owner')", name="ck_user_role_valid"),
    )
