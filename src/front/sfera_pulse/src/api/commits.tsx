export interface SimpleCommit {
  message: string;
  author: string;
  created_at: string;
}

export interface LastCommitsResponse {
  commits: SimpleCommit[];
  total?: number;
  request_id?: string;
}

export interface ErrorResponse {
  error: string;
  message: string;
  request_id?: string;
}

import { getApiBaseUrl } from './config';

export class CommitsService {
  private baseUrl = getApiBaseUrl();

  // Helper function to get cookie value
  private getCookie(name: string): string | null {
    const value = document.cookie
      .split('; ')
      .find(row => row.startsWith(`${name}=`))
      ?.split('=')[1];
    return value || null;
  }

  async getLastCommits(
    projectKey: string,
    repoName: string,
    limit?: number,
    rev?: string
  ): Promise<LastCommitsResponse> {
    const params = new URLSearchParams();
    if (limit) params.append('limit', limit.toString());
    if (rev) params.append('rev', rev);

    const url = `${this.baseUrl}/pulse/projects/${projectKey}/repos/${repoName}/last-commits?${params.toString()}`;

    // Get current authentication cookies
    const accessToken = this.getCookie('ACCESS_TOKEN');
    const refreshToken = this.getCookie('REFRESH_TOKEN');

    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      'accept': 'application/json',
    };

    // Add authentication cookies to headers if they exist
    if (accessToken) {
      headers['Cookie'] = `ACCESS_TOKEN=${accessToken}`;
    }
    if (refreshToken) {
      headers['Cookie'] = headers['Cookie']
        ? `${headers['Cookie']}; REFRESH_TOKEN=${refreshToken}`
        : `REFRESH_TOKEN=${refreshToken}`;
    }

    const response = await fetch(url, {
      method: 'GET',
      headers,
      credentials: 'include', // Important for cookies
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({ detail: 'Failed to fetch commits' }));
      throw new Error(errorData.detail || 'Failed to fetch commits');
    }

    return await response.json();
  }
}

export const commitsService = new CommitsService();
