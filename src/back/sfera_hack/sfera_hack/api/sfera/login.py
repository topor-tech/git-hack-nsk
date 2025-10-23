from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel
import httpx

router = APIRouter(prefix="/auth", tags=["authentication"])

# Configuration
SFERA_AUTH_URL = (
    "https://gateway-codemetrics.saas.sferaplatform.ru/app/ppau/api/auth/login"
)


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
        # Prepare login data
        login_data = {"username": request.username, "password": request.password}

        # Make request to Sfera authentication API
        async with httpx.AsyncClient() as client:
            auth_response = await client.post(
                SFERA_AUTH_URL,
                json=login_data,
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
                timeout=30.0,
            )

            if auth_response.status_code == 200:
                auth_data = auth_response.json()

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
                    secure=True,
                    samesite="lax",
                    max_age=3600,  # 1 hour
                )

                response.set_cookie(
                    key="REFRESH_TOKEN",
                    value=refresh_token,
                    httponly=True,
                    secure=True,
                    samesite="lax",
                    max_age=86400,  # 24 hours
                )

                response.set_cookie(
                    key="CHECK_AUTH",
                    value="true",
                    httponly=True,
                    secure=True,
                    samesite="lax",
                    max_age=3600,  # 1 hour
                )

                return LoginResponse(
                    access_token=access_token,
                    refresh_token=refresh_token,
                    message="Login successful",
                )

            elif auth_response.status_code == 401:
                raise HTTPException(status_code=401, detail="Invalid credentials")
            elif auth_response.status_code == 400:
                raise HTTPException(
                    status_code=400, detail="Bad request - Invalid login data"
                )
            else:
                raise HTTPException(
                    status_code=auth_response.status_code,
                    detail=f"Authentication failed: {auth_response.text}",
                )

    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Authentication service timeout")
    except httpx.RequestError as e:
        raise HTTPException(
            status_code=502,
            detail=f"Failed to connect to authentication service: {str(e)}",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
