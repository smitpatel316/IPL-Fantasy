import React, { useState, useEffect } from 'react';
import { leagueApi } from '../services/leagueApi';

export default function LeagueInvite({ leagueId, leagueName, onClose }) {
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [inviteData, setInviteData] = useState(null);
  const [error, setError] = useState(null);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    fetchInviteData();
  }, [leagueId]);

  const fetchInviteData = async () => {
    try {
      const data = await leagueApi.getInvite(leagueId);
      setInviteData(data);
    } catch (err) {
      setError(err.response?.data?.error || 'Failed to load invite data');
    } finally {
      setLoading(false);
    }
  };

  const handleCopy = async () => {
    if (!inviteData?.inviteUrl) return;
    
    try {
      await navigator.clipboard.writeText(inviteData.inviteUrl);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      // Fallback for browsers that don't support clipboard API
      const textArea = document.createElement('textarea');
      textArea.value = inviteData.inviteUrl;
      document.body.appendChild(textArea);
      textArea.select();
      document.execCommand('copy');
      document.body.removeChild(textArea);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const handleShare = async () => {
    if (!inviteData?.inviteUrl || !navigator.share) return;

    try {
      await navigator.share({
        title: `Join my ${leagueName || 'IPL Fantasy'} league!`,
        text: `Join my league "${leagueName}" on IPL Fantasy Pro! Use invite code: ${inviteData.code}`,
        url: inviteData.inviteUrl
      });
    } catch (err) {
      // User cancelled or share failed, fallback to copy
      if (err.name !== 'AbortError') {
        handleCopy();
      }
    }
  };

  const handleRegenerate = async () => {
    if (!window.confirm('Are you sure? This will invalidate the current invite link.')) {
      return;
    }

    setSaving(true);
    setError(null);

    try {
      const data = await leagueApi.regenerateInvite(leagueId);
      // Refresh invite data
      await fetchInviteData();
    } catch (err) {
      setError(err.response?.data?.error || 'Failed to regenerate invite code');
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center p-8">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg shadow-xl max-w-md w-full">
      <div className="p-6">
        <div className="flex justify-between items-center mb-6">
          <h2 className="text-2xl font-bold text-gray-800">Invite Players</h2>
          {onClose && (
            <button 
              onClick={onClose}
              className="text-gray-500 hover:text-gray-700 text-2xl leading-none"
            >
              ×
            </button>
          )}
        </div>

        {error && (
          <div className="mb-4 p-3 bg-red-100 border border-red-400 text-red-700 rounded">
            {error}
          </div>
        )}

        {/* League Name */}
        <div className="mb-6">
          <p className="text-sm text-gray-500">League</p>
          <p className="text-lg font-semibold text-gray-900">{leagueName || inviteData?.leagueName}</p>
        </div>

        {/* Invite Code Display */}
        <div className="mb-6">
          <p className="text-sm text-gray-500 mb-2">Invite Code</p>
          <div className="flex items-center gap-2">
            <div className="flex-1 p-3 bg-gray-100 rounded-lg border-2 border-dashed border-gray-300">
              <span className="text-2xl font-mono font-bold text-gray-800 tracking-wider">
                {inviteData?.code || '------'}
              </span>
            </div>
            <button
              onClick={handleCopy}
              className="p-3 bg-gray-100 rounded-lg hover:bg-gray-200 transition-colors border border-gray-300"
              title="Copy code"
            >
              {copied ? (
                <svg className="w-6 h-6 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
              ) : (
                <svg className="w-6 h-6 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                </svg>
              )}
            </button>
          </div>
        </div>

        {/* Shareable Link */}
        <div className="mb-6">
          <p className="text-sm text-gray-500 mb-2">Share Link</p>
          <div className="flex items-center gap-2">
            <input
              type="text"
              value={inviteData?.inviteUrl || ''}
              readOnly
              className="flex-1 p-3 bg-gray-50 rounded-lg border border-gray-300 text-sm text-gray-600 font-mono truncate"
            />
            <button
              onClick={handleCopy}
              className={`p-3 rounded-lg transition-colors border ${
                copied 
                  ? 'bg-green-100 border-green-400 text-green-700' 
                  : 'bg-blue-50 border-blue-300 text-blue-600 hover:bg-blue-100'
              }`}
              title="Copy link"
            >
              {copied ? (
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
              ) : (
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 5H6a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2v-1M8 5a2 2 0 002 2h2a2 2 0 002-2M8 5a2 2 0 012-2h2a2 2 0 012 2m0 0h2a2 2 0 012 2v3m2 4H10m0 0l3-3m-3 3l3 3" />
                </svg>
              )}
            </button>
          </div>
          {copied && (
            <p className="text-sm text-green-600 mt-2">Copied to clipboard!</p>
          )}
        </div>

        {/* Share Button (Mobile) */}
        {navigator.share && (
          <div className="mb-6">
            <button
              onClick={handleShare}
              className="w-full py-3 px-4 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors flex items-center justify-center gap-2 font-medium"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8.684 13.342C8.886 12.938 9 12.482 9 12c0-.482-.114-.938-.316-1.342m0 2.684a3 3 0 110-2.684m0 2.684l6.632 3.316m-6.632-6l6.632-3.316m0 0a3 3 0 105.367-2.684 3 3 0 00-5.367 2.684zm0 9.316a3 3 0 105.368 2.684 3 3 0 00-5.368-2.684z" />
              </svg>
              Share Invite
            </button>
          </div>
        )}

        {/* Regenerate Button */}
        <div className="pt-4 border-t">
          <button
            onClick={handleRegenerate}
            disabled={saving}
            className="w-full py-2 px-4 bg-gray-100 text-gray-600 rounded-lg hover:bg-gray-200 transition-colors text-sm disabled:opacity-50 flex items-center justify-center gap-2"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
            {saving ? 'Generating...' : 'Generate New Code'}
          </button>
          <p className="text-xs text-gray-500 mt-2 text-center">
            Generating a new code will invalidate the old one
          </p>
        </div>
      </div>
    </div>
  );
}
