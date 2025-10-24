from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any, Tuple
from collections import Counter, defaultdict
import logging
from functools import lru_cache

from fastapi import APIRouter, HTTPException, Path, Query, Request
from pydantic import BaseModel, Field

from .shared_utils import (
    get_auth_token, 
    get_commits_data, 
    CommitStats, 
    ErrorResponse
)

router = APIRouter()

# Same models as original file
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
    overall_score: float = Field(..., description="Overall KPI score: weighted average of throughput(500%), cycle_time(20%), wip(15%), quality(25%), activity(15%)")

class KPIBoardStats(BaseModel):
    total_developers: int = Field(..., description="Total number of unique developers who made commits in the analysis period")
    analysis_period: Dict[str, str] = Field(..., description="Start and end dates of the analysis period (YYYY-MM-DD format)")
    developer_kpis: List[DeveloperKPI] = Field(..., description="Complete KPI metrics for each developer, sorted by overall score (highest first)")
    team_averages: Dict[str, float] = Field(..., description="Team average scores: average_throughput, average_cycle_time, average_wip_score, average_quality, average_activity, average_overall")
    top_performers: Dict[str, str] = Field(..., description="Top performing developer names for each category: throughput, cycle_time, quality, activity, overall")
    request_id: Optional[str] = Field(None, description="Unique identifier for this request (currently not used)")


@lru_cache(maxsize=1000)
def parse_datetime_cached(datetime_str: str) -> Optional[datetime]:
    """Cached datetime parsing to avoid repeated parsing of same timestamps"""
    try:
        return datetime.fromisoformat(datetime_str.replace('Z', '+00:00'))
    except (ValueError, TypeError):
        return None


