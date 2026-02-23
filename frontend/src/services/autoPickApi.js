import axios from 'axios';

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:3001/api';

const api = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json'
  }
});

// Add token to requests
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Auto-Pick API
export const autoPickApi = {
  // Get settings for a specific league
  getSettings: async (leagueId) => {
    const response = await api.get(`/auto-pick/league/${leagueId}`);
    return response.data;
  },

  // Save settings for a league
  saveSettings: async (leagueId, settings) => {
    const response = await api.post(`/auto-pick/league/${leagueId}`, settings);
    return response.data;
  },

  // Get all auto-pick settings for the user
  getAllSettings: async () => {
    const response = await api.get('/auto-pick/');
    return response.data;
  },

  // Trigger auto-pick (when timer expires)
  triggerAutoPick: async (leagueId, draftId, playerId) => {
    const response = await api.post(`/auto-pick/league/${leagueId}/trigger`, {
      draftId,
      playerId
    });
    return response.data;
  }
};

export default api;
