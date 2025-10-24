from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from collections import Counter, defaultdict
import logging

from fastapi import APIRouter, HTTPException, Path, Query, Request
from pydantic import BaseModel, Field

from .shared_utils import (
    get_auth_token, 
    get_commits_data, 
    CommitStats, 
    ErrorResponse
)

router = APIRouter()


# KPI-specific models for developer metrics
class DeveloperThroughput(BaseModel):
    developer: str = Field(..., description="Developer name")
    commits_completed: int = Field(..., description="Total number of commits completed by the developer in the analysis period")
    lines_added: int = Field(..., description="Total lines of code added across all commits")
    lines_removed: int = Field(..., description="Total lines of code removed across all commits")
    files_changed: int = Field(..., description="Total number of files modified across all commits")
    throughput_score: float = Field(..., description="Throughput score calculated as commits per day (total commits divided by analysis period days)")
    productivity_score: float = Field(..., description="Productivity score calculated as total lines changed (added + removed) divided by number of commits")


class DeveloperCycleTime(BaseModel):
    developer: str = Field(..., description="Developer name")
    average_commit_interval_hours: float = Field(..., description="Average time between consecutive commits in hours (calculated from commit timestamps)")
    fastest_commit_interval_hours: float = Field(..., description="Shortest time interval between any two consecutive commits in hours")
    slowest_commit_interval_hours: float = Field(..., description="Longest time interval between any two consecutive commits in hours")
    cycle_time_score: float = Field(..., description="Cycle time score calculated as 100/(average_interval + 1) - lower intervals get higher scores")


class DeveloperWorkInProgress(BaseModel):
    developer: str = Field(..., description="Developer name")
    active_commits_count: int = Field(..., description="Total number of commits by the developer (used as proxy for concurrent work)")
    concurrent_work_score: float = Field(..., description="WIP score: 0-5 commits = linear increase, 5-20 = moderate increase, >20 = decreasing score")
    focus_score: float = Field(..., description="Focus score calculated as max(0, 100 - active_commits * 2) - lower concurrent work gets higher scores")


class DeveloperQualityMetrics(BaseModel):
    developer: str = Field(..., description="Developer name")
    large_commits_count: int = Field(..., description="Number of commits with >500 total lines changed (added + removed)")
    small_commits_count: int = Field(..., description="Number of commits with ≤50 total lines changed (added + removed)")
    average_commit_size: float = Field(..., description="Average commit size calculated as (lines_added + lines_removed) across all commits")
    quality_score: float = Field(..., description="Quality score calculated as percentage of medium-sized commits (50-500 lines) - higher percentage = better score")
    consistency_score: float = Field(..., description="Consistency score calculated as max(0, 100 - variance/100) - lower variance in commit sizes gets higher scores")


class DeveloperActivityPatterns(BaseModel):
    developer: str = Field(..., description="Developer name")
    most_active_day: str = Field(..., description="Day of the week with the highest number of commits (Monday-Sunday)")
    most_active_hour: str = Field(..., description="Hour of the day with the highest number of commits (00:00-23:00 format)")
    weekend_commits: int = Field(..., description="Total number of commits made on Saturday and Sunday")
    work_hours_commits: int = Field(..., description="Total number of commits made during work hours (9 AM - 5 PM)")
    activity_score: float = Field(..., description="Activity score calculated as (work_hours_ratio * 80) + (weekend_ratio * 20) - higher work hours ratio gets better scores")


class DeveloperKPI(BaseModel):
    developer: str = Field(..., description="Developer name")
    throughput: DeveloperThroughput = Field(..., description="Throughput metrics: commits per day and productivity (lines per commit)")
    cycle_time: DeveloperCycleTime = Field(..., description="Cycle time metrics: time intervals between commits")
    work_in_progress: DeveloperWorkInProgress = Field(..., description="Work in progress metrics: concurrent work tracking and focus scoring")
    quality: DeveloperQualityMetrics = Field(..., description="Quality metrics: commit size patterns and consistency analysis")
    activity_patterns: DeveloperActivityPatterns = Field(..., description="Activity pattern metrics: work schedule and timing analysis")
    overall_score: float = Field(..., description="Overall KPI score: weighted average of throughput(25%), cycle_time(20%), wip(15%), quality(25%), activity(15%)")


