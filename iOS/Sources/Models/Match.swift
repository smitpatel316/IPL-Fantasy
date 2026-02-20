import Foundation

// MARK: - Match Model
struct Match: Identifiable, Codable {
    let id: String
    var team1: String
    var team2: String
    var matchDate: Date
    var venue: String
    var status: MatchStatus
    var currentInning: Int
    var scores: MatchScore?
    
    enum MatchStatus: String, Codable {
        case scheduled
        case live
        case completed
    }
    
    init(id: String = UUID().uuidString, team1: String, team2: String, matchDate: Date, venue: String) {
        self.id = id
        self.team1 = team1
        self.team2 = team2
        self.matchDate = matchDate
        self.venue = venue
        self.status = .scheduled
        self.currentInning = 1
    }
    
    var displayTitle: String {
        "\(team1) vs \(team2)"
    }
}

// MARK: - Match Score
struct MatchScore: Codable {
    var team1Runs: Int
    var team1Wickets: Int
    var team1Overs: Double
    var team2Runs: Int
    var team2Wickets: Int
    var team2Overs: Double
    var target: Int?
    
    var team1Display: String {
        "\(team1Runs)/\(team1Wickets) (\(String(format: "%.1f", team1Overs)))"
    }
    
    var team2Display: String {
        "\(team2Runs)/\(team2Wickets) (\(String(format: "%.1f", team2Overs)))"
    }
}

// MARK: - Matchup (Fantasy contest between two teams)
struct Matchup: Identifiable, Codable {
    let id: String
    var leagueId: String
    var matchId: String
    var team1Id: String
    var team2Id: String
    var team1Points: Double
    var team2Points: Double
    var week: Int
    var isCompleted: Bool
    
    init(id: String = UUID().uuidString, leagueId: String, matchId: String, team1Id: String, team2Id: String, week: Int) {
        self.id = id
        self.leagueId = leagueId
        self.matchId = matchId
        self.team1Id = team1Id
        self.team2Id = team2Id
        self.team1Points = 0
        self.team2Points = 0
        self.week = week
        self.isCompleted = false
    }
}

// MARK: - Weekly Score
struct WeeklyScore: Identifiable, Codable {
    let id: String
    var teamId: String
    var week: Int
    var points: Double
    var wins: Int
    var losses: Int
    var ties: Int
    var categoryWins: [String]
    
    init(id: String = UUID().uuidString, teamId: String, week: Int) {
        self.id = id
        self.teamId = teamId
        self.week = week
        self.points = 0
        self.wins = 0
        self.losses = 0
        self.ties = 0
        self.categoryWins = []
    }
}

// MARK: - Standings Entry
struct StandingsEntry: Identifiable {
    let id = UUID()
    var rank: Int
    var teamName: String
    var userName: String
    var wins: Int
    var losses: Int
    var ties: Int
    var totalPoints: Double
}
