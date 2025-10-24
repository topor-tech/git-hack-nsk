from typing import List, Optional, Dict, Any
from collections import Counter

from fastapi import APIRouter, HTTPException, Path, Query, Request
from pydantic import BaseModel, Field

from .shared_utils import (
    get_commits_data,
    AuthorStats,
    CommitPattern,
    CommitStats,
    OverallCommitStats,
    analyze_commit_patterns,
    analyze_daily_activity,
    analyze_hourly_activity,
    calculate_overall_stats
)

router = APIRouter()


class DashboardStats(BaseModel):
    total_commits: int = Field(..., description="Total number of commits analyzed")
    analysis_period: Dict[str, str] = Field(..., description="Start and end dates of analysis")
    top_authors: List[AuthorStats] = Field(..., description="Top authors by commit count")
    commit_patterns: List[CommitPattern] = Field(..., description="Most common commit message patterns")
    daily_activity: Dict[str, int] = Field(..., description="Commits per day")
    hourly_activity: Dict[str, int] = Field(..., description="Commits per hour")
    commit_stats: List[CommitStats] = Field(..., description="Detailed statistics for each commit")
    overall_stats: OverallCommitStats = Field(..., description="Overall commit statistics")
    last_commit_hash: Optional[str] = Field(None, description="Hash of the oldest commit")
    request_id: Optional[str] = Field(None, description="Unique ID for this request")




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
        if limit and (limit < 1 or limit > 5000):
            raise HTTPException(
                status_code=400, detail="Limit must be between 1 and 5000"
            )

        # Get commits data using shared utility
        commits_data, commit_stats, analysis_period = await get_commits_data(
            request, projectKey, repoName, limit, rev
        )
        
        total_commits = len(commits_data)
        
        if total_commits == 0:
            empty_overall_stats = OverallCommitStats(
                total_commits=0,
                total_lines_added=0,
                total_lines_removed=0,
                total_files_changed=0,
                net_lines_changed=0,
                average_commit_size=0.0,
                average_changes_per_day=0.0,
                average_commits_per_day=0.0,
                average_files_per_commit=0.0,
                large_commits_count=0,
                small_commits_count=0,
                large_commits_percentage=0.0,
                small_commits_percentage=0.0
            )
            return DashboardStats(
                total_commits=0,
                analysis_period=analysis_period,
                top_authors=[],
                commit_patterns=[],
                daily_activity={},
                hourly_activity={},
                commit_stats=[],
                overall_stats=empty_overall_stats,
                last_commit_hash=None,
                request_id=None,
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

        # Get the oldest commit hash (last commit in the list should be the oldest)
        last_commit_hash = None
        if commits_data:
            last_commit_hash = commits_data[-1].get("hash")

        # Calculate overall commit statistics
        overall_stats = calculate_overall_stats(commit_stats, analysis_period)

        return DashboardStats(
            total_commits=total_commits,
            analysis_period=analysis_period,
            top_authors=top_authors,
            commit_patterns=commit_patterns,
            daily_activity=daily_activity,
            hourly_activity=hourly_activity,
            commit_stats=commit_stats,
            overall_stats=overall_stats,
            last_commit_hash=last_commit_hash,
            request_id=None,
        )

    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")
