import React, { useState } from 'react';
import LeagueInvite from './components/LeagueInvite';
import JoinLeague from './pages/JoinLeague';

// Demo App component that shows the League Invite System
function App() {
  const [view, setView] = useState('invite'); // 'invite' or 'join'
  const [leagueId] = useState('demo-league-id');
  const [leagueName] = useState('IPL Champions League 2026');

  return (
    <div className="min-h-screen bg-gray-100 flex flex-col items-center justify-center p-4">
      {/* Navigation */}
      <div className="mb-8 flex gap-4">
        <button
          onClick={() => setView('invite')}
          className={`px-4 py-2 rounded-lg font-medium transition-colors ${
            view === 'invite' 
              ? 'bg-blue-600 text-white' 
              : 'bg-white text-gray-700 hover:bg-gray-50'
          }`}
        >
          Invite Players (Commissioner)
        </button>
        <button
          onClick={() => setView('join')}
          className={`px-4 py-2 rounded-lg font-medium transition-colors ${
            view === 'join' 
              ? 'bg-blue-600 text-white' 
              : 'bg-white text-gray-700 hover:bg-gray-50'
          }`}
        >
          Join League (Player)
        </button>
      </div>

      {/* Demo Views */}
      {view === 'invite' ? (
        <LeagueInvite 
          leagueId={leagueId}
          leagueName={leagueName}
        />
      ) : (
        <JoinLeague 
          onJoinComplete={(leagueId) => console.log('Joined league:', leagueId)}
        />
      )}
    </div>
  );
}

export default App;
