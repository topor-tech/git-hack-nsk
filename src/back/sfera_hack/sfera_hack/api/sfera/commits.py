from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Path, Query, Request
from pydantic import BaseModel, Field

from sfera_hack.connetors.sfera import get_sfera_client

router = APIRouter()


# Pydantic models based on the swagger schema
class AuthorInfo(BaseModel):
    name: str = Field(..., description="Author name")
    email: str = Field(..., description="Author email")


class Commit(BaseModel):
    model_config = {"populate_by_name": True}

    id: str = Field(..., description="Commit hash", alias="hash")
    message: str = Field(..., description="Commit message")
    author: AuthorInfo = Field(..., description="Commit author")
    committer: AuthorInfo = Field(..., description="Commit committer")
    date: datetime = Field(..., description="Commit date", alias="created_at")
    parents: Optional[List[str]] = Field(None, description="Parent commit hashes")
    tree: Optional[str] = Field(None, description="Tree hash")
    url: Optional[str] = Field(None, description="Commit URL")
    tag_names: Optional[List[str]] = Field(None, description="Tag names")
    Tags: Optional[List[str]] = Field(None, description="Tags")
    branch_names: Optional[List[str]] = Field(None, description="Branch names")


class ResponsePageMeta(BaseModel):
    cursor: Optional[str] = Field(None, description="Cursor for pagination")
    limit: Optional[int] = Field(None, description="Page size")
    total: Optional[int] = Field(None, description="Total number of items")


class ListRepoCommitsResponse(BaseModel):
    data: List[Commit]
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


@router.get(
    "/projects/{projectKey}/repos/{repoName}/commits",
    response_model=ListRepoCommitsResponse,
)
async def list_project_repo_commits(
    request: Request,
    projectKey: str = Path(
        ..., description="key of the project", example="project-name"
    ),
    repoName: str = Path(
        ..., description="name of the repository", example="repo-name"
    ),
    ref: Optional[str] = Query(
        None, description="DEPRECATED!!! use `rev` parameter instead."
    ),
    rev: Optional[str] = Query(
        None,
        description="git rev (commit/branch/tag,commit-ish or any other git revision). Returns all commits by default.",
        example="refs/heads/master, master~, branch@{1}",
    ),
    until: Optional[str] = Query(
        None,
        description="git until rev (commit/branch/tag,commit-ish or any other git revision). See git log A..B.",
        example="refs/heads/master",
    ),
    author: Optional[str] = Query(None, description="commit author", example="goblin"),
    committer: Optional[str] = Query(
        None, description="committer of the commit", example="goblin"
    ),
    cursor: Optional[str] = Query(
        None,
        description="cursor of the requested page (received from the previous request)",
    ),
    limit: Optional[int] = Query(
        30, description="page size of results (ignored if cursor is set)"
    ),
    before: Optional[str] = Query(
        None,
        description="show commits older than a specific date.",
        example="2025-03-24T12:34:56Z",
    ),
    after: Optional[str] = Query(
        None,
        description="show commits more recent than a specific date.",
        example="2025-03-24T12:34:56Z",
    ),
    refType: Optional[str] = Query(
        None,
        description="reference type ('refs/tag/' or 'refs/heads/')",
        example="refs/heads/",
    ),
    path: Optional[str] = Query(
        None,
        description="file or directory path",
        example="file.txt, folder/path, full/folder/file.txt (path should be provided without leading slash '/')",
    ),
    fullHistory: Optional[bool] = Query(
        False,
        description="show full history incl. all merge commits",
    ),
):
    """
    Paginated list of a project repo commits.
    Datasource: Git
    """
    try:
        # Get authentication token from cookies
        access_token = get_auth_token(request)

        # Prepare query parameters
        params = {}
        if ref:
            params["ref"] = ref
        if rev:
            params["rev"] = rev
        if until:
            params["until"] = until
        if author:
            params["author"] = author
        if committer:
            params["committer"] = committer
        if cursor:
            params["cursor"] = cursor
        if limit:
            params["limit"] = limit
        if before:
            params["before"] = before
        if after:
            params["after"] = after
        if refType:
            params["refType"] = refType
        if path:
            params["path"] = path
        if fullHistory is not None:
            params["fullHistory"] = fullHistory

        # Use Sfera API client
        sfera_client = await get_sfera_client(access_token)
        return await sfera_client.get_project_commits(projectKey, repoName, params)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")
