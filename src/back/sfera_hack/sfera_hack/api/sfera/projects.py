from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, Field
from typing import Optional, List
import httpx
from datetime import datetime

router = APIRouter(prefix="/projects", tags=["projects"])


# Pydantic models based on the swagger schema
class Project(BaseModel):
    id: int
    full_name: str = Field(
        ..., description="Name of the project", example="My awesome project"
    )
    description: Optional[str] = Field(None, description="Description set by the user")
    created_at: Optional[datetime] = Field(None, description="Repo created timestamp")
    updated_at: Optional[datetime] = Field(None, description="Repo updated timestamp")
    groups: Optional[List["Project"]] = Field(
        None, description="SubProjects list of project groups or group subgroups"
    )


class ResponsePageMeta(BaseModel):
    cursor: Optional[str] = Field(None, description="Cursor for pagination")
    limit: Optional[int] = Field(None, description="Page size")
    total: Optional[int] = Field(None, description="Total number of items")


class ProjectsListResponse(BaseModel):
    data: List[Project]
    page: Optional[ResponsePageMeta] = None
    request_id: Optional[str] = Field(None, description="Unique ID for this request")
    status: Optional[str] = Field(None, description="Response status")


class ErrorResponse(BaseModel):
    error: str
    message: str
    request_id: Optional[str] = None


# Configuration
SFERA_API_BASE_URL = (
    "https://gateway-codemetrics.saas.sferaplatform.ru/app/sourcecode/api/api/v2"
)


def get_auth_token(request: Request) -> str:
    """Get authentication token from cookies"""
    access_token = request.cookies.get("ACCESS_TOKEN")
    if not access_token:
        raise HTTPException(
            status_code=401, detail="Authentication required. Please login first."
        )
    return access_token


@router.get("/", response_model=ProjectsListResponse)
async def list_projects(
    request: Request,
    cursor: Optional[str] = Query(
        None,
        description="cursor of the requested page (received from the previous request)",
    ),
    limit: Optional[int] = Query(
        30, description="page size of results (ignored if cursor is set)"
    ),
    sort: Optional[str] = Query(
        "name",
        description="sorting type of results",
        regex="^(name|created_at|updated_at)$",
    ),
    order: Optional[str] = Query(
        "asc", description="sort order of results", regex="^(asc|desc)$"
    ),
    q: Optional[str] = Query(None, description="filter organizations by name"),
    favorite_projects: Optional[int] = Query(
        None, description="filter favorite projects", alias="favoriteProjects"
    ),
    create_action: Optional[bool] = Query(
        None,
        description="filter projects with sfera.code.project.repo.create available permission",
        alias="createAction",
    ),
):
    """
    Paginated list of projects.
    Datasource: External Sfera API
    """
    try:
        # Get authentication token from cookies
        access_token = get_auth_token(request)

        # Prepare query parameters
        params = {}
        if cursor:
            params["cursor"] = cursor
        if limit:
            params["limit"] = limit
        if sort:
            params["sort"] = sort
        if order:
            params["order"] = order
        if q:
            params["q"] = q
        if favorite_projects is not None:
            params["favoriteProjects"] = favorite_projects
        if create_action is not None:
            params["createAction"] = create_action

        # Prepare headers with authentication
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        # Make request to external Sfera API
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{SFERA_API_BASE_URL}/projects",
                params=params,
                headers=headers,
                timeout=30.0,
            )

            if response.status_code == 200:
                return response.json()
            elif response.status_code == 400:
                raise HTTPException(
                    status_code=400, detail="Bad Request - Invalid parameters"
                )
            elif response.status_code == 403:
                raise HTTPException(
                    status_code=403, detail="Forbidden - Insufficient permissions"
                )
            elif response.status_code == 500:
                raise HTTPException(
                    status_code=500, detail="Internal Server Error - External API error"
                )
            else:
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"External API error: {response.text}",
                )

    except httpx.TimeoutException:
        raise HTTPException(
            status_code=504, detail="Gateway Timeout - External API request timed out"
        )
    except httpx.RequestError as e:
        raise HTTPException(
            status_code=502,
            detail=f"Bad Gateway - Failed to connect to external API: {str(e)}",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")
