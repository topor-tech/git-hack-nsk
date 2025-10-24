from datetime import datetime
from enum import Enum
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Path, Query, Request
from pydantic import BaseModel, Field

from sfera_hack.connetors.sfera import get_sfera_client

router = APIRouter()


class SortType(str, Enum):
    """Sort type for branches"""

    name = "name"
    committed_at = "committed_at"


class SortOrder(str, Enum):
    """Sort order for branches"""

    asc = "asc"
    desc = "desc"


# Simplified branch model for branches endpoint
class SimpleBranch(BaseModel):
    model_config = {"populate_by_name": True}

    name: str = Field(..., description="Branch name")
    is_protected: bool = Field(..., description="Protection flag", alias="is_protected")
    last_commit_message: Optional[str] = Field(None, description="Last commit message")
    last_commit_author: Optional[str] = Field(None, description="Last commit author")
    last_commit_datetime: Optional[datetime] = Field(
        None, description="Last commit datetime"
    )


class BranchesResponse(BaseModel):
    branches: List[SimpleBranch]
    total: Optional[int] = Field(None, description="Total number of branches")
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
    "/projects/{projectKey}/repos/{repoName}/branches",
    response_model=BranchesResponse,
)
async def get_project_branches(
    request: Request,
    projectKey: str = Path(
        ..., description="key of the project", example="project-name"
    ),
    repoName: str = Path(
        ..., description="name of the repository", example="repo-name"
    ),
    sort: Optional[SortType] = Query(
        None, description="sorting type of results", example="name"
    ),
    order: Optional[SortOrder] = Query(
        None, description="sort order of results", example="asc"
    ),
    q: Optional[str] = Query(None, description="filter branches by name"),
    merged: Optional[bool] = Query(None, description="list merged branches"),
    issueName: Optional[str] = Query(
        None,
        description="issue name to find all branches to which the issue entity is linked",
        example="CODE-123, DEV-456",
    ),
    cursor: Optional[str] = Query(
        None,
        description="cursor of the requested page (received from the previous request)",
    ),
    limit: Optional[int] = Query(
        30, description="page size of results (ignored if cursor is set)", example=30
    ),
):
    """
    List project repository branches (all).
    Returns branch information with simplified commit details.
    """
    try:
        # Validate limit
        if limit and (limit < 1 or limit > 5000):
            raise HTTPException(
                status_code=400, detail="Limit must be between 1 and 5000"
            )

        # Get authentication token from cookies
        access_token = get_auth_token(request)

        # Prepare query parameters
        params = {
            "limit": limit or 30,
        }

        if sort:
            params["sort"] = sort.value
        if order:
            params["order"] = order.value
        if q:
            params["q"] = q
        if merged is not None:
            params["merged"] = merged
        if issueName:
            params["issueName"] = issueName
        if cursor:
            params["cursor"] = cursor

        # Use Sfera API client to get branches
        sfera_client = await get_sfera_client(access_token)
        response = await sfera_client.get_project_branches(projectKey, repoName, params)

        # Transform the response to simplified format
        branches_data = response.get("data", [])
        simplified_branches = []

        for branch in branches_data:
            # Filter to keep only unprotected branches
            if branch.get("is_protected", False):
                continue

            # Extract last commit information
            last_commit = branch.get("last_commit", {})
            last_commit_message = last_commit.get("message", "")

            # Extract author name (use name if available, otherwise email)
            author_name = last_commit.get("author", {}).get("name", "")
            if not author_name:
                author_name = last_commit.get("author", {}).get("email", "Unknown")

            # Create simplified branch using Pydantic's automatic field mapping
            simplified_branch = SimpleBranch(
                name=branch.get("name", ""),
                is_protected=branch.get("is_protected", False),
                last_commit_message=last_commit_message,
                last_commit_author=author_name,
                last_commit_datetime=last_commit.get(
                    "created_at", last_commit.get("date", None)
                ),
            )
            simplified_branches.append(simplified_branch)

        return BranchesResponse(
            branches=simplified_branches,
            total=len(simplified_branches),
            request_id=response.get("request_id"),
        )

    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")
