from datetime import datetime
from typing import List, Optional, Dict, Any
from collections import Counter, defaultdict
import base64
import logging
import re
import asyncio

from fastapi import HTTPException, Request
from pydantic import BaseModel, Field

from sfera_hack.connetors.sfera import get_sfera_client


# Shared response models
class AuthorStats(BaseModel):
    author: str = Field(..., description="Author name")
    commit_count: int = Field(..., description="Number of commits by this author")
    percentage: float = Field(..., description="Percentage of total commits")


class CommitPattern(BaseModel):
    pattern: str = Field(..., description="Commit message pattern")
    count: int = Field(..., description="Number of commits matching this pattern")
    percentage: float = Field(..., description="Percentage of total commits")


class CommitStats(BaseModel):
    commit_hash: str = Field(..., description="Commit SHA hash")
    lines_added: int = Field(..., description="Lines added in this commit")
    lines_removed: int = Field(..., description="Lines removed in this commit")
    files_changed: int = Field(..., description="Number of files changed in this commit")
    net_lines_changed: int = Field(..., description="Net lines changed (added - removed)")
    author: str = Field(..., description="Commit author")
    message: str = Field(..., description="Commit message")
    created_at: str = Field(..., description="Commit creation date")


class OverallCommitStats(BaseModel):
    total_commits: int = Field(..., description="Total number of commits")
    total_lines_added: int = Field(..., description="Total lines added across all commits")
    total_lines_removed: int = Field(..., description="Total lines removed across all commits")
    total_files_changed: int = Field(..., description="Total files changed across all commits")
    net_lines_changed: int = Field(..., description="Net lines changed (total added - total removed)")
    average_commit_size: float = Field(..., description="Average lines changed per commit")
    average_changes_per_day: float = Field(..., description="Average lines changed per day")
    average_commits_per_day: float = Field(..., description="Average commits per day")
    average_files_per_commit: float = Field(..., description="Average files changed per commit")
    large_commits_count: int = Field(..., description="Number of large commits (>500 lines)")
    small_commits_count: int = Field(..., description="Number of small commits (≤50 lines)")
    large_commits_percentage: float = Field(..., description="Percentage of large commits")
    small_commits_percentage: float = Field(..., description="Percentage of small commits")


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


async def process_single_commit(
    sfera_client, project_key: str, repo_name: str, commit: Dict[str, Any]
) -> Optional[CommitStats]:
    """Process a single commit to get its diff statistics"""
    commit_hash = commit.get("hash")
    if not commit_hash:
        return None
        
    try:
        # Get diff content for this specific commit
        diff_response = await sfera_client.get_project_commit_diff(
            project_key, repo_name, commit_hash, {"binary": True}
        )
        
        # Parse diff content
        diff_data = diff_response.get("data", {})
        diff_content = ""
        if diff_data.get("content"):
            diff_content = base64.b64decode(diff_data["content"]).decode('utf-8')
        
        # Parse diff statistics
        diff_stats = parse_diff_content(diff_content)
        
        # Get commit author and message
        author_name = commit.get("author", {}).get("name", "")
        if not author_name:
            author_name = commit.get("author", {}).get("email", "Unknown")
        
        commit_message = commit.get("message", "")
        created_at = commit.get("created_at", commit.get("date", ""))
        
        # Create commit statistics
        return CommitStats(
            commit_hash=commit_hash,
            lines_added=diff_stats["lines_added"],
            lines_removed=diff_stats["lines_removed"],
            files_changed=diff_stats["files_changed"],
            net_lines_changed=diff_stats["lines_added"] - diff_stats["lines_removed"],
            author=author_name,
            message=commit_message,
            created_at=created_at
        )
        
    except Exception as e:
        # Log error but return None to continue with other commits
        logging.warning(f"Error getting diff for commit {commit_hash}: {str(e)}")
        return None


