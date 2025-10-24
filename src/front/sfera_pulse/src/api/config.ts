// API Configuration
// Determines the base URL based on environment

const getBaseUrl = (): string => {
  // Check if we're in development mode
  const isDevelopment = import.meta.env.DEV || 
                       window.location.hostname === 'localhost' || 
                       window.location.hostname === '127.0.0.1';
  
  if (isDevelopment) {
    return 'http://localhost:8000/api';
  } else {
    // Production mode - use the current URL's schema and host
    const currentUrl = window.location;
    return `${currentUrl.protocol}//${currentUrl.host}/api`;
  }
};

export const API_CONFIG = {
  BASE_URL: getBaseUrl(),
  SFERA_BASE_URL: getBaseUrl().replace('/api', '/api/sfera'),
};

// Helper function to get the current base URL
export const getApiBaseUrl = (): string => API_CONFIG.BASE_URL;
export const getSferaApiBaseUrl = (): string => API_CONFIG.SFERA_BASE_URL;
