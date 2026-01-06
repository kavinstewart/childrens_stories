"""Authentication routes for PIN-based login and Hume EVI tokens."""

import os

import httpx
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from ..dependencies import CurrentUser
from .tokens import create_access_token

router = APIRouter(prefix="/auth", tags=["Authentication"])

# PIN for authentication - set via environment variable
APP_PIN = os.getenv("APP_PIN", "1234")  # Default for development only

# Hume API credentials for EVI access tokens
HUME_API_KEY = os.getenv("HUME_API_KEY", "")
HUME_SECRET_KEY = os.getenv("HUME_SECRET_KEY", "")
HUME_TOKEN_URL = "https://api.hume.ai/oauth2-cc/token"


class LoginRequest(BaseModel):
    """Login request with PIN."""

    pin: str


class LoginResponse(BaseModel):
    """Login response with access token."""

    access_token: str
    token_type: str = "bearer"


class HumeTokenResponse(BaseModel):
    """Response containing Hume EVI access token."""

    access_token: str
    expires_in: int = 1800  # 30 minutes in seconds


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


@router.get("/hume-token", response_model=HumeTokenResponse)
async def get_hume_token(user: CurrentUser) -> HumeTokenResponse:
    """Get a Hume EVI access token for the authenticated user.

    This endpoint fetches a short-lived access token from Hume's API
    that can be used to connect to the EVI WebSocket. Tokens expire
    after 30 minutes.

    Requires authentication via bearer token.
    """
    # Validate Hume credentials are configured
    if not HUME_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Hume API key not configured",
        )
    if not HUME_SECRET_KEY:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Hume secret key not configured",
        )

    # Request access token from Hume API using async client
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                HUME_TOKEN_URL,
                auth=(HUME_API_KEY, HUME_SECRET_KEY),
                data={"grant_type": "client_credentials"},
            )
    except httpx.RequestError:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to connect to Hume API",
        )

    if response.status_code != 200:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Hume API authentication failed",
        )

    data = response.json()
    return HumeTokenResponse(access_token=data["access_token"])
