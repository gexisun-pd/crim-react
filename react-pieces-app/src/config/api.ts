// API configuration utility for Create React App
export const getApiBaseUrl = (): string => {
  // If environment variable is set, use it
  if (process.env.REACT_APP_API_BASE_URL) {
    return process.env.REACT_APP_API_BASE_URL;
  }
  
  // For local network access, try to determine the API server URL dynamically
  // If accessing via IP address, use the same IP for API calls
  if (typeof window !== 'undefined') {
    const hostname = window.location.hostname;
    
    // If accessing via IP address (not localhost), use same IP for API
    if (hostname !== 'localhost' && hostname !== '127.0.0.1') {
      return `http://${hostname}:9000`;
    }
  }
  
  // Default fallback
  return 'http://localhost:9000';
};

export const getHealthCheckUrl = (): string => {
  const baseUrl = getApiBaseUrl();
  return `${baseUrl}/health`;
};
