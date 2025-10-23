from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel

from sfera_hack.connetors.sfera import get_sfera_auth_client

router = APIRouter(prefix="/auth", tags=["authentication"])


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    message: str = "Login successful"


@router.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest, response: Response):
    """
    Authenticate user with Sfera platform and store tokens in cookies.
    """
    try:
        # Use Sfera authentication client
        auth_client = await get_sfera_auth_client()
        auth_data = await auth_client.login(request.username, request.password)

        # Extract tokens from response
        access_token = auth_data.get("access_token")
        refresh_token = auth_data.get("refresh_token")

        if not access_token or not refresh_token:
            raise HTTPException(
                status_code=500,
                detail="Invalid response from authentication service",
            )

        # Set tokens as HTTP-only cookies
        response.set_cookie(
            key="ACCESS_TOKEN",
            value=access_token,
            httponly=True,
            secure=False,  # Set to False for development (HTTP)
            samesite="lax",
            max_age=3600,  # 1 hour
        )

        response.set_cookie(
            key="REFRESH_TOKEN",
            value=refresh_token,
            httponly=True,
            secure=False,  # Set to False for development (HTTP)
            samesite="lax",
            max_age=86400,  # 24 hours
        )

        response.set_cookie(
            key="CHECK_AUTH",
            value="true",
            httponly=True,
            secure=False,  # Set to False for development (HTTP)
            samesite="lax",
            max_age=3600,  # 1 hour
        )

        return LoginResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            message="Login successful",
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
