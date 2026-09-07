from typing import Optional
from pydantic import BaseModel


class SSOLoginRequest(BaseModel):
    token: str  # Microsoft ID token from MSAL


class LoginRequest(BaseModel):
    email: str
    password: str


class UserOut(BaseModel):
    id: int
    email: str
    name: Optional[str]
    role: str
    fleet_owner_id: Optional[int]
    fleet_owner_name: Optional[str] = None

    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut
