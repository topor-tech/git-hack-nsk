from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Path, Query, Request
from pydantic import BaseModel, Field

from sfera_hack.connetors.sfera import get_sfera_client

router = APIRouter(prefix="/projects/{projectKey}/repos/{repoName}/pull-requests")


# Pydantic models based on the swagger schema
class SimpleUser(BaseModel):
    email: str = Field(..., description="Unique primary email")
    first_name: Optional[str] = Field(None, description="First name")
    full_name: Optional[str] = Field(None, description="Full name")
    last_name: Optional[str] = Field(None, description="Last name")
    principal_name: Optional[str] = Field(None, description="Principal name")
    username: Optional[str] = Field(None, description="Username")


class Assignee(BaseModel):
    decision: Optional[str] = Field(
        None, description="Decision: pending, approve, reject"
    )
    email: str = Field(..., description="Unique primary email")
    first_name: Optional[str] = Field(None, description="First name")
    full_name: Optional[str] = Field(None, description="Full name")
    last_name: Optional[str] = Field(None, description="Last name")
    principal_name: Optional[str] = Field(None, description="Principal name")
    username: Optional[str] = Field(None, description="Username")


class PullRequest(BaseModel):
    model_config = {"populate_by_name": True}

    id: Optional[int] = Field(None, description="Pull request ID")
    title: str = Field(..., description="Pull request title")
    description: Optional[str] = Field(None, description="Pull request description")
    author: SimpleUser = Field(..., description="Pull request author")
    assignees: Optional[List[Assignee]] = Field(
        None, description="Pull request reviewers"
    )
    source_branch: str = Field(..., description="Source branch name")
    target_branch: str = Field(..., description="Target branch name")
    status: Optional[str] = Field(None, description="Pull request status")
    closed: Optional[bool] = Field(None, description="Is pull request closed")
    created_at: Optional[datetime] = Field(
        None, description="Pull request creation time"
    )
    updated_at: Optional[datetime] = Field(
        None, description="Pull request last update time"
    )
    closed_at: Optional[datetime] = Field(
        None, description="Pull request close time if closed"
    )
    conflicts: Optional[List[str]] = Field(
        None, description="List of pull request conflicts"
    )
    untracked_files: Optional[List[str]] = Field(None, description="Untracked files")


class ResponsePageMeta(BaseModel):
    cursor: Optional[str] = Field(None, description="Cursor for pagination")
    limit: Optional[int] = Field(None, description="Page size")
    total: Optional[int] = Field(None, description="Total number of items")


class PullRequestsListResponse(BaseModel):
    data: List[PullRequest]
    page: Optional[ResponsePageMeta] = None
    request_id: Optional[str] = Field(None, description="Unique ID for this request")
    status: Optional[str] = Field(None, description="Response status")


class PullRequestResponse(BaseModel):
    data: PullRequest
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


@router.get("/", response_model=PullRequestsListResponse)
async def list_project_repo_pull_requests(
    request: Request,
    projectKey: str = Path(
        ..., description="key of the project", example="project-name"
    ),
    repoName: str = Path(
        ..., description="name of the repository", example="repo-name"
    ),
    cursor: Optional[str] = Query(
        None,
        description="cursor of the requested page (received from the previous request)",
    ),
    limit: Optional[int] = Query(30, description="page size of results"),
    sort: Optional[str] = Query(
        None, description="sorting type of results", example="created_at"
    ),
    order: Optional[str] = Query(
        "asc", description="sort order of results", example="desc"
    ),
    prStatus: Optional[str] = Query(
        "all", description="pull requests status to filter out", example="open"
    ),
    q: Optional[str] = Query(
        None, description="filter pull requests by title or id pull request"
    ),
    targetBranch: Optional[str] = Query(
        None, description="pull requests target branch name to filter out"
    ),
    sourceBranch: Optional[str] = Query(
        None, description="pull requests source branch name to filter out"
    ),
    posters: Optional[List[str]] = Query(
        None, description="list of PR posters to filter out (usernames)"
    ),
    author: Optional[str] = Query(
        None, description="author (principal_name) pull requests to filter out"
    ),
    assignees: Optional[List[str]] = Query(
        None, description="list of PR assignees (reviewers) to filter out (usernames)"
    ),
):
    """
    Get an existing repository pull requests list.
    Datasource: DB
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
        if prStatus:
            params["prStatus"] = prStatus
        if q:
            params["q"] = q
        if targetBranch:
            params["targetBranch"] = targetBranch
        if sourceBranch:
            params["sourceBranch"] = sourceBranch
        if posters:
            params["posters"] = posters
        if author:
            params["author"] = author
        if assignees:
            params["assignees"] = assignees

        # Use Sfera API client
        sfera_client = await get_sfera_client(access_token)
        return await sfera_client.get_pull_requests(projectKey, repoName, params)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")


@router.get("/{prId}", response_model=PullRequestResponse)
async def get_project_repo_pull_request(
    request: Request,
    projectKey: str = Path(
        ..., description="key of the project", example="project-name"
    ),
    repoName: str = Path(
        ..., description="name of the repository", example="repo-name"
    ),
    prId: int = Path(..., description="pull request id", example=42),
):
    """
    Get an existing repository pull request.
    Datasource: DB
    """
    try:
        # Get authentication token from cookies
        access_token = get_auth_token(request)

        # Use Sfera API client
        sfera_client = await get_sfera_client(access_token)
        return await sfera_client.get_pull_request(projectKey, repoName, prId)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")
