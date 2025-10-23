import React, { createContext, useContext, useState, useCallback, type ReactNode } from 'react';

export interface LoginRequest {
  username: string;
  password: string;
}

export interface LoginResponse {
  access_token: string;
  refresh_token: string;
  message: string;
}

interface AuthContextType {
  isAuthenticated: boolean;
  login: (credentials: LoginRequest) => Promise<LoginResponse>;
  logout: () => Promise<void>;
  loading: boolean;
  error: string | null;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

interface AuthProviderProps {
  children: ReactNode;
}

// Helper function to check if user is authenticated via cookies
const checkAuthStatus = (): boolean => {
  const accessToken = document.cookie
    .split('; ')
    .find(row => row.startsWith('ACCESS_TOKEN='))
    ?.split('=')[1];
  return !!accessToken;
};

export const AuthProvider: React.FC<AuthProviderProps> = ({ children }) => {
  const [isAuthenticated, setIsAuthenticated] = useState<boolean>(checkAuthStatus());
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const baseUrl = 'http://localhost:8000/api/sfera';

  const login = useCallback(async (credentials: LoginRequest): Promise<LoginResponse> => {
    setLoading(true);
    setError(null);

    try {
      const response = await fetch(`${baseUrl}/auth/login`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'accept': 'application/json',
        },
        credentials: 'include', // Important for cookies
        body: JSON.stringify(credentials),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: 'Login failed' }));
        throw new Error(errorData.detail || 'Login failed');
      }

      const result = await response.json();

      // Set authentication cookies from response
      if (result.access_token) {
        document.cookie = `ACCESS_TOKEN=${result.access_token}; path=/; max-age=3600; secure; samesite=strict`;
      }
      if (result.refresh_token) {
        document.cookie = `REFRESH_TOKEN=${result.refresh_token}; path=/; max-age=86400; secure; samesite=strict`;
      }

      setIsAuthenticated(true);
      return result;
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Login failed';
      setError(errorMessage);
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  const logout = useCallback(async (): Promise<void> => {
    setLoading(true);
    setError(null);

    try {
      // Clear cookies by making a request to logout endpoint if it exists
      // For now, we'll just clear local state
      document.cookie = 'ACCESS_TOKEN=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;';
      document.cookie = 'REFRESH_TOKEN=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;';
      document.cookie = 'CHECK_AUTH=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;';
      setIsAuthenticated(false);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Logout failed';
      setError(errorMessage);
    } finally {
      setLoading(false);
    }
  }, []);

  const value: AuthContextType = {
    isAuthenticated,
    login,
    logout,
    loading,
    error,
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
};

// Legacy service class for backward compatibility
export class AuthService {
  private baseUrl = 'http://127.0.0.1:8000/api/sfera';

  async login(credentials: LoginRequest): Promise<LoginResponse> {
    const response = await fetch(`${this.baseUrl}/auth/login`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'accept': 'application/json',
      },
      credentials: 'include', // Important for cookies
      body: JSON.stringify(credentials),
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({ detail: 'Login failed' }));
      throw new Error(errorData.detail || 'Login failed');
    }

    const result = await response.json();

    // Set authentication cookies from response
    if (result.access_token) {
      document.cookie = `ACCESS_TOKEN=${result.access_token}; path=/; max-age=3600; secure; samesite=strict`;
    }
    if (result.refresh_token) {
      document.cookie = `REFRESH_TOKEN=${result.refresh_token}; path=/; max-age=86400; secure; samesite=strict`;
    }

    return result;
  }

  async logout(): Promise<void> {
    // Clear cookies by making a request to logout endpoint if it exists
    // For now, we'll just clear local state
    document.cookie = 'ACCESS_TOKEN=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;';
    document.cookie = 'REFRESH_TOKEN=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;';
    document.cookie = 'CHECK_AUTH=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;';
  }
}

export const authService = new AuthService();
