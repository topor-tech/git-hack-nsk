import { API_CONFIG } from './config';

// Dashboard API response types
export interface AuthorStats {
  author: string;
  commit_count: number;
  percentage: number;
}

export interface CommitPattern {
  pattern: string;
  count: number;
  percentage: number;
}

export interface DashboardStats {
  total_commits: number;
  analysis_period: {
    start: string;
    end: string;
  };
  top_authors: AuthorStats[];
  commit_patterns: CommitPattern[];
  daily_activity: Record<string, number>;
  hourly_activity: Record<string, number>;
  request_id?: string;
}

export interface DashboardParams {
  limit?: number;
  rev?: string;
}

class DashboardService {
  private baseUrl: string;

  constructor() {
    this.baseUrl = API_CONFIG.BASE_URL;
  }

  async getDashboard(
    projectKey: string,
    repoName: string,
    params: DashboardParams = {}
  ): Promise<DashboardStats> {
    const searchParams = new URLSearchParams();
    
    if (params.limit) {
      searchParams.append('limit', params.limit.toString());
    }
    if (params.rev) {
      searchParams.append('rev', params.rev);
    }

    const queryString = searchParams.toString();
    const url = `${this.baseUrl}/pulse/projects/${encodeURIComponent(projectKey)}/repos/${encodeURIComponent(repoName)}/dashboard${queryString ? `?${queryString}` : ''}`;

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

export const dashboardService = new DashboardService();
