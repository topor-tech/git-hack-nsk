"""
Benchmark script to compare original vs optimized KPI board performance
"""
import time
import random
from datetime import datetime, timedelta
from typing import List
from dataclasses import dataclass

# Mock data structures
@dataclass
class MockCommitStats:
    author: str
    created_at: str
    lines_added: int
    lines_removed: int
    files_changed: int

def generate_mock_data(num_developers: int, commits_per_developer: int) -> List[MockCommitStats]:
    """Generate mock commit data for benchmarking"""
    developers = [f"developer_{i}" for i in range(num_developers)]
    commits = []
    
    base_time = datetime.now() - timedelta(days=30)
    
    for dev in developers:
        for i in range(commits_per_developer):
            # Random commit time within last 30 days
            commit_time = base_time + timedelta(
                days=random.randint(0, 30),
                hours=random.randint(0, 23),
                minutes=random.randint(0, 59)
            )
            
            commit = MockCommitStats(
                author=dev,
                created_at=commit_time.isoformat() + "Z",
                lines_added=random.randint(10, 500),
                lines_removed=random.randint(0, 100),
                files_changed=random.randint(1, 10)
            )
            commits.append(commit)
    
    return commits

def benchmark_original_algorithm(commits: List[MockCommitStats], analysis_period: dict):
    """Simulate original algorithm performance"""
    start_time = time.time()
    
    # Simulate original algorithm complexity
    developers = list(set(commit.author for commit in commits))
    
    for developer in developers:
        # Filter commits for developer (O(C) operation)
        developer_commits = [c for c in commits if c.author == developer]
        
        # Sort commits (O(C log C) operation)
        developer_commits.sort(key=lambda x: x.created_at)
        
        # Simulate processing each commit multiple times
        for commit in developer_commits:
            # Simulate datetime parsing (expensive operation)
            datetime.fromisoformat(commit.created_at.replace('Z', '+00:00'))
            
            # Simulate multiple metric calculations
            _ = commit.lines_added + commit.lines_removed
            _ = commit.files_changed
    
    # Simulate team averages calculation (multiple passes)
    for metric in ['throughput', 'cycle_time', 'wip', 'quality', 'activity']:
        for developer in developers:
            pass  # Simulate metric calculation
    
    end_time = time.time()
    return end_time - start_time

def benchmark_optimized_algorithm(commits: List[MockCommitStats], analysis_period: dict):
    """Simulate optimized algorithm performance"""
    start_time = time.time()
    
    # Pre-process data once (O(C) operation)
    developer_commits = {}
    parsed_timestamps = {}
    
    for commit in commits:
        if commit.author not in developer_commits:
            developer_commits[commit.author] = []
        developer_commits[commit.author].append(commit)
        
        # Parse timestamp once and cache
        if commit.created_at not in parsed_timestamps:
            parsed_timestamps[commit.created_at] = datetime.fromisoformat(
                commit.created_at.replace('Z', '+00:00')
            )
    
    # Single sort of all commits (O(C log C) operation)
    all_commits_sorted = sorted(commits, key=lambda x: parsed_timestamps[x.created_at])
    
    # Process each developer (O(D × C) operation)
    for developer, dev_commits in developer_commits.items():
        # Single pass through commits
        for commit in dev_commits:
            # Use cached timestamp
            _ = parsed_timestamps[commit.created_at]
            
            # Single calculation per commit
            _ = commit.lines_added + commit.lines_removed
            _ = commit.files_changed
    
    # Single pass team averages calculation
    for developer in developer_commits.keys():
        pass  # Simulate single-pass calculation
    
    end_time = time.time()
    return end_time - start_time

def run_benchmark():
    """Run performance benchmark"""
    print("KPI Board Performance Benchmark")
    print("=" * 50)
    
    test_cases = [
        (10, 100),   # Small: 10 developers, 100 commits each
        (25, 200),   # Medium: 25 developers, 200 commits each  
        (50, 500),   # Large: 50 developers, 500 commits each
        (100, 1000), # Very Large: 100 developers, 1000 commits each
    ]
    
    analysis_period = {"start": "2024-01-01", "end": "2024-01-31"}
    
    for num_devs, commits_per_dev in test_cases:
        print(f"\nTest Case: {num_devs} developers, {commits_per_dev} commits each")
        print(f"Total commits: {num_devs * commits_per_dev:,}")
        
        # Generate mock data
        commits = generate_mock_data(num_devs, commits_per_dev)
        
        # Benchmark original algorithm
        original_time = benchmark_original_algorithm(commits, analysis_period)
        
        # Benchmark optimized algorithm  
        optimized_time = benchmark_optimized_algorithm(commits, analysis_period)
        
        # Calculate speedup
        speedup = original_time / optimized_time if optimized_time > 0 else float('inf')
        
        print(f"Original algorithm:  {original_time:.4f}s")
        print(f"Optimized algorithm: {optimized_time:.4f}s")
        print(f"Speedup: {speedup:.2f}x")
        print(f"Time saved: {((original_time - optimized_time) / original_time * 100):.1f}%")

if __name__ == "__main__":
    run_benchmark()