class KPIBoardStats(BaseModel):
    total_developers: int = Field(..., description="Total number of unique developers who made commits in the analysis period")
    analysis_period: Dict[str, str] = Field(..., description="Start and end dates of the analysis period (YYYY-MM-DD format)")
    developer_kpis: List[DeveloperKPI] = Field(..., description="Complete KPI metrics for each developer, sorted by overall score (highest first)")
    team_averages: Dict[str, float] = Field(..., description="Team average scores: average_throughput, average_cycle_time, average_wip_score, average_quality, average_activity, average_overall")
    top_performers: Dict[str, str] = Field(..., description="Top performing developer names for each category: throughput, cycle_time, quality, activity, overall")
    request_id: Optional[str] = Field(None, description="Unique identifier for this request (currently not used)")


def calculate_developer_throughput(developer: str, commit_stats: List[CommitStats], analysis_period: Dict[str, str]) -> DeveloperThroughput:
    """Calculate throughput metrics for a developer"""
    developer_commits = [c for c in commit_stats if c.author == developer]
    
    if not developer_commits:
        return DeveloperThroughput(
            developer=developer,
            commits_completed=0,
            lines_added=0,
            lines_removed=0,
            files_changed=0,
            throughput_score=0.0,
            productivity_score=0.0
        )
    
    commits_count = len(developer_commits)
    lines_added = sum(c.lines_added for c in developer_commits)
    lines_removed = sum(c.lines_removed for c in developer_commits)
    files_changed = sum(c.files_changed for c in developer_commits)
    
    # Calculate throughput score (commits per day)
    try:
        if analysis_period.get("start") != "N/A" and analysis_period.get("end") != "N/A":
            start_date = datetime.strptime(analysis_period["start"], "%Y-%m-%d")
            end_date = datetime.strptime(analysis_period["end"], "%Y-%m-%d")
            days_diff = (end_date - start_date).days + 1
            throughput_score = commits_count / days_diff if days_diff > 0 else 0
        else:
            throughput_score = 0.0
    except (ValueError, TypeError):
        throughput_score = 0.0
    
    # Calculate productivity score (lines per commit)
    productivity_score = (lines_added + lines_removed) / commits_count if commits_count > 0 else 0
    
    return DeveloperThroughput(
        developer=developer,
        commits_completed=commits_count,
        lines_added=lines_added,
        lines_removed=lines_removed,
        files_changed=files_changed,
        throughput_score=round(throughput_score, 2),
        productivity_score=round(productivity_score, 2)
    )


def calculate_developer_cycle_time(developer: str, commit_stats: List[CommitStats]) -> DeveloperCycleTime:
    """Calculate cycle time metrics for a developer"""
    developer_commits = [c for c in commit_stats if c.author == developer]
    
    if len(developer_commits) < 2:
        return DeveloperCycleTime(
            developer=developer,
            average_commit_interval_hours=0.0,
            fastest_commit_interval_hours=0.0,
            slowest_commit_interval_hours=0.0,
            cycle_time_score=0.0
        )
    
    # Sort commits by creation time
    developer_commits.sort(key=lambda x: x.created_at)
    
    intervals = []
    for i in range(1, len(developer_commits)):
        try:
            current_time = datetime.fromisoformat(developer_commits[i].created_at.replace('Z', '+00:00'))
            previous_time = datetime.fromisoformat(developer_commits[i-1].created_at.replace('Z', '+00:00'))
            interval_hours = (current_time - previous_time).total_seconds() / 3600
            intervals.append(interval_hours)
        except (ValueError, TypeError):
            continue
    
    if not intervals:
        return DeveloperCycleTime(
            developer=developer,
            average_commit_interval_hours=0.0,
            fastest_commit_interval_hours=0.0,
            slowest_commit_interval_hours=0.0,
            cycle_time_score=0.0
        )
    
    average_interval = sum(intervals) / len(intervals)
    fastest_interval = min(intervals)
    slowest_interval = max(intervals)
    
    # Cycle time score: lower is better (inverse relationship)
    cycle_time_score = 100 / (average_interval + 1) if average_interval > 0 else 0
    
    return DeveloperCycleTime(
        developer=developer,
        average_commit_interval_hours=round(average_interval, 2),
        fastest_commit_interval_hours=round(fastest_interval, 2),
        slowest_commit_interval_hours=round(slowest_interval, 2),
        cycle_time_score=round(cycle_time_score, 2)
    )


