import React, { useState, useEffect } from 'react';
import { leagueApi } from '../services/leagueApi';

export default function JoinLeague({ onJoinComplete, onCancel }) {
  const [step, setStep] = useState('enterCode'); // 'enterCode', 'confirm', 'joining', 'success', 'error'
  const [inviteCode, setInviteCode] = useState('');
  const [teamName, setTeamName] = useState('');
  const [leagueInfo, setLeagueInfo] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);
  const [copied, setCopied] = useState(false);

  // Handle deep links
  useEffect(() => {
    const path = window.location.pathname;
    const match = path.match(/\/join\/([A-Z0-9]+)/i);
    if (match) {
      setInviteCode(match[1]);
      handleValidateCode(match[1]);
    }
  }, []);

  const handleValidateCode = async (code = inviteCode) => {
    if (!code.trim()) {
      setError('Please enter an invite code');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const data = await leagueApi.validateInvite(code);
      
      if (!data.valid) {
        setError('Invalid invite code');
        setStep('enterCode');
        return;
      }

      if (data.league.isFull) {
        setError('This league is full and cannot accept new members');
        setStep('enterCode');
        return;
      }

      setLeagueInfo(data.league);
      setStep('confirm');
    } catch (err) {
      if (err.response?.status === 404) {
        setError('League not found. Please check the invite code.');
      } else {
        setError(err.response?.data?.error || 'Failed to validate invite code');
      }
      setStep('enterCode');
    } finally {
      setLoading(false);
    }
  };

  const handleSubmitCode = (e) => {
    e.preventDefault();
    handleValidateCode();
  };

  const handleJoin = async () => {
    if (!teamName.trim()) {
      setError('Please enter a team name');
      return;
    }

    setLoading(true);
    setStep('joining');
    setError(null);

    try {
      await leagueApi.joinLeague(inviteCode, teamName);
      setStep('success');
      if (onJoinComplete) {
        onJoinComplete(leagueInfo.id);
      }
    } catch (err) {
      setError(err.response?.data?.error || 'Failed to join league');
      setStep('confirm');
    } finally {
      setLoading(false);
    }
  };

  const handleCopyCode = async () => {
    try {
      await navigator.clipboard.writeText(inviteCode);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      const textArea = document.createElement('textarea');
      textArea.value = inviteCode;
      document.body.appendChild(textArea);
      textArea.select();
      document.execCommand('copy');
      document.body.removeChild(textArea);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const handleChangeCode = () => {
    setStep('enterCode');
    setLeagueInfo(null);
    setError(null);
    // Update URL
    window.history.pushState({}, '', '/join');
  };

  // Step: Enter Code
  if (step === 'enterCode') {
    return (
      <div className="min-h-screen bg-gray-100 flex items-center justify-center p-4">
        <div className="bg-white rounded-lg shadow-xl max-w-md w-full">
          <div className="p-6">
            <div className="text-center mb-6">
              <div className="w-16 h-16 bg-blue-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <svg className="w-8 h-8 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />
                </svg>
              </div>
              <h1 className="text-2xl font-bold text-gray-800">Join a League</h1>
              <p className="text-gray-500 mt-2">Enter the invite code to join a league</p>
            </div>

            {error && (
              <div className="mb-4 p-3 bg-red-100 border border-red-400 text-red-700 rounded">
                {error}
              </div>
            )}

            <form onSubmit={handleSubmitCode}>
              <div className="mb-4">
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Invite Code
                </label>
                <input
                  type="text"
                  value={inviteCode}
                  onChange={(e) => setInviteCode(e.target.value.toUpperCase())}
                  placeholder="e.g., ABC123"
                  maxLength={6}
                  className="w-full px-4 py-3 border border-gray-300 rounded-lg text-center text-xl font-mono tracking-wider uppercase focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  autoFocus
                />
              </div>

              <button
                type="submit"
                disabled={loading || !inviteCode.trim()}
                className="w-full py-3 px-4 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors font-medium disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {loading ? (
                  <span className="flex items-center justify-center gap-2">
                    <svg className="animate-spin h-5 w-5" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                    Validating...
                  </span>
                ) : (
                  'Continue'
                )}
              </button>
            </form>

            {onCancel && (
              <button
                onClick={onCancel}
                className="w-full mt-3 py-2 text-gray-600 hover:text-gray-800 transition-colors"
              >
                Cancel
              </button>
            )}
          </div>
        </div>
      </div>
    );
  }

  // Step: Confirm
  if (step === 'confirm') {
    return (
      <div className="min-h-screen bg-gray-100 flex items-center justify-center p-4">
        <div className="bg-white rounded-lg shadow-xl max-w-md w-full">
          <div className="p-6">
            <div className="text-center mb-6">
              <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <svg className="w-8 h-8 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </div>
              <h1 className="text-2xl font-bold text-gray-800">Join League?</h1>
              <p className="text-gray-500 mt-2">You're about to join this league</p>
            </div>

            {error && (
              <div className="mb-4 p-3 bg-red-100 border border-red-400 text-red-700 rounded">
                {error}
              </div>
            )}

            {/* League Info Card */}
            <div className="mb-6 p-4 bg-gray-50 rounded-lg">
              <div className="flex justify-between items-center mb-3">
                <span className="text-gray-500">League Name</span>
                <span className="font-semibold text-gray-900">{leagueInfo?.name}</span>
              </div>
              <div className="flex justify-between items-center mb-3">
                <span className="text-gray-500">Invite Code</span>
                <div className="flex items-center gap-2">
                  <span className="font-mono font-bold text-gray-800">{leagueInfo?.code}</span>
                  <button
                    onClick={handleCopyCode}
                    className="p-1 text-gray-400 hover:text-gray-600"
                    title="Copy code"
                  >
                    {copied ? (
                      <svg className="w-4 h-4 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                      </svg>
                    ) : (
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                      </svg>
                    )}
                  </button>
                </div>
              </div>
              <div className="flex justify-between items-center mb-3">
                <span className="text-gray-500">Teams</span>
                <span className="font-semibold text-gray-900">
                  {leagueInfo?.currentTeams} / {leagueInfo?.maxTeams}
                </span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-gray-500">Status</span>
                <span className={`px-2 py-1 rounded text-xs font-medium ${
                  leagueInfo?.status === 'open' 
                    ? 'bg-green-100 text-green-800' 
                    : 'bg-gray-100 text-gray-800'
                }`}>
                  {leagueInfo?.status || 'Open'}
                </span>
              </div>
            </div>

            {/* Team Name Input */}
            <div className="mb-6">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Your Team Name
              </label>
              <input
                type="text"
                value={teamName}
                onChange={(e) => setTeamName(e.target.value)}
                placeholder="Enter your team name"
                maxLength={30}
                className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                autoFocus
              />
            </div>

            <div className="flex gap-3">
              <button
                onClick={handleChangeCode}
                className="flex-1 py-3 px-4 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 transition-colors font-medium"
              >
                Back
              </button>
              <button
                onClick={handleJoin}
                disabled={loading || !teamName.trim()}
                className="flex-1 py-3 px-4 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors font-medium disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {loading ? 'Joining...' : 'Join League'}
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  // Step: Joining
  if (step === 'joining') {
    return (
      <div className="min-h-screen bg-gray-100 flex items-center justify-center p-4">
        <div className="bg-white rounded-lg shadow-xl max-w-md w-full p-8 text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <h2 className="text-xl font-semibold text-gray-800">Joining League...</h2>
          <p className="text-gray-500 mt-2">Please wait while we add you to the league</p>
        </div>
      </div>
    );
  }

  // Step: Success
  if (step === 'success') {
    return (
      <div className="min-h-screen bg-gray-100 flex items-center justify-center p-4">
        <div className="bg-white rounded-lg shadow-xl max-w-md w-full">
          <div className="p-6 text-center">
            <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
              <svg className="w-8 h-8 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
            </div>
            <h1 className="text-2xl font-bold text-gray-800">You're In!</h1>
            <p className="text-gray-500 mt-2">
              You've successfully joined <strong>{leagueInfo?.name}</strong>
            </p>

            <div className="mt-6 p-4 bg-gray-50 rounded-lg">
              <p className="text-sm text-gray-500">Your Team</p>
              <p className="text-lg font-semibold text-gray-900">{teamName}</p>
            </div>

            <button
              onClick={() => window.location.href = `/league/${leagueInfo?.id}`}
              className="w-full mt-6 py-3 px-4 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors font-medium"
            >
              Go to League
            </button>
          </div>
        </div>
      </div>
    );
  }

  return null;
}
