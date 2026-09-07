"""
POST /auth/sso-login — exchange a verified Microsoft ID token for a FleetGuard JWT.
GET  /auth/me         — who am I, based on the current token.

Deliberately stricter than Meridian's sso_login: Meridian auto-created an
"Employee" record for ANY Microsoft login in the tenant. Here, unknown
emails are rejected with 403 — role="fleet_owner" grants real
data-scoping rights over a specific fleet, so self-provisioning is not
acceptable. Demo users are pre-seeded via scripts/seed_demo_users.py.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.auth import create_access_token, get_current_user, verify_password
from app.core.oidc_auth import verify_oidc_token
from app.models.user import User
from app.schemas.auth import SSOLoginRequest, LoginRequest, TokenResponse, UserOut

router = APIRouter(prefix="/auth", tags=["auth"])


def _to_user_out(user: User) -> UserOut:
    return UserOut(
        id=user.id, email=user.email, name=user.name, role=user.role,
        fleet_owner_id=user.fleet_owner_id,
        fleet_owner_name=user.fleet_owner.name if user.fleet_owner else None,
    )


@router.post("/login", response_model=TokenResponse)
def login(credentials: LoginRequest, db: Session = Depends(get_db)):
    """Password login — for the demo 'data' accounts (fleet owners you
    won't personally log in as during the video). Accounts created with
    hashed_password=None (SSO-only) can never authenticate here."""
    user = db.query(User).filter(User.email == credentials.email).first()
    if not user or not user.hashed_password or not verify_password(credentials.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect email or password")
    token = create_access_token(user.id)
    return TokenResponse(access_token=token, user=_to_user_out(user))


@router.post("/sso-login", response_model=TokenResponse)
def sso_login(payload: SSOLoginRequest, db: Session = Depends(get_db)):
    claims = verify_oidc_token(payload.token)
    email = claims.get("email") or claims.get("preferred_username")
    if not email:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                             detail="Microsoft token did not include an email address")

    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"'{email}' is not provisioned for FleetGuard AI. "
                   f"Ask an admin to add this email via scripts/seed_demo_users.py.",
        )

    token = create_access_token(user.id)
    return TokenResponse(access_token=token, user=_to_user_out(user))


@router.get("/me", response_model=UserOut)
def me(current_user: User = Depends(get_current_user)):
    return _to_user_out(current_user)