def calculate_developer_wip(developer: str, commit_stats: List[CommitStats]) -> DeveloperWorkInProgress:
    """Calculate work in progress metrics for a developer"""
    developer_commits = [c for c in commit_stats if c.author == developer]
    
    # For WIP, we'll use the number of commits as a proxy for concurrent work
    # In a real scenario, you'd track actual work items
    active_commits = len(developer_commits)
    
    # WIP score: moderate number of concurrent work is good
    # Too few = not productive, too many = unfocused
    if active_commits <= 5:
        wip_score = active_commits * 10  # Linear increase for low numbers
    elif active_commits <= 20:
        wip_score = 50 + (active_commits - 5) * 2  # Slower increase
    else:
        wip_score = max(0, 80 - (active_commits - 20) * 2)  # Decrease for too many
    
    # Focus score: lower concurrent work is better
    focus_score = max(0, 100 - active_commits * 2)
    
    return DeveloperWorkInProgress(
        developer=developer,
        active_commits_count=active_commits,
        concurrent_work_score=round(wip_score, 2),
        focus_score=round(focus_score, 2)
    )


def calculate_developer_quality(developer: str, commit_stats: List[CommitStats]) -> DeveloperQualityMetrics:
    """Calculate quality metrics for a developer"""
    developer_commits = [c for c in commit_stats if c.author == developer]
    
    if not developer_commits:
        return DeveloperQualityMetrics(
            developer=developer,
            large_commits_count=0,
            small_commits_count=0,
            average_commit_size=0.0,
            quality_score=0.0,
            consistency_score=0.0
        )
    
    large_commits = sum(1 for c in developer_commits if (c.lines_added + c.lines_removed) > 500)
    small_commits = sum(1 for c in developer_commits if (c.lines_added + c.lines_removed) <= 50)
    
    commit_sizes = [(c.lines_added + c.lines_removed) for c in developer_commits]
    average_commit_size = sum(commit_sizes) / len(commit_sizes) if commit_sizes else 0
    
    # Quality score: balanced approach to commit sizes
    # Prefer medium-sized commits (50-500 lines)
    medium_commits = len(developer_commits) - large_commits - small_commits
    quality_score = (medium_commits / len(developer_commits)) * 100 if developer_commits else 0
    
    # Consistency score: lower variance is better
    if len(commit_sizes) > 1:
        mean_size = sum(commit_sizes) / len(commit_sizes)
        variance = sum((size - mean_size) ** 2 for size in commit_sizes) / len(commit_sizes)
        consistency_score = max(0, 100 - variance / 100)  # Normalize variance
    else:
        consistency_score = 100.0
    
    return DeveloperQualityMetrics(
        developer=developer,
        large_commits_count=large_commits,
        small_commits_count=small_commits,
        average_commit_size=round(average_commit_size, 2),
        quality_score=round(quality_score, 2),
        consistency_score=round(consistency_score, 2)
    )