class OptimizedKPICalculator:
    """Optimized KPI calculator that processes all data in single pass"""
    
    def __init__(self, commit_stats: List[CommitStats], analysis_period: Dict[str, str]):
        self.commit_stats = commit_stats
        self.analysis_period = analysis_period
        self.developer_commits = defaultdict(list)
        self.parsed_timestamps = {}
        
        # Pre-process: group commits by developer and parse timestamps once
        self._preprocess_data()
    
    def _preprocess_data(self):
        """Pre-process data: group by developer and parse timestamps once"""
        for commit in self.commit_stats:
            self.developer_commits[commit.author].append(commit)
            
            # Parse and cache timestamp
            if commit.created_at not in self.parsed_timestamps:
                self.parsed_timestamps[commit.created_at] = parse_datetime_cached(commit.created_at)
    
    def calculate_all_kpis(self) -> List[DeveloperKPI]:
        """Calculate all KPIs for all developers in optimized manner"""
        developer_kpis = []
        
        # Process all developers
        for developer, commits in self.developer_commits.items():
            # Calculate all metrics in single pass
            throughput = self._calculate_throughput_optimized(developer, commits)
            cycle_time = self._calculate_cycle_time_optimized(developer, commits)
            wip = self._calculate_wip_optimized(developer, commits)
            quality = self._calculate_quality_optimized(developer, commits)
            activity = self._calculate_activity_optimized(developer, commits)
            
            # Calculate overall score
            overall_score = self._calculate_overall_score(throughput, cycle_time, wip, quality, activity)
            
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
        return developer_kpis
    
    def _calculate_throughput_optimized(self, developer: str, commits: List[CommitStats]) -> DeveloperThroughput:
        """Optimized throughput calculation"""
        if not commits:
            return DeveloperThroughput(
                developer=developer, commits_completed=0, lines_added=0, 
                lines_removed=0, files_changed=0, throughput_score=0.0, productivity_score=0.0
            )
        
        commits_count = len(commits)
        lines_added = sum(c.lines_added for c in commits)
        lines_removed = sum(c.lines_removed for c in commits)
        files_changed = sum(c.files_changed for c in commits)
        
        # Calculate throughput score
        try:
            if (self.analysis_period.get("start") != "N/A" and 
                self.analysis_period.get("end") != "N/A"):
                start_date = datetime.strptime(self.analysis_period["start"], "%Y-%m-%d")
                end_date = datetime.strptime(self.analysis_period["end"], "%Y-%m-%d")
                days_diff = (end_date - start_date).days + 1
                throughput_score = commits_count / days_diff if days_diff > 0 else 0
            else:
                throughput_score = 0.0
        except (ValueError, TypeError):
            throughput_score = 0.0
        
        productivity_score = (lines_added + lines_removed) / commits_count if commits_count > 0 else 0
        
        return DeveloperThroughput(
            developer=developer, commits_completed=commits_count,
            lines_added=lines_added, lines_removed=lines_removed,
            files_changed=files_changed, throughput_score=round(throughput_score, 2),
            productivity_score=round(productivity_score, 2)
        )
    
    def _calculate_cycle_time_optimized(self, developer: str, commits: List[CommitStats]) -> DeveloperCycleTime:
        """Optimized cycle time calculation with single sort"""
        if len(commits) < 2:
            return DeveloperCycleTime(
                developer=developer, average_commit_interval_hours=0.0,
                fastest_commit_interval_hours=0.0, slowest_commit_interval_hours=0.0,
                cycle_time_score=0.0
            )
        
        # Sort commits by creation time (use cached timestamps)
        commits.sort(key=lambda x: self.parsed_timestamps.get(x.created_at) or datetime.min)
        
        intervals = []
        for i in range(1, len(commits)):
            current_time = self.parsed_timestamps.get(commits[i].created_at)
            previous_time = self.parsed_timestamps.get(commits[i-1].created_at)
            
            if current_time and previous_time:
                interval_hours = (current_time - previous_time).total_seconds() / 3600
                intervals.append(interval_hours)
        
        if not intervals:
            return DeveloperCycleTime(
                developer=developer, average_commit_interval_hours=0.0,
                fastest_commit_interval_hours=0.0, slowest_commit_interval_hours=0.0,
                cycle_time_score=0.0
            )
        
        average_interval = sum(intervals) / len(intervals)
        fastest_interval = min(intervals)
        slowest_interval = max(intervals)
        cycle_time_score = 100 / (average_interval + 1) if average_interval > 0 else 0
        
        return DeveloperCycleTime(
            developer=developer, average_commit_interval_hours=round(average_interval, 2),
            fastest_commit_interval_hours=round(fastest_interval, 2),
            slowest_commit_interval_hours=round(slowest_interval, 2),
            cycle_time_score=round(cycle_time_score, 2)
        )
    
    def _calculate_wip_optimized(self, developer: str, commits: List[CommitStats]) -> DeveloperWorkInProgress:
        """Optimized WIP calculation"""
        active_commits = len(commits)
        
        # WIP score calculation
        if active_commits <= 5:
            wip_score = active_commits * 10
        elif active_commits <= 20:
            wip_score = 50 + (active_commits - 5) * 2
        else:
            wip_score = max(0, 80 - (active_commits - 20) * 2)
        
        focus_score = max(0, 100 - active_commits * 2)
        
        return DeveloperWorkInProgress(
            developer=developer, active_commits_count=active_commits,
            concurrent_work_score=round(wip_score, 2), focus_score=round(focus_score, 2)
        )
    
    def _calculate_quality_optimized(self, developer: str, commits: List[CommitStats]) -> DeveloperQualityMetrics:
        """Optimized quality calculation with single pass"""
        if not commits:
            return DeveloperQualityMetrics(
                developer=developer, large_commits_count=0, small_commits_count=0,
                average_commit_size=0.0, quality_score=0.0, consistency_score=0.0
            )
        
        large_commits = 0
        small_commits = 0
        commit_sizes = []
        
        # Single pass through commits
        for commit in commits:
            size = commit.lines_added + commit.lines_removed
            commit_sizes.append(size)
            
            if size > 500:
                large_commits += 1
            elif size <= 50:
                small_commits += 1
        
        average_commit_size = sum(commit_sizes) / len(commit_sizes) if commit_sizes else 0
        
        # Quality score: percentage of medium-sized commits
        medium_commits = len(commits) - large_commits - small_commits
        quality_score = (medium_commits / len(commits)) * 100 if commits else 0
        
        # Consistency score: variance calculation
        if len(commit_sizes) > 1:
            mean_size = sum(commit_sizes) / len(commit_sizes)
            variance = sum((size - mean_size) ** 2 for size in commit_sizes) / len(commit_sizes)
            consistency_score = max(0, 100 - variance / 100)
        else:
            consistency_score = 100.0
        
        return DeveloperQualityMetrics(
            developer=developer, large_commits_count=large_commits,
            small_commits_count=small_commits, average_commit_size=round(average_commit_size, 2),
            quality_score=round(quality_score, 2), consistency_score=round(consistency_score, 2)
        )
    
    def _calculate_activity_optimized(self, developer: str, commits: List[CommitStats]) -> DeveloperActivityPatterns:
        """Optimized activity patterns calculation"""
        if not commits:
            return DeveloperActivityPatterns(
                developer=developer, most_active_day="N/A", most_active_hour="N/A",
                weekend_commits=0, work_hours_commits=0, activity_score=0.0
            )
        
        day_counts = defaultdict(int)
        hour_counts = defaultdict(int)
        weekend_commits = 0
        work_hours_commits = 0
        
        day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        
        # Single pass through commits
        for commit in commits:
            parsed_time = self.parsed_timestamps.get(commit.created_at)
            if not parsed_time:
                continue
                
            day_name = day_names[parsed_time.weekday()]
            hour = parsed_time.hour
            
            day_counts[day_name] += 1
            hour_counts[hour] += 1
            
            # Check if weekend
            if parsed_time.weekday() >= 5:
                weekend_commits += 1
            
            # Check if work hours (9-17)
            if 9 <= hour <= 17:
                work_hours_commits += 1
        
        most_active_day = max(day_counts.items(), key=lambda x: x[1])[0] if day_counts else "N/A"
        most_active_hour = f"{max(hour_counts.items(), key=lambda x: x[1])[0]:02d}:00" if hour_counts else "N/A"
        
        # Activity score calculation
        work_hours_ratio = work_hours_commits / len(commits) if commits else 0
        weekend_ratio = weekend_commits / len(commits) if commits else 0
        activity_score = (work_hours_ratio * 80) + (weekend_ratio * 20)
        
        return DeveloperActivityPatterns(
            developer=developer, most_active_day=most_active_day,
            most_active_hour=most_active_hour, weekend_commits=weekend_commits,
            work_hours_commits=work_hours_commits, activity_score=round(activity_score, 2)
        )
    
    def _calculate_overall_score(self, throughput: DeveloperThroughput, cycle_time: DeveloperCycleTime, 
                               wip: DeveloperWorkInProgress, quality: DeveloperQualityMetrics, 
                               activity: DeveloperActivityPatterns) -> float:
        """Calculate overall KPI score"""
        weights = {'throughput': 5.0, 'cycle_time': 0.20, 'wip': 0.15, 'quality': 0.25, 'activity': 0.15}
        
        overall_score = (
            throughput.throughput_score * weights['throughput'] +
            cycle_time.cycle_time_score * weights['cycle_time'] +
            wip.concurrent_work_score * weights['wip'] +
            quality.quality_score * weights['quality'] +
            activity.activity_score * weights['activity']
        )
        
        return round(overall_score, 2)
    
    def calculate_team_averages_and_top_performers(self, developer_kpis: List[DeveloperKPI]) -> Tuple[Dict[str, float], Dict[str, str]]:
        """Calculate team averages and top performers in single pass"""
        if not developer_kpis:
            return {}, {}
        
        # Initialize accumulators
        total_throughput = total_cycle_time = total_wip = total_quality = total_activity = total_overall = 0
        max_throughput = max_cycle_time = max_quality = max_activity = 0
        top_throughput = top_cycle_time = top_quality = top_activity = ""
        
        # Single pass to calculate all metrics
        for kpi in developer_kpis:
            # Accumulate for averages
            total_throughput += kpi.throughput.throughput_score
            total_cycle_time += kpi.cycle_time.cycle_time_score
            total_wip += kpi.work_in_progress.concurrent_work_score
            total_quality += kpi.quality.quality_score
            total_activity += kpi.activity_patterns.activity_score
            total_overall += kpi.overall_score
            
            # Track top performers
            if kpi.throughput.throughput_score > max_throughput:
                max_throughput = kpi.throughput.throughput_score
                top_throughput = kpi.developer
            
            if kpi.cycle_time.cycle_time_score > max_cycle_time:
                max_cycle_time = kpi.cycle_time.cycle_time_score
                top_cycle_time = kpi.developer
            
            if kpi.quality.quality_score > max_quality:
                max_quality = kpi.quality.quality_score
                top_quality = kpi.developer
            
            if kpi.activity_patterns.activity_score > max_activity:
                max_activity = kpi.activity_patterns.activity_score
                top_activity = kpi.developer
        
        count = len(developer_kpis)
        team_averages = {
            "average_throughput": round(total_throughput / count, 2),
            "average_cycle_time": round(total_cycle_time / count, 2),
            "average_wip_score": round(total_wip / count, 2),
            "average_quality": round(total_quality / count, 2),
            "average_activity": round(total_activity / count, 2),
            "average_overall": round(total_overall / count, 2)
        }
        
        top_performers = {
            "throughput": top_throughput,
            "cycle_time": top_cycle_time,
            "quality": top_quality,
            "activity": top_activity,
            "overall": developer_kpis[0].developer  # Already sorted by overall score
        }
        
        return team_averages, top_performers


