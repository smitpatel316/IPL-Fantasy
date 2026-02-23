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

// League API
export const leagueApi = {
  // Get all leagues for the current user
  getLeagues: async () => {
    const response = await api.get('/leagues');
    return response.data;
  },

  // Get a specific league by ID
  getLeague: async (leagueId) => {
    const response = await api.get(`/leagues/${leagueId}`);
    return response.data;
  },

  // Create a new league
  createLeague: async (leagueData) => {
    const response = await api.post('/leagues', leagueData);
    return response.data;
  },

  // Join a league with invite code
  joinLeague: async (code, teamName) => {
    const response = await api.post('/leagues/join', {
      code: code.toUpperCase(),
      teamName
    });
    return response.data;
  },

  // Get invite details for a league (requires auth)
  getInvite: async (leagueId) => {
    const response = await api.get(`/leagues/${leagueId}/invite`);
    return response.data;
  },

  // Validate invite code (public endpoint - no auth required)
  validateInvite: async (code) => {
    const response = await api.get(`/leagues/invite/${code.toUpperCase()}`);
    return response.data;
  },

  // Regenerate invite code (commissioner only)
  regenerateInvite: async (leagueId) => {
    const response = await api.post(`/leagues/${leagueId}/invite/regenerate`);
    return response.data;
  },

  // Update league status (commissioner only)
  updateLeagueStatus: async (leagueId, status) => {
    const response = await api.put(`/leagues/${leagueId}/status`, { status });
    return response.data;
  }
};

export default api;