def calculate_developer_activity_patterns(developer: str, commit_stats: List[CommitStats]) -> DeveloperActivityPatterns:
    """Calculate activity pattern metrics for a developer"""
    developer_commits = [c for c in commit_stats if c.author == developer]
    
    if not developer_commits:
        return DeveloperActivityPatterns(
            developer=developer,
            most_active_day="N/A",
            most_active_hour="N/A",
            weekend_commits=0,
            work_hours_commits=0,
            activity_score=0.0
        )
    
    # Analyze by day of week
    day_counts = defaultdict(int)
    hour_counts = defaultdict(int)
    weekend_commits = 0
    work_hours_commits = 0
    
    day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    
    for commit in developer_commits:
        try:
            created_at = datetime.fromisoformat(commit.created_at.replace('Z', '+00:00'))
            day_name = day_names[created_at.weekday()]
            hour = created_at.hour
            
            day_counts[day_name] += 1
            hour_counts[hour] += 1
            
            # Check if weekend
            if created_at.weekday() >= 5:  # Saturday = 5, Sunday = 6
                weekend_commits += 1
            
            # Check if work hours (9-17)
            if 9 <= hour <= 17:
                work_hours_commits += 1
                
        except (ValueError, TypeError):
            continue
    
    most_active_day = max(day_counts.items(), key=lambda x: x[1])[0] if day_counts else "N/A"
    most_active_hour = f"{max(hour_counts.items(), key=lambda x: x[1])[0]:02d}:00" if hour_counts else "N/A"
    
    # Activity score: balance between work hours and weekend work
    work_hours_ratio = work_hours_commits / len(developer_commits) if developer_commits else 0
    weekend_ratio = weekend_commits / len(developer_commits) if developer_commits else 0
    
    # Higher score for more work hours, moderate weekend work is okay
    activity_score = (work_hours_ratio * 80) + (weekend_ratio * 20)
    
    return DeveloperActivityPatterns(
        developer=developer,
        most_active_day=most_active_day,
        most_active_hour=most_active_hour,
        weekend_commits=weekend_commits,
        work_hours_commits=work_hours_commits,
        activity_score=round(activity_score, 2)
    )


def calculate_overall_kpi_score(throughput: DeveloperThroughput, cycle_time: DeveloperCycleTime, 
                              wip: DeveloperWorkInProgress, quality: DeveloperQualityMetrics, 
                              activity: DeveloperActivityPatterns) -> float:
    """Calculate overall KPI score for a developer"""
    # Weighted average of all metrics
    weights = {
        'throughput': 0.25,
        'cycle_time': 0.20,
        'wip': 0.15,
        'quality': 0.25,
        'activity': 0.15
    }
    
    overall_score = (
        throughput.throughput_score * weights['throughput'] +
        cycle_time.cycle_time_score * weights['cycle_time'] +
        wip.concurrent_work_score * weights['wip'] +
        quality.quality_score * weights['quality'] +
        activity.activity_score * weights['activity']
    )
    
    return round(overall_score, 2)


