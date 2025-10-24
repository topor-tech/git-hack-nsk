export interface Project {
  id: number;
  full_name: string;
  description: string;
  created_at: string;
  updated_at: string;
  groups: any;
}

export interface ProjectsResponse {
  data: Project[];
  page: any;
  request_id: string;
  status: string;
}

export interface ErrorResponse {
  error: string;
  message: string;
  request_id?: string;
}

export class ProjectsService {
  private baseUrl = 'http://localhost:8000/api';

  // Helper function to get cookie value
  private getCookie(name: string): string | null {
    const value = document.cookie
      .split('; ')
      .find(row => row.startsWith(`${name}=`))
      ?.split('=')[1];
    return value || null;
  }

  async getProjects(
    limit?: number,
    sort?: string,
    order?: string
  ): Promise<ProjectsResponse> {
    const params = new URLSearchParams();
    if (limit) params.append('limit', limit.toString());
    if (sort) params.append('sort', sort);
    if (order) params.append('order', order);

    const url = `${this.baseUrl}/pulse/projects?${params.toString()}`;

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
      const errorData = await response.json().catch(() => ({ detail: 'Failed to fetch projects' }));
      throw new Error(errorData.detail || 'Failed to fetch projects');
    }

    const result = await response.json();
    return result;
  }
}

export const projectsService = new ProjectsService();
