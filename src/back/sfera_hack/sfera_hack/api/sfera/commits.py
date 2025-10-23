from fastapi import APIRouter, HTTPException, Query, Request, Path
from pydantic import BaseModel, Field
from typing import Optional, List
import httpx
from datetime import datetime

router = APIRouter(
    prefix="/projects/{projectKey}/repos/{repoName}/commits", tags=["repository"]
)


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


@router.get("/", response_model=ListRepoCommitsResponse)
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

        # Prepare headers with authentication
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        # Make request to external Sfera API
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{SFERA_API_BASE_URL}/projects/{projectKey}/repos/{repoName}/commits",
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
