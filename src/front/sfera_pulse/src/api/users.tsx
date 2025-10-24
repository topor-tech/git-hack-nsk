export interface UserSuggestion {
  email?: string;
  first_name?: string;
  full_name?: string;
  last_name?: string;
  login?: string;
  middle_name?: string;
  principal_name?: string;
}

export interface ResponsePageMeta {
  cursor?: string;
  limit: number;
  total?: number;
}

export interface UserSuggestionsResponse {
  data: UserSuggestion[];
  page: ResponsePageMeta;
}

export interface ErrorResponse {
  error: string;
  message: string;
  request_id?: string;
}

import { getApiBaseUrl } from './config';

export class UsersService {
  private baseUrl = getApiBaseUrl();

  // Helper function to get cookie value
  private getCookie(name: string): string | null {
    const value = document.cookie
      .split('; ')
      .find(row => row.startsWith(`${name}=`))
      ?.split('=')[1];
    return value || null;
  }

  async getUserSuggestions(
    projectKey: string,
    repoName: string,
    params?: {
      q?: string;
      prId?: number;
      skipSelf?: boolean;
      cursor?: string;
      limit?: number;
    }
  ): Promise<UserSuggestionsResponse> {
    const queryParams = new URLSearchParams();
    
    if (params?.q) queryParams.append('q', params.q);
    if (params?.prId) queryParams.append('prId', params.prId.toString());
    if (params?.skipSelf !== undefined) queryParams.append('skipSelf', params.skipSelf.toString());
    if (params?.cursor) queryParams.append('cursor', params.cursor);
    if (params?.limit) queryParams.append('limit', params.limit.toString());

    const url = `${this.baseUrl}/pulse/projects/${projectKey}/repos/${repoName}/pull-requests/user-suggestions?${queryParams.toString()}`;

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
      const errorData = await response.json().catch(() => ({ detail: 'Failed to fetch user suggestions' }));
      throw new Error(errorData.detail || 'Failed to fetch user suggestions');
    }

    const result = await response.json();
    return result;
  }
}

export const usersService = new UsersService();
