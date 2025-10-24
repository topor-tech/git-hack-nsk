export interface Repository {
  id: number;
  name: string;
  full_name: string;
  description: string;
  created_at: string;
  updated_at: string;
}

export interface RepositoriesResponse {
  data: Repository[];
  page: any;
  request_id: string;
  status: string;
}

export interface ErrorResponse {
  error: string;
  message: string;
  request_id?: string;
}

import { getApiBaseUrl } from './config';

export class RepositoriesService {
  private baseUrl = getApiBaseUrl();

  // Helper function to get cookie value
  private getCookie(name: string): string | null {
    const value = document.cookie
      .split('; ')
      .find(row => row.startsWith(`${name}=`))
      ?.split('=')[1];
    return value || null;
  }

  async getRepositories(
    projectKey: string,
    limit?: number,
    sort?: string,
    order?: string
  ): Promise<RepositoriesResponse> {
    const params = new URLSearchParams();
    params.append('project_key', projectKey);
    if (limit) params.append('limit', limit.toString());
    if (sort) params.append('sort', sort);
    if (order) params.append('order', order);

    const url = `${this.baseUrl}/pulse/repositories?${params.toString()}`;

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
      const errorData = await response.json().catch(() => ({ detail: 'Failed to fetch repositories' }));
      throw new Error(errorData.detail || 'Failed to fetch repositories');
    }

    const result = await response.json();
    return result;
  }
}

export const repositoriesService = new RepositoriesService();
