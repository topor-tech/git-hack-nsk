from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, Field

from sfera_hack.connetors.sfera import get_sfera_client

router = APIRouter()


# Repository model based on swagger definition
class CloneLinks(BaseModel):
    """Clone links for repository"""

    ssh: Optional[str] = Field(None, description="SSH clone URL")
    https: Optional[str] = Field(None, description="HTTPS clone URL")


class RepositoryPermissions(BaseModel):
    """Repository permissions"""

    read: bool = Field(False, description="Read permission")
    write: bool = Field(False, description="Write permission")
    admin: bool = Field(False, description="Admin permission")


class Repository(BaseModel):
    model_config = {"populate_by_name": True}

    name: str = Field(..., description="Unique repository name")
    owner_name: str = Field(..., description="Project key", alias="ownerName")
    description: Optional[str] = Field(None, description="Description set by the owner")
    default_branch: Optional[str] = Field(
        None, description="Default branch name", alias="defaultBranch"
    )
    is_fork: bool = Field(
        False, description="IsFork flag identifying repo as fork", alias="isFork"
    )
    created_at: datetime = Field(
        ..., description="Repo created timestamp", alias="createdAt"
    )
    updated_at: Optional[datetime] = Field(
        None, description="Repo updated timestamp", alias="updatedAt"
    )
    clone_links: Optional[CloneLinks] = Field(
        None, description="Clone links", alias="cloneLinks"
    )
    permissions: Optional[RepositoryPermissions] = Field(
        None, description="Repository permissions"
    )
    topics: Optional[List[str]] = Field(
        None, description="Repo topics (tags) set by owner"
    )
    fork_slug: Optional[str] = Field(None, description="Fork slug", alias="forkSlug")


class ResponsePageMeta(BaseModel):
    """Page metadata for paginated responses"""

    cursor: Optional[str] = Field(None, description="Cursor for next page")
    limit: int = Field(..., description="Page size")
    total: Optional[int] = Field(None, description="Total number of items")


class RepositoriesListResponse(BaseModel):
    data: List[Repository]
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
    "/repositories",
    response_model=RepositoriesListResponse,
)
async def get_available_repositories(
    request: Request,
    project_key: str = Query(
        ...,
        description="Key of the project",
        example="project-name",
    ),
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
        description="Filter repositories by name",
    ),
):
    """
    Get paginated list of repositories for a project.
    Returns repositories with pagination metadata.
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

        # Use Sfera API client to get repositories
        sfera_client = await get_sfera_client(access_token)
        response = await sfera_client.get_repositories(project_key, params)

        # Transform the response
        repositories_data = response.get("data", [])
        repositories = []

        for repo in repositories_data:
            # Create repository using Pydantic's automatic field mapping
            clone_links_data = repo.get("clone_links")
            clone_links = None
            if clone_links_data:
                clone_links = CloneLinks(
                    ssh=clone_links_data.get("ssh"), https=clone_links_data.get("https")
                )

            permissions_data = repo.get("permissions")
            permissions = None
            if permissions_data:
                permissions = RepositoryPermissions(
                    read=permissions_data.get("read", False),
                    write=permissions_data.get("write", False),
                    admin=permissions_data.get("admin", False),
                )

            repo_obj = Repository(
                name=repo.get("name", ""),
                ownerName=repo.get("owner_name", ""),
                description=repo.get("description"),
                defaultBranch=repo.get("default_branch"),
                isFork=repo.get("is_fork", False),
                createdAt=repo.get("created_at"),
                updatedAt=repo.get("updated_at"),
                cloneLinks=clone_links,
                permissions=permissions,
                topics=repo.get("topics"),
                forkSlug=repo.get("fork_slug"),
            )
            repositories.append(repo_obj)

        # Create page metadata
        page_data = response.get("page", {})
        page_meta = ResponsePageMeta(
            cursor=page_data.get("cursor"),
            limit=page_data.get("limit", limit or 30),
            total=page_data.get("total"),
        )

        return RepositoriesListResponse(
            data=repositories,
            page=page_meta,
            request_id=response.get("request_id"),
        )

    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")
