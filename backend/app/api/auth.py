"""
POST /auth/sso-login — exchange a verified Microsoft ID token for a FleetGuard JWT.
GET  /auth/me         — who am I, based on the current token.
 
Microsoft SSO:
- Any verified @aaysinsight.com account is automatically provisioned as an admin.
- Other Microsoft accounts are rejected unless they already exist in the users table.
 
Password login remains available for pre-seeded demo accounts.
"""
 
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
 
from app.core.database import get_db
from app.core.auth import create_access_token, get_current_user, verify_password
from app.core.oidc_auth import verify_oidc_token
from app.models.user import User
from app.schemas.auth import SSOLoginRequest, LoginRequest, TokenResponse, UserOut
 
router = APIRouter(prefix="/auth", tags=["auth"])
 
AAYSINSIGHT_DOMAIN = "aaysinsight.com"
 
 
def _to_user_out(user: User) -> UserOut:
    return UserOut(
        id=user.id,
        email=user.email,
        name=user.name,
        role=user.role,
        fleet_owner_id=user.fleet_owner_id,
        fleet_owner_name=user.fleet_owner.name if user.fleet_owner else None,
    )
 
 
@router.post("/login", response_model=TokenResponse)
def login(credentials: LoginRequest, db: Session = Depends(get_db)):
    """Password login — for pre-seeded demo accounts.
 
    Accounts with hashed_password=None are SSO-only and cannot
    authenticate using a password.
    """
    user = db.query(User).filter(User.email == credentials.email).first()
 
    if (
        not user
        or not user.hashed_password
        or not verify_password(credentials.password, user.hashed_password)
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )
 
    token = create_access_token(user.id)
 
    return TokenResponse(
        access_token=token,
        user=_to_user_out(user),
    )
 
 
@router.post("/sso-login", response_model=TokenResponse)
def sso_login(payload: SSOLoginRequest, db: Session = Depends(get_db)):
    """Microsoft SSO login.
 
    Any verified Microsoft account from @aaysinsight.com is
    automatically created as an admin if it does not already
    exist in the FleetGuard users table.
    """
 
    # 1. Verify the Microsoft ID token.
    claims = verify_oidc_token(payload.token)
 
    # 2. Get the user's email from the Microsoft token.
    email = claims.get("email") or claims.get("preferred_username")
 
    if not email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Microsoft token did not include an email address",
        )
 
    # Normalize the email to avoid case/whitespace mismatches.
    email = email.strip().lower()
 
    # 3. Check whether the user already exists.
    user = db.query(User).filter(User.email == email).first()
 
    # 4. If the user does not exist, automatically provision
    #    verified AAYS Insight accounts as administrators.
    if not user:
        domain = email.rsplit("@", 1)[-1]
 
        if domain == AAYSINSIGHT_DOMAIN:
            user = User(
                email=email,
                name=claims.get("name") or email,
                role="admin",
                fleet_owner_id=None,
            )
 
            db.add(user)
            db.commit()
            db.refresh(user)
 
        else:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"'{email}' is not provisioned for FleetGuard AI.",
            )
 
    # 5. Create FleetGuard's own JWT.
    token = create_access_token(user.id)
 
    return TokenResponse(
        access_token=token,
        user=_to_user_out(user),
    )
 
 
@router.get("/me", response_model=UserOut)
def me(current_user: User = Depends(get_current_user)):
    """Return the currently authenticated FleetGuard user."""
    return _to_user_out(current_user)
 