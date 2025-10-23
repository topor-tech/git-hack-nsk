from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, Field

from sfera_hack.connetors.sfera import get_sfera_client

router = APIRouter(prefix="/projects")


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


# Configuration is now imported from config.py


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

        # Use Sfera API client
        sfera_client = await get_sfera_client(access_token)
        return await sfera_client.get_projects(params)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")
