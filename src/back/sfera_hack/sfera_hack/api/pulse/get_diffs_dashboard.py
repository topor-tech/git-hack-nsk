from datetime import datetime
import logging
from typing import List, Optional, Dict, Any
from collections import Counter, defaultdict
import base64
import re

from fastapi import APIRouter, HTTPException, Path, Query, Request
from pydantic import BaseModel, Field

from sfera_hack.connetors.sfera import get_sfera_client

router = APIRouter()


# Dashboard response models
class DiffStats(BaseModel):
    total_lines_added: int = Field(..., description="Total lines added across all diffs")
    total_lines_removed: int = Field(..., description="Total lines removed across all diffs")
    total_files_changed: int = Field(..., description="Total number of files changed")
    net_lines_changed: int = Field(..., description="Net lines changed (added - removed)")
    average_changes_per_file: float = Field(..., description="Average changes per file")
    largest_file_changes: int = Field(..., description="Largest number of changes in a single file")
    files_with_most_additions: int = Field(..., description="Number of files with most additions")
    files_with_most_deletions: int = Field(..., description="Number of files with most deletions")
    change_ratio: float = Field(..., description="Ratio of additions to deletions")


class FileTypeStats(BaseModel):
    file_type: str = Field(..., description="File extension or type")
    files_count: int = Field(..., description="Number of files of this type")
    lines_added: int = Field(..., description="Lines added in this file type")
    lines_removed: int = Field(..., description="Lines removed in this file type")
    percentage: float = Field(..., description="Percentage of total changes")


class FileChangeStats(BaseModel):
    new_files: List[str] = Field(..., description="List of newly added files")
    deleted_files: List[str] = Field(..., description="List of deleted files")
    modified_files: List[str] = Field(..., description="List of modified files")
    renamed_files: List[Dict[str, str]] = Field(..., description="List of renamed files with old and new paths")
    binary_files: List[str] = Field(..., description="List of binary files in the diff")


class DiffDashboardStats(BaseModel):
    total_commits: int = Field(..., description="Total number of commits analyzed")
    analysis_period: Dict[str, str] = Field(..., description="Start and end dates of analysis")
    diff_stats: DiffStats = Field(..., description="Overall diff statistics")
    file_type_stats: List[FileTypeStats] = Field(..., description="Statistics by file type")
    file_change_stats: FileChangeStats = Field(..., description="File change statistics")
    large_files: List[str] = Field(..., description="List of large files in diff")
    excluded_files: List[str] = Field(..., description="List of excluded files")
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
    # The diff content can represent:
    # 1. A single commit diff (most common case)
    # 2. A range of commits diff
    # 3. Multiple commits in patch format
    
    commits_count = 0
    
    # Method 1: Look for explicit commit headers (git log --format=fuller format)
    commit_headers = re.findall(r'^commit\s+[a-f0-9]{40}', diff_content, re.MULTILINE)
    if commit_headers:
        commits_count = len(commit_headers)
    else:
        # Method 2: Look for "From" headers (git format-patch format)
        from_headers = re.findall(r'^From\s+[a-f0-9]{40}', diff_content, re.MULTILINE)
        if from_headers:
            commits_count = len(from_headers)
        else:
            # Method 3: Look for commit hash patterns in the content
            # This is less reliable but can catch some cases
            commit_hash_pattern = r'\b[a-f0-9]{40}\b'
            commit_hashes = re.findall(commit_hash_pattern, diff_content)
            unique_hashes = set(commit_hashes)
            
            # Filter out hashes that are likely file hashes (in index lines)
            # vs commit hashes (standalone or in commit headers)
            filtered_hashes = []
            for hash_val in unique_hashes:
                # Skip hashes that appear in index lines (file hashes)
                if not re.search(rf'index\s+{hash_val}', diff_content):
                    filtered_hashes.append(hash_val)
            
            if filtered_hashes:
                commits_count = len(filtered_hashes)
            else:
                # Method 4: Default to 1 commit if no clear commit boundaries found
                # This handles the case where we have a single commit diff
                commits_count = 1
    
    # Split diff into file sections - handle both unified and git diff formats
    # Look for diff headers that start with "diff --git" or "diff -u" or similar
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


def analyze_file_types(file_types_data: Dict[str, Any]) -> List[FileTypeStats]:
    """Analyze file type statistics"""
    total_changes = sum(
        data["lines_added"] + data["lines_removed"] 
        for data in file_types_data.values()
    )
    
    result = []
    for file_type, data in file_types_data.items():
        files_count = len(data["files"])
        lines_added = data["lines_added"]
        lines_removed = data["lines_removed"]
        total_type_changes = lines_added + lines_removed
        
        percentage = round((total_type_changes / total_changes) * 100, 2) if total_changes > 0 else 0
        
        result.append(FileTypeStats(
            file_type=file_type,
            files_count=files_count,
            lines_added=lines_added,
            lines_removed=lines_removed,
            percentage=percentage
        ))
    
    # Sort by total changes (descending)
    result.sort(key=lambda x: x.lines_added + x.lines_removed, reverse=True)
    return result[:15]  # Return top 15 file types


