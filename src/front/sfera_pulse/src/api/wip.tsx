export interface WIPBranch {
  name: string;
  is_protected: boolean;
  last_commit_message?: string;
  last_commit_author?: string;
  last_commit_datetime?: string;
}

export interface WIPBranchesResponse {
  branches: WIPBranch[];
  total?: number;
  request_id?: string;
}

export interface ErrorResponse {
  error: string;
  message: string;
  request_id?: string;
}

import { getApiBaseUrl } from './config';

export class WIPService {
  private baseUrl = getApiBaseUrl();

  // Helper function to get cookie value
  private getCookie(name: string): string | null {
    const value = document.cookie
      .split('; ')
      .find(row => row.startsWith(`${name}=`))
      ?.split('=')[1];
    return value || null;
  }

  async getWIPBranches(
    projectKey: string,
    repoName: string,
    limit?: number,
    sort?: string,
    order?: string,
    q?: string,
    merged?: boolean,
    issueName?: string,
    cursor?: string
  ): Promise<WIPBranchesResponse> {
    const params = new URLSearchParams();
    if (limit) params.append('limit', limit.toString());
    if (sort) params.append('sort', sort);
    if (order) params.append('order', order);
    if (q) params.append('q', q);
    if (merged !== undefined) params.append('merged', merged.toString());
    if (issueName) params.append('issueName', issueName);
    if (cursor) params.append('cursor', cursor);

    const url = `${this.baseUrl}/pulse/projects/${projectKey}/repos/${repoName}/branches?${params.toString()}`;

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
      const errorData = await response.json().catch(() => ({ detail: 'Failed to fetch WIP branches' }));
      throw new Error(errorData.detail || 'Failed to fetch WIP branches');
    }

    const result = await response.json();
    return result;
  }
}

export const wipService = new WIPService();
