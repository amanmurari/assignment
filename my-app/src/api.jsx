import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'https://assignment-8p3t.onrender.com';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const executeQuery = async (query, isAsync = false) => {
  try {
    const response = await api.post('/query', {
      query,
      async_execution: isAsync,
      max_iterations: 3,
    });
    return response.data;
  } catch (error) {
    console.error('API Error:', error);
    throw new Error(
      error.response?.data?.detail || 
      error.response?.data?.error || 
      error.message || 
      'An error occurred while processing your query'
    );
  }
};