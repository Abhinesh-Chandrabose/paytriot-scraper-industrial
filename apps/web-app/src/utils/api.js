/**
 * Industrial API Client using Native Fetch.
 * Avoids Axios conflicts and provides a consistent interface.
 */

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';

async function request(endpoint, options = {}) {
  const { body, headers, ...customConfig } = options;
  const config = {
    method: body ? 'POST' : 'GET',
    ...customConfig,
    headers: {
      'Content-Type': 'application/json',
      ...headers,
    },
  };

  if (body) {
    config.body = JSON.stringify(body);
  }

  try {
    const response = await fetch(`${API_BASE_URL}${endpoint}`, config);
    const data = await response.json();
    
    if (response.ok) {
      return data;
    }
    
    throw new Error(data.detail || response.statusText);
  } catch (err) {
    return Promise.reject(err.message || 'Something went wrong');
  }
}

export const api = {
  get: (endpoint, config) => request(endpoint, { ...config, method: 'GET' }),
  post: (endpoint, body, config) => request(endpoint, { ...config, method: 'POST', body }),
  patch: (endpoint, body, config) => request(endpoint, { ...config, method: 'PATCH', body }),
  delete: (endpoint, config) => request(endpoint, { ...config, method: 'DELETE' }),
};
