from datetime import datetime
from typing import List, Optional, Dict, Any
from collections import Counter, defaultdict

from fastapi import APIRouter, HTTPException, Path, Query, Request
from pydantic import BaseModel, Field

from sfera_hack.connetors.sfera import get_sfera_client

router = APIRouter()


# Dashboard response models
class AuthorStats(BaseModel):
    author: str = Field(..., description="Author name")
    commit_count: int = Field(..., description="Number of commits by this author")
    percentage: float = Field(..., description="Percentage of total commits")


class CommitPattern(BaseModel):
    pattern: str = Field(..., description="Commit message pattern")
    count: int = Field(..., description="Number of commits matching this pattern")
    percentage: float = Field(..., description="Percentage of total commits")


class DashboardStats(BaseModel):
    total_commits: int = Field(..., description="Total number of commits analyzed")
    analysis_period: Dict[str, str] = Field(..., description="Start and end dates of analysis")
    top_authors: List[AuthorStats] = Field(..., description="Top authors by commit count")
    commit_patterns: List[CommitPattern] = Field(..., description="Most common commit message patterns")
    daily_activity: Dict[str, int] = Field(..., description="Commits per day")
    hourly_activity: Dict[str, int] = Field(..., description="Commits per hour")
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


def analyze_commit_patterns(commits: List[Dict[str, Any]]) -> List[CommitPattern]:
    """Analyze commit message patterns"""
    patterns = []
    
    for commit in commits:
        message = commit.get("message", "").strip()
        if not message:
            continue
            
        # Extract common patterns
        if message.startswith("feat:"):
            patterns.append("feat: (new features)")
        elif message.startswith("fix:"):
            patterns.append("fix: (bug fixes)")
        elif message.startswith("docs:"):
            patterns.append("docs: (documentation)")
        elif message.startswith("style:"):
            patterns.append("style: (formatting)")
        elif message.startswith("refactor:"):
            patterns.append("refactor: (code refactoring)")
        elif message.startswith("test:"):
            patterns.append("test: (testing)")
        elif message.startswith("chore:"):
            patterns.append("chore: (maintenance)")
        elif "merge" in message.lower():
            patterns.append("merge commits")
        elif "revert" in message.lower():
            patterns.append("revert commits")
        else:
            # Check for other common patterns
            if len(message.split()) == 1:
                patterns.append("single word commits")
            elif message.endswith("."):
                patterns.append("period ending commits")
            else:
                patterns.append("other commits")
    
    # Count patterns and return top ones
    pattern_counts = Counter(patterns)
    total = len(patterns)
    
    result = []
    for pattern, count in pattern_counts.most_common(10):
        result.append(CommitPattern(
            pattern=pattern,
            count=count,
            percentage=round((count / total) * 100, 2) if total > 0 else 0
        ))
    
    return result


def analyze_daily_activity(commits: List[Dict[str, Any]]) -> Dict[str, int]:
    """Analyze commits by day of week"""
    daily_counts = defaultdict(int)
    day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    
    for commit in commits:
        created_at = commit.get("created_at", commit.get("date", ""))
        if created_at:
            try:
                # Parse datetime and get day of week
                if isinstance(created_at, str):
                    dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                else:
                    dt = created_at
                day_name = day_names[dt.weekday()]
                daily_counts[day_name] += 1
            except (ValueError, TypeError):
                continue
    
    return dict(daily_counts)


def analyze_hourly_activity(commits: List[Dict[str, Any]]) -> Dict[str, int]:
    """Analyze commits by hour of day"""
    hourly_counts = defaultdict(int)
    
    for commit in commits:
        created_at = commit.get("created_at", commit.get("date", ""))
        if created_at:
            try:
                # Parse datetime and get hour
                if isinstance(created_at, str):
                    dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                else:
                    dt = created_at
                hour = dt.hour
                hourly_counts[f"{hour:02d}:00"] += 1
            except (ValueError, TypeError):
                continue
    
    return dict(hourly_counts)


@router.get(
    "/projects/{projectKey}/repos/{repoName}/dashboard",
    response_model=DashboardStats,
)
async def get_dashboard(
    request: Request,
    projectKey: str = Path(
        ..., description="key of the project", example="project-name"
    ),
    repoName: str = Path(
        ..., description="name of the repository", example="repo-name"
    ),
    limit: Optional[int] = Query(
        500, description="Number of recent commits to analyze (default: 500, max: 1000)"
    ),
    rev: Optional[str] = Query(
        None,
        description="git rev (commit/branch/tag,commit-ish or any other git revision). Returns commits from default branch by default.",
        example="refs/heads/master, master~, branch@{1}",
    ),
):
    """
    Get dashboard analytics for a project repository.
    Analyzes the last N commits to provide insights about:
    - Top authors by commit count
    - Common commit message patterns
    - Daily and hourly activity patterns
    """
    try:
        # Validate limit
        if limit and (limit < 1 or limit > 1000):
            raise HTTPException(
                status_code=400, detail="Limit must be between 1 and 1000"
            )

        # Get authentication token from cookies
        access_token = get_auth_token(request)

        # Prepare query parameters
        params = {
            "limit": limit or 500,
        }

        if rev:
            params["rev"] = rev

        # Use Sfera API client to get commits
        sfera_client = await get_sfera_client(access_token)
        response = await sfera_client.get_project_commits(projectKey, repoName, params)

        # Get commits data
        commits_data = response.get("data", [])
        total_commits = len(commits_data)
        
        if total_commits == 0:
            return DashboardStats(
                total_commits=0,
                analysis_period={"start": "N/A", "end": "N/A"},
                top_authors=[],
                commit_patterns=[],
                daily_activity={},
                hourly_activity={},
                request_id=response.get("request_id"),
            )

        # Analyze authors
        author_counts = Counter()
        for commit in commits_data:
            author_name = commit.get("author", {}).get("name", "")
            if not author_name:
                author_name = commit.get("author", {}).get("email", "Unknown")
            author_counts[author_name] += 1

        # Create top authors list
        top_authors = []
        for author, count in author_counts.most_common(10):
            percentage = round((count / total_commits) * 100, 2) if total_commits > 0 else 0
            top_authors.append(AuthorStats(
                author=author,
                commit_count=count,
                percentage=percentage
            ))

        # Analyze commit patterns
        commit_patterns = analyze_commit_patterns(commits_data)

        # Analyze daily activity
        daily_activity = analyze_daily_activity(commits_data)

        # Analyze hourly activity
        hourly_activity = analyze_hourly_activity(commits_data)

        # Determine analysis period
        dates = []
        for commit in commits_data:
            created_at = commit.get("created_at", commit.get("date", ""))
            if created_at:
                try:
                    if isinstance(created_at, str):
                        dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                    else:
                        dt = created_at
                    dates.append(dt)
                except (ValueError, TypeError):
                    continue

        analysis_period = {"start": "N/A", "end": "N/A"}
        if dates:
            dates.sort()
            analysis_period = {
                "start": dates[0].strftime("%Y-%m-%d"),
                "end": dates[-1].strftime("%Y-%m-%d")
            }

        return DashboardStats(
            total_commits=total_commits,
            analysis_period=analysis_period,
            top_authors=top_authors,
            commit_patterns=commit_patterns,
            daily_activity=daily_activity,
            hourly_activity=hourly_activity,
            request_id=response.get("request_id"),
        )

    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")
