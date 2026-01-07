"""Authentication routes for PIN-based login."""

import os

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from .tokens import create_access_token

router = APIRouter(prefix="/auth", tags=["Authentication"])

# PIN for authentication - set via environment variable
APP_PIN = os.getenv("APP_PIN", "1234")  # Default for development only


class LoginRequest(BaseModel):
    """Login request with PIN."""

    pin: str


class LoginResponse(BaseModel):
    """Login response with access token."""

    access_token: str
    token_type: str = "bearer"


@router.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest) -> LoginResponse:
    """Authenticate with PIN and receive an access token.

    The token is valid for 30 days and should be included in the
    Authorization header for all subsequent requests.
    """
    if request.pin != APP_PIN:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid PIN",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(subject="app_user")
    return LoginResponse(access_token=access_token)
