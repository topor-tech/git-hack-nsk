from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, Field

from sfera_hack.connetors.sfera import get_sfera_client

router = APIRouter()


# Project model based on swagger definition
class Project(BaseModel):
    model_config = {"populate_by_name": True}

    id: int = Field(..., description="Project's identifier")
    name: str = Field(..., description="Unique project key", alias="key")
    full_name: str = Field(..., description="Project name")
    description: Optional[str] = Field(None, description="Description set by the user")
    is_public: bool = Field(..., description="Project public visibility flag")
    is_favorite: bool = Field(..., description="Favorite project flag")
    lfs_allow: bool = Field(..., description="Project support lfs")
    created_at: datetime = Field(..., description="Repo created timestamp")
    updated_at: datetime = Field(..., description="Repo updated timestamp")
    parent_id: Optional[int] = Field(
        None, description="Parent group or project identifier"
    )


class ResponsePageMeta(BaseModel):
    """Page metadata for paginated responses"""

    cursor: Optional[str] = Field(None, description="Cursor for next page")
    limit: int = Field(..., description="Page size")
    total: Optional[int] = Field(None, description="Total number of items")


class ProjectsListResponse(BaseModel):
    data: List[Project]
    page: ResponsePageMeta
    request_id: Optional[str] = Field(None, description="Unique ID for this request")


class ErrorResponse(BaseModel):
    error: str
    message: str
    request_id: Optional[str] = None


def get_auth_token(request: Request) -> str:
    """Get authentication token from cookies"""
    access_token = request.cookies.get("ACCESS_TOKEN")
    if not access_token:
        raise HTTPException(
            status_code=401, detail="Authentication required. Please login first."
        )
    return access_token


@router.get(
    "/projects",
    response_model=ProjectsListResponse,
)
async def get_available_projects(
    request: Request,
    cursor: Optional[str] = Query(
        None,
        description="Cursor of the requested page (received from the previous request)",
    ),
    limit: Optional[int] = Query(
        30,
        description="Page size of results (ignored if cursor is set)",
        example=30,
    ),
    sort: Optional[str] = Query(
        "name",
        description="Sorting type of results",
        example="name",
    ),
    order: Optional[str] = Query(
        "asc",
        description="Sort order of results",
        example="asc",
    ),
    q: Optional[str] = Query(
        None,
        description="Filter organizations by name",
    ),
    favorite_projects: Optional[int] = Query(
        None,
        description="Filter favorite projects (1 - show favorite projects only. Empty or 0 - show all projects)",
        alias="favoriteProjects",
    ),
    create_action: Optional[bool] = Query(
        None,
        description="Filter projects with sfera.code.project.repo.create available permission",
        alias="createAction",
    ),
):
    """
    Get paginated list of projects.
    Returns projects with pagination metadata.
    """
    try:
        # Validate sort parameter
        valid_sort_fields = ["name", "created_at", "updated_at"]
        if sort and sort not in valid_sort_fields:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid sort field. Must be one of: {', '.join(valid_sort_fields)}",
            )

        # Validate order parameter
        valid_orders = ["asc", "desc"]
        if order and order not in valid_orders:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid order. Must be one of: {', '.join(valid_orders)}",
            )

        # Validate limit
        if limit and (limit < 1 or limit > 100):
            raise HTTPException(
                status_code=400, detail="Limit must be between 1 and 100"
            )

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

        # Use Sfera API client to get projects
        sfera_client = await get_sfera_client(access_token)
        response = await sfera_client.get_projects(params)

        # Transform the response
        projects_data = response.get("data", [])
        projects = []

        for project in projects_data:
            # Create project using Pydantic's automatic field mapping
            project_obj = Project(
                id=project.get("id"),
                key=project.get("name", ""),
                full_name=project.get("full_name", ""),
                description=project.get("description"),
                is_public=project.get("is_public", False),
                is_favorite=project.get("is_favorite", False),
                lfs_allow=project.get("lfs_allow", False),
                created_at=project.get("created_at"),
                updated_at=project.get("updated_at"),
                parent_id=project.get("parent_id"),
            )
            projects.append(project_obj)

        # Create page metadata
        page_data = response.get("page", {})
        page_meta = ResponsePageMeta(
            cursor=page_data.get("cursor"),
            limit=page_data.get("limit", limit or 30),
            total=page_data.get("total"),
        )

        return ProjectsListResponse(
            data=projects,
            page=page_meta,
            request_id=response.get("request_id"),
        )

    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")
