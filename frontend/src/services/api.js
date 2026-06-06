import axios from 'axios';

// Configure axios defaults
const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000/api/v1';

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000, // 30 seconds
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor for logging
api.interceptors.request.use(
  (config) => {
    console.log(`API Request: ${config.method?.toUpperCase()} ${config.url}`);
    return config;
  },
  (error) => {
    console.error('API Request Error:', error);
    return Promise.reject(error);
  }
);

// Response interceptor for error handling
api.interceptors.response.use(
  (response) => {
    return response;
  },
  (error) => {
    console.error('API Response Error:', error);
    
    if (error.response) {
      // Server responded with error status
      const { status, data } = error.response;
      console.error(`API Error ${status}:`, data);
    } else if (error.request) {
      // Request was made but no response received
      console.error('No response received:', error.request);
    } else {
      // Error in setting up the request
      console.error('Request setup error:', error.message);
    }
    
    return Promise.reject(error);
  }
);

// Session API
export const sessionAPI = {
  create: (data) => api.post('/chat/sessions', data),
  get: (sessionId) => api.get(`/chat/sessions/${sessionId}`),
  update: (sessionId, data) => api.put(`/chat/sessions/${sessionId}`, data),
  delete: (sessionId) => api.delete(`/chat/sessions/${sessionId}`),
  list: (limit = 20) => api.get('/chat/sessions', { params: { limit } }),
  getStats: (sessionId) => api.get(`/chat/sessions/${sessionId}/stats`),
  getConversation: (sessionId, includeFiles = false) => 
    api.get(`/chat/sessions/${sessionId}/conversation`, { params: { include_files: includeFiles } }),
};

// Message API
export const messageAPI = {
  send: (sessionId, content, metadata = null) => 
    api.post(`/chat/sessions/${sessionId}/messages`, { 
      content, 
      role: 'user',
      metadata 
    }),
  list: (sessionId, limit = 50, offset = 0) => 
    api.get(`/chat/sessions/${sessionId}/messages`, { 
      params: { limit, offset } 
    }),
};

// File API
export const fileAPI = {
  upload: (sessionId, file, onProgress = null) => {
    const formData = new FormData();
    formData.append('file', file);
    
    return api.post(`/files/upload/${sessionId}`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
      onUploadProgress: (progressEvent) => {
        if (onProgress && progressEvent.total) {
          const progress = (progressEvent.loaded / progressEvent.total) * 100;
          onProgress(Math.round(progress));
        }
      },
    });
  },
  
  list: (sessionId) => api.get(`/files/${sessionId}`),
  
  get: (sessionId, fileId) => api.get(`/files/${sessionId}/${fileId}`),
  
  download: (sessionId, fileId) => 
    api.get(`/files/${sessionId}/${fileId}/download`, {
      responseType: 'blob',
    }),
  
  delete: (sessionId, fileId) => api.delete(`/files/${sessionId}/${fileId}`),
};

// Model API
export const modelAPI = {
  list: () => api.get('/models'),
  
  listProvider: (provider) => api.get(`/models/${provider}`),
  
  select: (sessionId, modelName, provider) => 
    api.post(`/models/select/${sessionId}`, {
      model_name: modelName,
      provider: provider,
    }),
  
  getSessionModel: (sessionId) => api.get(`/models/session/${sessionId}`),
  
  checkHealth: () => api.get('/models/health'),
};

// Utility functions for error handling
export const handleAPIError = (error) => {
  if (error.response) {
    const { status, data } = error.response;
    
    switch (status) {
      case 400:
        return data?.detail || 'Invalid request. Please check your input.';
      case 401:
        return 'Authentication required.';
      case 403:
        return 'Access denied.';
      case 404:
        return data?.detail || 'Resource not found.';
      case 422:
        return data?.detail || 'Validation error.';
      case 429:
        return 'Too many requests. Please wait a moment.';
      case 500:
        return data?.detail || 'Server error. Please try again later.';
      case 502:
      case 503:
      case 504:
        return 'Service temporarily unavailable. Please try again.';
      default:
        return data?.detail || `Error ${status}: ${error.message}`;
    }
  } else if (error.request) {
    return 'Unable to connect to the server. Please check your internet connection.';
  } else {
    return error.message || 'An unexpected error occurred.';
  }
};

// Utility function to check if error is network-related
export const isNetworkError = (error) => {
  return !error.response && (
    error.code === 'NETWORK_ERROR' ||
    error.code === 'ECONNABORTED' ||
    error.message.includes('Network Error') ||
    error.message.includes('timeout')
  );
};

// Health check function
export const healthCheck = async () => {
  try {
    const response = await api.get('/health', { timeout: 5000 });
    return { healthy: true, data: response.data };
  } catch (error) {
    return { healthy: false, error: handleAPIError(error) };
  }
};

export default api;