def parse_diff_content(diff_content: str) -> Dict[str, Any]:
    """Parse diff content to extract comprehensive statistics"""
    if not diff_content or not diff_content.strip():
        return {
            "lines_added": 0,
            "lines_removed": 0,
            "files_changed": 0,
            "file_types": {},
            "binary_files": [],
            "renamed_files": [],
            "new_files": [],
            "deleted_files": [],
            "modified_files": [],
            "file_changes": [],
            "commits_count": 0
        }
    
    # Handle potential encoding issues
    try:
        if isinstance(diff_content, bytes):
            diff_content = diff_content.decode('utf-8', errors='ignore')
    except (UnicodeDecodeError, AttributeError):
        # If we can't decode, return empty stats
        return {
            "lines_added": 0,
            "lines_removed": 0,
            "files_changed": 0,
            "file_types": {},
            "binary_files": [],
            "renamed_files": [],
            "new_files": [],
            "deleted_files": [],
            "modified_files": [],
            "file_changes": [],
            "commits_count": 0
        }
    
    lines_added = 0
    lines_removed = 0
    files_changed = set()
    file_types = defaultdict(lambda: {"files": set(), "lines_added": 0, "lines_removed": 0})
    binary_files = []
    renamed_files = []
    new_files = []
    deleted_files = []
    modified_files = []
    file_changes = []  # Track changes per file for additional stats
    
    # Count commits by analyzing the diff structure
    commits_count = 1  # Default to 1 commit for individual commit diffs
    
    # Split diff into file sections - handle both unified and git diff formats
    file_sections = re.split(r'^diff --git\s+', diff_content, flags=re.MULTILINE)
    
    # If no git diff format, try unified diff format
    if len(file_sections) == 1:
        file_sections = re.split(r'^diff -u\s+', diff_content, flags=re.MULTILINE)
    
    # If still no sections, try to find any diff-like content
    if len(file_sections) == 1:
        file_sections = re.split(r'^diff\s+', diff_content, flags=re.MULTILINE)
    
    for section in file_sections:
        if not section.strip():
            continue
        
        try:
            # Extract file paths from diff header - handle multiple formats
            file_match = None
            
            # Try git diff format: diff --git a/path b/path
            file_match = re.search(r'^a/(.+?)\s+b/(.+?)$', section, re.MULTILINE)
            
            # If not found, try unified diff format: --- a/path +++ b/path
            if not file_match:
                old_match = re.search(r'^---\s+(.+?)$', section, re.MULTILINE)
                new_match = re.search(r'^\+\+\+\s+(.+?)$', section, re.MULTILINE)
                if old_match and new_match:
                    old_path = old_match.group(1).strip()
                    new_path = new_match.group(1).strip()
                    # Remove a/ and b/ prefixes if present
                    old_path = old_path[2:] if old_path.startswith('a/') else old_path
                    new_path = new_path[2:] if new_path.startswith('b/') else new_path
                    file_match = type('Match', (), {'group': lambda x: old_path if x == 1 else new_path})()
            
            if not file_match:
                continue
                
            old_path = file_match.group(1).strip()
            new_path = file_match.group(2).strip()
            
            # Remove a/ and b/ prefixes if present
            if old_path.startswith('a/'):
                old_path = old_path[2:]
            if new_path.startswith('b/'):
                new_path = new_path[2:]
                
            files_changed.add(new_path)
            
            # Determine file status
            if old_path == "/dev/null" or old_path == "dev/null":
                new_files.append(new_path)
            elif new_path == "/dev/null" or new_path == "dev/null":
                deleted_files.append(old_path)
            elif old_path != new_path:
                renamed_files.append({"old": old_path, "new": new_path})
            else:
                modified_files.append(new_path)
            
            # Check if it's a binary file - improved detection
            is_binary = (
                "Binary files" in section or 
                "GIT binary patch" in section or 
                "binary file" in section.lower() or
                "Binary file" in section or
                "cannot display" in section.lower() or
                "diff --git" in section and "index" in section and ".." in section and "GIT binary patch" in section
            )
            
            if is_binary:
                binary_files.append(new_path)
                continue
            
            # Get file extension
            file_ext = ""
            if '.' in new_path:
                file_ext = new_path.split('.')[-1].lower()
            else:
                file_ext = "no_extension"
            
            # Count lines in this file section (excluding context lines)
            # Count only actual additions and deletions, not context
            # Use more precise regex to avoid counting context lines
            file_lines_added = len(re.findall(r'^\+(?!\+)', section, re.MULTILINE))
            file_lines_removed = len(re.findall(r'^-(?!-)', section, re.MULTILINE))
            
            lines_added += file_lines_added
            lines_removed += file_lines_removed
            
            file_types[file_ext]["files"].add(new_path)
            file_types[file_ext]["lines_added"] += file_lines_added
            file_types[file_ext]["lines_removed"] += file_lines_removed
            
            # Track changes per file
            file_changes.append({
                "file": new_path,
                "lines_added": file_lines_added,
                "lines_removed": file_lines_removed,
                "total_changes": file_lines_added + file_lines_removed
            })
            
        except Exception as e:
            # Log the error but continue processing other sections
            logging.warning(f"Error parsing diff section: {str(e)}")
            continue
    
    return {
        "lines_added": lines_added,
        "lines_removed": lines_removed,
        "files_changed": len(files_changed),
        "file_types": dict(file_types),
        "binary_files": binary_files,
        "renamed_files": renamed_files,
        "new_files": new_files,
        "deleted_files": deleted_files,
        "modified_files": modified_files,
        "file_changes": file_changes,
        "commits_count": commits_count
    }


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