@router.get(
    "/projects/{projectKey}/repos/{repoName}/kpi-board-optimized",
    response_model=KPIBoardStats,
)
async def get_kpi_board_optimized(
    request: Request,
    projectKey: str = Path(..., description="key of the project", example="project-name"),
    repoName: str = Path(..., description="name of the repository", example="repo-name"),
    limit: Optional[int] = Query(500, description="Number of recent commits to analyze (default: 500, max: 1000)"),
    rev: Optional[str] = Query(None, description="git rev (commit/branch/tag,commit-ish or any other git revision). Returns commits from default branch by default.", example="refs/heads/master, master~, branch@{1}"),
):
    """
    Optimized KPI board endpoint with improved performance.
    
    Key optimizations:
    1. Pre-processes data once instead of filtering per developer
    2. Caches datetime parsing to avoid repeated parsing
    3. Calculates team averages in single pass
    4. Uses memoization for expensive operations
    5. Reduces time complexity from O(D × C × log C) to O(C × log C + D × C)
    """
    try:
        # Validate limit
        if limit and (limit < 1 or limit > 5000):
            raise HTTPException(status_code=400, detail="Limit must be between 1 and 5000")

        # Get commits data using shared utility
        commits_data, commit_stats, analysis_period = await get_commits_data(
            request, projectKey, repoName, limit, rev
        )
        
        if not commits_data:
            return KPIBoardStats(
                total_developers=0, analysis_period=analysis_period,
                developer_kpis=[], team_averages={}, top_performers={}, request_id=None
            )

        # Use optimized calculator
        calculator = OptimizedKPICalculator(commit_stats, analysis_period)
        developer_kpis = calculator.calculate_all_kpis()
        team_averages, top_performers = calculator.calculate_team_averages_and_top_performers(developer_kpis)
        
        total_developers = len(calculator.developer_commits)

        return KPIBoardStats(
            total_developers=total_developers, analysis_period=analysis_period,
            developer_kpis=developer_kpis, team_averages=team_averages,
            top_performers=top_performers, request_id=None
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")
