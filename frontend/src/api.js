import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

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
    throw new Error(
      error.response?.data?.detail || 
      error.response?.data?.error || 
      error.message || 
      'An error occurred while processing your query'
    );
  }
};

export const fetchTaskStatus = async (taskId) => {
  try {
    const response = await api.get(`/tasks/${taskId}`);
    return response.data;
  } catch (error) {
    throw new Error(
      error.response?.data?.detail || 
      error.response?.data?.error || 
      error.message || 
      'An error occurred while fetching task status'
    );
  }
};

export const listTasks = async (status, limit = 10, offset = 0) => {
  try {
    const response = await api.get('/tasks', {
      params: { status, limit, offset },
    });
    return response.data;
  } catch (error) {
    throw new Error(
      error.response?.data?.detail || 
      error.response?.data?.error || 
      error.message || 
      'An error occurred while fetching tasks'
    );
  }
};

export const deleteTask = async (taskId) => {
  try {
    const response = await api.delete(`/tasks/${taskId}`);
    return response.data;
  } catch (error) {
    throw new Error(
      error.response?.data?.detail || 
      error.response?.data?.error || 
      error.message || 
      'An error occurred while deleting the task'
    );
  }
}; 