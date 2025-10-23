from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Path, Query, Request
from pydantic import BaseModel, Field

from sfera_hack.connetors.sfera import get_sfera_client

router = APIRouter()


# Simplified commit model for last commits endpoint
class SimpleCommit(BaseModel):
    model_config = {"populate_by_name": True}

    title: str = Field(..., description="Commit message/title", alias="message")
    author: str = Field(..., description="Author name")
    commit_datetime: datetime = Field(
        ..., description="Commit datetime", alias="created_at"
    )


class LastCommitsResponse(BaseModel):
    commits: List[SimpleCommit]
    total: Optional[int] = Field(None, description="Total number of commits")
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
    "/projects/{projectKey}/repos/{repoName}/last-commits",
    response_model=LastCommitsResponse,
)
async def get_last_commits(
    request: Request,
    projectKey: str = Path(
        ..., description="key of the project", example="project-name"
    ),
    repoName: str = Path(
        ..., description="name of the repository", example="repo-name"
    ),
    limit: Optional[int] = Query(
        10, description="Number of recent commits to return (default: 10, max: 50)"
    ),
    rev: Optional[str] = Query(
        None,
        description="git rev (commit/branch/tag,commit-ish or any other git revision). Returns commits from default branch by default.",
        example="refs/heads/master, master~, branch@{1}",
    ),
):
    """
    Get the last N commits from a project repository with simplified information.
    Returns commit title, author, and datetime.
    """
    try:
        # Validate limit
        if limit and (limit < 1 or limit > 50):
            raise HTTPException(
                status_code=400, detail="Limit must be between 1 and 50"
            )

        # Get authentication token from cookies
        access_token = get_auth_token(request)

        # Prepare query parameters
        params = {
            "limit": limit or 10,
        }

        if rev:
            params["rev"] = rev

        # Use Sfera API client to get commits
        sfera_client = await get_sfera_client(access_token)
        response = await sfera_client.get_project_commits(projectKey, repoName, params)

        # Transform the response to simplified format
        commits_data = response.get("data", [])
        simplified_commits = []

        for commit in commits_data:
            # Extract author name (use name if available, otherwise email)
            author_name = commit.get("author", {}).get("name", "")
            if not author_name:
                author_name = commit.get("author", {}).get("email", "Unknown")

            # Create simplified commit using Pydantic's automatic field mapping
            simplified_commit = SimpleCommit(
                message=commit.get("message", ""),
                author=author_name,
                created_at=commit.get("created_at", commit.get("date", "")),
            )
            simplified_commits.append(simplified_commit)

        return LastCommitsResponse(
            commits=simplified_commits,
            total=len(simplified_commits),
            request_id=response.get("request_id"),
        )

    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")