@router.get(
    "/projects/{projectKey}/repos/{repoName}/kpi-board",
    response_model=KPIBoardStats,
)
async def get_kpi_board(
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
    Get comprehensive KPI board analytics for a project repository.
    
    This endpoint analyzes developer performance across five key metrics:
    
    **THROUGHPUT METRICS:**
    - Commits completed: Total commits by developer in analysis period
    - Lines added/removed: Total code changes across all commits
    - Files changed: Total files modified across all commits
    - Throughput score: Commits per day (commits ÷ analysis period days)
    - Productivity score: Lines per commit ((lines_added + lines_removed) ÷ commits)
    
    **CYCLE TIME METRICS:**
    - Average commit interval: Mean time between consecutive commits (hours)
    - Fastest/slowest intervals: Min/max time between consecutive commits
    - Cycle time score: 100/(average_interval + 1) - lower intervals get higher scores
    
    **WORK IN PROGRESS METRICS:**
    - Active commits count: Total commits (proxy for concurrent work)
    - Concurrent work score: 0-5 commits = linear increase, 5-20 = moderate, >20 = decreasing
    - Focus score: max(0, 100 - active_commits * 2) - lower concurrent work = higher focus
    
    **QUALITY METRICS:**
    - Large commits: Commits with >500 total lines changed
    - Small commits: Commits with ≤50 total lines changed
    - Average commit size: Mean lines changed per commit
    - Quality score: Percentage of medium-sized commits (50-500 lines)
    - Consistency score: max(0, 100 - variance/100) - lower variance = higher consistency
    
    **ACTIVITY PATTERN METRICS:**
    - Most active day/hour: Peak activity timing
    - Weekend commits: Commits on Saturday/Sunday
    - Work hours commits: Commits during 9 AM - 5 PM
    - Activity score: (work_hours_ratio × 80) + (weekend_ratio × 20)
    
    **OVERALL SCORING:**
    Weighted average: Throughput(25%) + Cycle Time(20%) + WIP(15%) + Quality(25%) + Activity(15%)
    
    Returns team averages, top performers, and individual developer KPIs sorted by overall score.
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
        
        if not commits_data:
            return KPIBoardStats(
                total_developers=0,
                analysis_period=analysis_period,
                developer_kpis=[],
                team_averages={},
                top_performers={},
                request_id=None
            )

        # Get unique developers
        developers = list(set(commit.author for commit in commit_stats))
        total_developers = len(developers)
        
        # Calculate KPI metrics for each developer
        developer_kpis = []
        
        for developer in developers:
            # Calculate all metrics
            throughput = calculate_developer_throughput(developer, commit_stats, analysis_period)
            cycle_time = calculate_developer_cycle_time(developer, commit_stats)
            wip = calculate_developer_wip(developer, commit_stats)
            quality = calculate_developer_quality(developer, commit_stats)
            activity = calculate_developer_activity_patterns(developer, commit_stats)
            
            # Calculate overall score
            overall_score = calculate_overall_kpi_score(throughput, cycle_time, wip, quality, activity)
            
            developer_kpi = DeveloperKPI(
                developer=developer,
                throughput=throughput,
                cycle_time=cycle_time,
                work_in_progress=wip,
                quality=quality,
                activity_patterns=activity,
                overall_score=overall_score
            )
            
            developer_kpis.append(developer_kpi)
        
        # Sort by overall score
        developer_kpis.sort(key=lambda x: x.overall_score, reverse=True)
        
        # Calculate team averages
        if developer_kpis:
            team_averages = {
                "average_throughput": sum(d.throughput.throughput_score for d in developer_kpis) / len(developer_kpis),
                "average_cycle_time": sum(d.cycle_time.cycle_time_score for d in developer_kpis) / len(developer_kpis),
                "average_wip_score": sum(d.work_in_progress.concurrent_work_score for d in developer_kpis) / len(developer_kpis),
                "average_quality": sum(d.quality.quality_score for d in developer_kpis) / len(developer_kpis),
                "average_activity": sum(d.activity_patterns.activity_score for d in developer_kpis) / len(developer_kpis),
                "average_overall": sum(d.overall_score for d in developer_kpis) / len(developer_kpis)
            }
            
            # Round averages
            team_averages = {k: round(v, 2) for k, v in team_averages.items()}
            
            # Find top performers
            top_performers = {
                "throughput": max(developer_kpis, key=lambda x: x.throughput.throughput_score).developer,
                "cycle_time": max(developer_kpis, key=lambda x: x.cycle_time.cycle_time_score).developer,
                "quality": max(developer_kpis, key=lambda x: x.quality.quality_score).developer,
                "activity": max(developer_kpis, key=lambda x: x.activity_patterns.activity_score).developer,
                "overall": developer_kpis[0].developer  # Already sorted by overall score
            }
        else:
            team_averages = {}
            top_performers = {}

        return KPIBoardStats(
            total_developers=total_developers,
            analysis_period=analysis_period,
            developer_kpis=developer_kpis,
            team_averages=team_averages,
            top_performers=top_performers,
            request_id=None
        )

    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")
