import React, { useState, useEffect } from 'react';
import axios from 'axios';

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:3001/api';

export default function AutoPickSettings({ leagueId, onClose }) {
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);
  
  // Settings state
  const [settings, setSettings] = useState({
    isEnabled: false,
    favoritePlayers: [],
    favoritePlayerIds: [],
    preferredRoles: [],
    maxPrice: 100.00,
    autoBidEnabled: false,
    autoBidIncrement: 1.00
  });

  // Available players for favorites
  const [availablePlayers, setAvailablePlayers] = useState([]);
  
  // Role options
  const roleOptions = ['batsman', 'bowler', 'all-rounder', 'wicket-keeper'];

  useEffect(() => {
    fetchSettings();
    fetchAvailablePlayers();
  }, [leagueId]);

  const fetchSettings = async () => {
    try {
      const token = localStorage.getItem('token');
      const response = await axios.get(`${API_URL}/auto-pick/league/${leagueId}`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setSettings(response.data);
    } catch (err) {
      console.error('Error fetching settings:', err);
    } finally {
      setLoading(false);
    }
  };

  const fetchAvailablePlayers = async () => {
    try {
      const token = localStorage.getItem('token');
      const response = await axios.get(`${API_URL}/players`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setAvailablePlayers(response.data.players || []);
    } catch (err) {
      console.error('Error fetching players:', err);
    }
  };

  const handleSave = async () => {
    setSaving(true);
    setError(null);
    setSuccess(null);

    try {
      const token = localStorage.getItem('token');
      await axios.post(`${API_URL}/auto-pick/league/${leagueId}`, settings, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setSuccess('Auto-pick settings saved successfully!');
    } catch (err) {
      setError(err.response?.data?.error || 'Failed to save settings');
    } finally {
      setSaving(false);
    }
  };

  const toggleFavoritePlayer = (playerId) => {
    setSettings(prev => ({
      ...prev,
      favoritePlayerIds: prev.favoritePlayerIds.includes(playerId)
        ? prev.favoritePlayerIds.filter(id => id !== playerId)
        : [...prev.favoritePlayerIds, playerId],
      // Also update the favoritePlayers array with player details
      favoritePlayers: prev.favoritePlayerIds.includes(playerId)
        ? prev.favoritePlayers.filter(p => p.id !== playerId)
        : [...prev.favoritePlayers, availablePlayers.find(p => p.id === playerId)]
    }));
  };

  const toggleRole = (role) => {
    setSettings(prev => ({
      ...prev,
      preferredRoles: prev.preferredRoles.includes(role)
        ? prev.preferredRoles.filter(r => r !== role)
        : [...prev.preferredRoles, role]
    }));
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center p-8">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
      <div className="p-6">
        <div className="flex justify-between items-center mb-6">
          <h2 className="text-2xl font-bold text-gray-800">Auto-Pick Settings</h2>
          {onClose && (
            <button 
              onClick={onClose}
              className="text-gray-500 hover:text-gray-700"
            >
              ✕
            </button>
          )}
        </div>

        {error && (
          <div className="mb-4 p-3 bg-red-100 border border-red-400 text-red-700 rounded">
            {error}
          </div>
        )}

        {success && (
          <div className="mb-4 p-3 bg-green-100 border border-green-400 text-green-700 rounded">
            {success}
          </div>
        )}

        {/* Enable Auto-Pick Toggle */}
        <div className="mb-6 p-4 bg-gray-50 rounded-lg">
          <label className="flex items-center cursor-pointer">
            <div className="relative">
              <input
                type="checkbox"
                checked={settings.isEnabled}
                onChange={(e) => setSettings(prev => ({ ...prev, isEnabled: e.target.checked }))}
                className="sr-only"
              />
              <div className={`w-12 h-6 rounded-full transition-colors ${settings.isEnabled ? 'bg-green-500' : 'bg-gray-300'}`}>
                <div className={`absolute top-1 left-1 w-4 h-4 bg-white rounded-full transition-transform ${settings.isEnabled ? 'translate-x-6' : ''}`}></div>
              </div>
            </div>
            <div className="ml-3">
              <span className="text-lg font-medium text-gray-900">Enable Auto-Pick</span>
              <p className="text-sm text-gray-500">Automatically pick players when timer expires</p>
            </div>
          </label>
        </div>

        {settings.isEnabled && (
          <>
            {/* Favorite Players */}
            <div className="mb-6">
              <h3 className="text-lg font-semibold text-gray-800 mb-3">Favorite Players</h3>
              <p className="text-sm text-gray-500 mb-3">
                These players will always be picked when available
              </p>
              <div className="grid grid-cols-2 gap-2 max-h-48 overflow-y-auto">
                {availablePlayers.map(player => (
                  <button
                    key={player.id}
                    onClick={() => toggleFavoritePlayer(player.id)}
                    className={`p-2 text-left rounded border transition-colors ${
                      settings.favoritePlayerIds.includes(player.id)
                        ? 'bg-blue-100 border-blue-500 text-blue-900'
                        : 'bg-white border-gray-300 hover:bg-gray-50'
                    }`}
                  >
                    <div className="font-medium">{player.name}</div>
                    <div className="text-xs text-gray-500">{player.team} • {player.role}</div>
                  </button>
                ))}
              </div>
              {settings.favoritePlayerIds.length > 0 && (
                <p className="mt-2 text-sm text-gray-600">
                  {settings.favoritePlayerIds.length} player(s) selected
                </p>
              )}
            </div>

            {/* Preferred Roles */}
            <div className="mb-6">
              <h3 className="text-lg font-semibold text-gray-800 mb-3">Preferred Roles</h3>
              <p className="text-sm text-gray-500 mb-3">
                Auto-pick players of these roles (leave empty for any)
              </p>
              <div className="flex flex-wrap gap-2">
                {roleOptions.map(role => (
                  <button
                    key={role}
                    onClick={() => toggleRole(role)}
                    className={`px-4 py-2 rounded-full text-sm font-medium capitalize transition-colors ${
                      settings.preferredRoles.includes(role)
                        ? 'bg-blue-500 text-white'
                        : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                    }`}
                  >
                    {role}
                  </button>
                ))}
              </div>
            </div>

            {/* Max Price */}
            <div className="mb-6">
              <h3 className="text-lg font-semibold text-gray-800 mb-3">Maximum Player Price</h3>
              <div className="flex items-center">
                <span className="text-xl font-bold text-gray-700 mr-2">₹</span>
                <input
                  type="number"
                  value={settings.maxPrice}
                  onChange={(e) => setSettings(prev => ({ ...prev, maxPrice: parseFloat(e.target.value) || 0 }))}
                  min="0"
                  step="0.5"
                  className="w-32 px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                />
                <span className="ml-2 text-gray-500">Crores</span>
              </div>
            </div>

            {/* Auto-Bid Settings */}
            <div className="mb-6 p-4 bg-yellow-50 rounded-lg">
              <h3 className="text-lg font-semibold text-gray-800 mb-3">Auto-Bid Settings</h3>
              
              <label className="flex items-center cursor-pointer mb-4">
                <div className="relative">
                  <input
                    type="checkbox"
                    checked={settings.autoBidEnabled}
                    onChange={(e) => setSettings(prev => ({ ...prev, autoBidEnabled: e.target.checked }))}
                    className="sr-only"
                  />
                  <div className={`w-12 h-6 rounded-full transition-colors ${settings.autoBidEnabled ? 'bg-green-500' : 'bg-gray-300'}`}>
                    <div className={`absolute top-1 left-1 w-4 h-4 bg-white rounded-full transition-transform ${settings.autoBidEnabled ? 'translate-x-6' : ''}`}></div>
                  </div>
                </div>
                <div className="ml-3">
                  <span className="font-medium text-gray-900">Enable Auto-Bid</span>
                  <p className="text-sm text-gray-500">Automatically bid on players you want</p>
                </div>
              </label>

              {settings.autoBidEnabled && (
                <div className="flex items-center">
                  <span className="text-gray-700 mr-2">Auto-bid increment:</span>
                  <span className="text-xl font-bold text-gray-700 mr-2">₹</span>
                  <input
                    type="number"
                    value={settings.autoBidIncrement}
                    onChange={(e) => setSettings(prev => ({ ...prev, autoBidIncrement: parseFloat(e.target.value) || 0 }))}
                    min="0.5"
                    step="0.5"
                    className="w-24 px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  />
                  <span className="ml-2 text-gray-500">Crores</span>
                </div>
              )}
            </div>

            {/* Summary */}
            <div className="mb-6 p-4 bg-blue-50 rounded-lg">
              <h3 className="text-lg font-semibold text-gray-800 mb-2">Summary</h3>
              <ul className="text-sm text-gray-700 space-y-1">
                <li>• Auto-pick is <strong>{settings.isEnabled ? 'enabled' : 'disabled'}</strong></li>
                <li>• Favorite players: <strong>{settings.favoritePlayerIds.length}</strong></li>
                <li>• Preferred roles: <strong>{settings.preferredRoles.length > 0 ? settings.preferredRoles.join(', ') : 'Any'}</strong></li>
                <li>• Max price: <strong>₹{settings.maxPrice} Cr</strong></li>
                <li>• Auto-bid: <strong>{settings.autoBidEnabled ? `Enabled (₹${settings.autoBidIncrement} increment)` : 'Disabled'}</strong></li>
              </ul>
            </div>
          </>
        )}

        {/* Actions */}
        <div className="flex justify-end gap-3 pt-4 border-t">
          {onClose && (
            <button
              onClick={onClose}
              className="px-4 py-2 text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200 transition-colors"
            >
              Cancel
            </button>
          )}
          <button
            onClick={handleSave}
            disabled={saving}
            className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50"
          >
            {saving ? 'Saving...' : 'Save Settings'}
          </button>
        </div>
      </div>
    </div>
  );
}