def calculate_overall_stats(commit_stats: List[CommitStats], analysis_period: Dict[str, str]) -> OverallCommitStats:
    """Calculate overall commit statistics"""
    if not commit_stats:
        return OverallCommitStats(
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
    
    # Calculate totals
    total_commits = len(commit_stats)
    total_lines_added = sum(commit.lines_added for commit in commit_stats)
    total_lines_removed = sum(commit.lines_removed for commit in commit_stats)
    total_files_changed = sum(commit.files_changed for commit in commit_stats)
    net_lines_changed = total_lines_added - total_lines_removed
    
    # Calculate averages
    average_commit_size = (total_lines_added + total_lines_removed) / total_commits if total_commits > 0 else 0
    average_files_per_commit = total_files_changed / total_commits if total_commits > 0 else 0
    
    # Calculate daily averages
    try:
        if analysis_period.get("start") != "N/A" and analysis_period.get("end") != "N/A":
            start_date = datetime.strptime(analysis_period["start"], "%Y-%m-%d")
            end_date = datetime.strptime(analysis_period["end"], "%Y-%m-%d")
            days_diff = (end_date - start_date).days + 1  # +1 to include both start and end days
            
            average_changes_per_day = (total_lines_added + total_lines_removed) / days_diff if days_diff > 0 else 0
            average_commits_per_day = total_commits / days_diff if days_diff > 0 else 0
        else:
            average_changes_per_day = 0.0
            average_commits_per_day = 0.0
    except (ValueError, TypeError):
        average_changes_per_day = 0.0
        average_commits_per_day = 0.0
    
    # Count large and small commits
    large_commits_count = sum(1 for commit in commit_stats if (commit.lines_added + commit.lines_removed) > 500)
    small_commits_count = sum(1 for commit in commit_stats if (commit.lines_added + commit.lines_removed) <= 50)
    
    # Calculate percentages
    large_commits_percentage = (large_commits_count / total_commits) * 100 if total_commits > 0 else 0
    small_commits_percentage = (small_commits_count / total_commits) * 100 if total_commits > 0 else 0
    
    return OverallCommitStats(
        total_commits=total_commits,
        total_lines_added=total_lines_added,
        total_lines_removed=total_lines_removed,
        total_files_changed=total_files_changed,
        net_lines_changed=net_lines_changed,
        average_commit_size=round(average_commit_size, 1),
        average_changes_per_day=round(average_changes_per_day, 1),
        average_commits_per_day=round(average_commits_per_day, 1),
        average_files_per_commit=round(average_files_per_commit, 1),
        large_commits_count=large_commits_count,
        small_commits_count=small_commits_count,
        large_commits_percentage=round(large_commits_percentage, 1),
        small_commits_percentage=round(small_commits_percentage, 1)
    )


async def get_commits_data(
    request: Request, 
    project_key: str, 
    repo_name: str, 
    limit: Optional[int] = 500,
    rev: Optional[str] = None
) -> tuple[List[Dict[str, Any]], List[CommitStats], Dict[str, str]]:
    """Get commits data and process them to get detailed statistics"""
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
    response = await sfera_client.get_project_commits(project_key, repo_name, params)

    # Get commits data
    commits_data = response.get("data", [])
    
    if not commits_data:
        return [], [], {"start": "N/A", "end": "N/A"}

    # Get detailed commit statistics by fetching diff content for each commit in parallel
    # Process commits in batches of 20 to avoid overwhelming the API
    batch_size = 50
    commit_stats = []
    
    for i in range(0, len(commits_data), batch_size):
        batch = commits_data[i:i + batch_size]
        
        # Create tasks for parallel processing
        tasks = [
            process_single_commit(sfera_client, project_key, repo_name, commit)
            for commit in batch
        ]
        
        # Execute batch in parallel
        batch_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter out None results and exceptions
        for result in batch_results:
            if isinstance(result, CommitStats):
                commit_stats.append(result)
            elif isinstance(result, Exception):
                logging.warning(f"Exception in parallel processing: {str(result)}")

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

    return commits_data, commit_stats, analysis_period