@router.get(
    "/projects/{projectKey}/repos/{repoName}/diffs-dashboard",
    response_model=DiffDashboardStats,
)
async def get_diffs_dashboard(
    request: Request,
    projectKey: str = Path(
        ..., description="key of the project", example="project-name"
    ),
    repoName: str = Path(
        ..., description="name of the repository", example="repo-name"
    ),
    rev: Optional[str]= Query(
        None, description="git rev (commit/branch/tag,commit-ish or any other git revision)", 
        example="refs/heads/master, master~, branch@{1}"
    ),
    until: Optional[str] = Query(
        None, description="git until rev (commit/branch/tag,commit-ish or any other git revision)"
    ),
    binary: Optional[bool] = Query(
        True, description="whether to include binary file changes"
    ),
    path: Optional[str] = Query(
        None, description="file or directory path"
    ),
):
    """
    Get diffs dashboard analytics for a project repository.
    Analyzes diff content to provide insights about:
    - Lines added/removed statistics
    - File type analysis
    - Large and excluded files
    """
    try:
        # Get authentication token from cookies
        access_token = get_auth_token(request)

        # Prepare query parameters
        params = {
            "rev": rev or "HEAD",
        }

        if until:
            params["until"] = until
        if binary is not None:
            params["binary"] = binary
        if path:
            params["path"] = path

        # Use Sfera API client to get diff
        sfera_client = await get_sfera_client(access_token)
        response = await sfera_client.get_project_commits_diff(projectKey, repoName, params)        
        # Get diff data
        diff_data = response.get("data", {})
        
        if not diff_data:
            return DiffDashboardStats(
                total_commits=0,
                analysis_period={"start": "N/A", "end": "N/A"},
                diff_stats=DiffStats(
                    total_lines_added=0,
                    total_lines_removed=0,
                    total_files_changed=0,
                    net_lines_changed=0,
                    average_changes_per_file=0.0,
                    largest_file_changes=0,
                    files_with_most_additions=0,
                    files_with_most_deletions=0,
                    change_ratio=0.0
                ),
                file_type_stats=[],
                file_change_stats=FileChangeStats(
                    new_files=[],
                    deleted_files=[],
                    modified_files=[],
                    renamed_files=[],
                    binary_files=[]
                ),
                large_files=[],
                excluded_files=[],
                request_id=response.get("request_id"),
            )

        # Decode and parse diff content
        diff_content = ""
        if diff_data.get("content"):
            diff_content = base64.b64decode(diff_data["content"]).decode('utf-8')

        # Parse diff statistics
        diff_stats = parse_diff_content(diff_content)
        
        # Calculate overall statistics
        total_lines_added = diff_stats["lines_added"]
        total_lines_removed = diff_stats["lines_removed"]
        total_files_changed = diff_stats["files_changed"]
        net_lines_changed = total_lines_added - total_lines_removed
        average_changes_per_file = (
            (total_lines_added + total_lines_removed) / total_files_changed 
            if total_files_changed > 0 else 0
        )
        
        # Calculate additional statistics
        file_changes = diff_stats.get("file_changes", [])
        largest_file_changes = max([fc["total_changes"] for fc in file_changes], default=0)
        
        # Count files with most additions and deletions
        files_with_most_additions = len([fc for fc in file_changes if fc["lines_added"] > fc["lines_removed"]])
        files_with_most_deletions = len([fc for fc in file_changes if fc["lines_removed"] > fc["lines_added"]])
        
        # Calculate change ratio
        change_ratio = total_lines_added / total_lines_removed if total_lines_removed > 0 else float('inf') if total_lines_added > 0 else 0

        # Analyze file types
        file_type_stats = analyze_file_types(diff_stats["file_types"])

        # Create file change statistics
        file_change_stats = FileChangeStats(
            new_files=diff_stats["new_files"],
            deleted_files=diff_stats["deleted_files"],
            modified_files=diff_stats["modified_files"],
            renamed_files=diff_stats["renamed_files"],
            binary_files=diff_stats["binary_files"]
        )

        # Get large and excluded files
        large_files = diff_data.get("large_files", [])
        excluded_files = diff_data.get("excluded_files", [])

        return DiffDashboardStats(
            total_commits=diff_stats.get("commits_count", 1),  # Use parsed commit count
            analysis_period={"start": "N/A", "end": "N/A"},  # Single point in time
            diff_stats=DiffStats(
                total_lines_added=total_lines_added,
                total_lines_removed=total_lines_removed,
                total_files_changed=total_files_changed,
                net_lines_changed=net_lines_changed,
                average_changes_per_file=round(average_changes_per_file, 2),
                largest_file_changes=largest_file_changes,
                files_with_most_additions=files_with_most_additions,
                files_with_most_deletions=files_with_most_deletions,
                change_ratio=round(change_ratio, 2) if change_ratio != float('inf') else 999.99
            ),
            file_type_stats=file_type_stats,
            file_change_stats=file_change_stats,
            large_files=large_files,
            excluded_files=excluded_files,
            request_id=response.get("request_id"),
        )

    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")
