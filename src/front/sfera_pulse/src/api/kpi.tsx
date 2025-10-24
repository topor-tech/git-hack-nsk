import { API_CONFIG } from './config';

export interface DeveloperThroughput {
  developer: string;
  commits_completed: number;
  lines_added: number;
  lines_removed: number;
  files_changed: number;
  throughput_score: number;
  productivity_score: number;
}

export interface DeveloperCycleTime {
  developer: string;
  average_commit_interval_hours: number;
  fastest_commit_interval_hours: number;
  slowest_commit_interval_hours: number;
  cycle_time_score: number;
}

export interface DeveloperWorkInProgress {
  developer: string;
  active_commits_count: number;
  concurrent_work_score: number;
  focus_score: number;
}

export interface DeveloperQualityMetrics {
  developer: string;
  large_commits_count: number;
  small_commits_count: number;
  average_commit_size: number;
  quality_score: number;
  consistency_score: number;
}

export interface DeveloperActivityPatterns {
  developer: string;
  most_active_day: string;
  most_active_hour: string;
  weekend_commits: number;
  work_hours_commits: number;
  activity_score: number;
}

export interface DeveloperKPI {
  developer: string;
  throughput: DeveloperThroughput;
  cycle_time: DeveloperCycleTime;
  work_in_progress: DeveloperWorkInProgress;
  quality: DeveloperQualityMetrics;
  activity_patterns: DeveloperActivityPatterns;
  overall_score: number;
}

export interface KPIBoardStats {
  total_developers: number;
  analysis_period: {
    start: string;
    end: string;
  };
  developer_kpis: DeveloperKPI[];
  team_averages: {
    average_throughput: number;
    average_cycle_time: number;
    average_wip_score: number;
    average_quality: number;
    average_activity: number;
    average_overall: number;
  };
  top_performers: {
    throughput: string;
    cycle_time: string;
    quality: string;
    activity: string;
    overall: string;
  };
  request_id: string | null;
}

export interface KPIBoardParams {
  limit?: number;
  rev?: string;
}

class KPIBoardService {
  private baseUrl: string;

  constructor() {
    this.baseUrl = API_CONFIG.BASE_URL;
  }

  async getKPIBoard(
    projectKey: string,
    repoName: string,
    params: KPIBoardParams = {}
  ): Promise<KPIBoardStats> {
    const searchParams = new URLSearchParams();
    
    if (params.limit) {
      searchParams.append('limit', params.limit.toString());
    }
    if (params.rev) {
      searchParams.append('rev', params.rev);
    }

    const queryString = searchParams.toString();
    const url = `${this.baseUrl}/pulse/projects/${encodeURIComponent(projectKey)}/repos/${encodeURIComponent(repoName)}/kpi-board${queryString ? `?${queryString}` : ''}`;

    const response = await fetch(url, {
      method: 'GET',
      credentials: 'include', // Include cookies for authentication
      headers: {
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
    }

    return await response.json();
  }
}

export const kpiBoardService = new KPIBoardService();
