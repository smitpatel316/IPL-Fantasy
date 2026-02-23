import { create } from 'zustand';
import { autoPickApi } from '../services/autoPickApi';

export const useAutoPickStore = create((set, get) => ({
  // State
  settings: {},
  allSettings: [],
  loading: false,
  error: null,
  success: null,

  // Actions
  fetchSettings: async (leagueId) => {
    set({ loading: true, error: null });
    try {
      const settings = await autoPickApi.getSettings(leagueId);
      set({ settings, loading: false });
      return settings;
    } catch (error) {
      set({ error: error.message, loading: false });
      throw error;
    }
  },

  saveSettings: async (leagueId, settings) => {
    set({ loading: true, error: null, success: null });
    try {
      const savedSettings = await autoPickApi.saveSettings(leagueId, settings);
      set({ 
        settings: savedSettings, 
        loading: false,
        success: 'Settings saved successfully!'
      });
      return savedSettings;
    } catch (error) {
      set({ error: error.message, loading: false });
      throw error;
    }
  },

  fetchAllSettings: async () => {
    set({ loading: true, error: null });
    try {
      const allSettings = await autoPickApi.getAllSettings();
      set({ allSettings, loading: false });
      return allSettings;
    } catch (error) {
      set({ error: error.message, loading: false });
      throw error;
    }
  },

  triggerAutoPick: async (leagueId, draftId, playerId) => {
    try {
      const result = await autoPickApi.triggerAutoPick(leagueId, draftId, playerId);
      return result;
    } catch (error) {
      console.error('Auto-pick trigger failed:', error);
      throw error;
    }
  },

  clearMessages: () => {
    set({ error: null, success: null });
  },

  // Initialize with default settings
  resetSettings: () => {
    set({
      settings: {
        isEnabled: false,
        favoritePlayers: [],
        favoritePlayerIds: [],
        preferredRoles: [],
        maxPrice: 100.00,
        autoBidEnabled: false,
        autoBidIncrement: 1.00
      },
      error: null,
      success: null
    });
  }
}));

export default useAutoPickStore;
