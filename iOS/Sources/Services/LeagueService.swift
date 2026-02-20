import Foundation

// MARK: - League Service
class LeagueService {
    static let shared = LeagueService()
    
    // Mock data storage
    @Published var leagues: [League] = []
    @Published var currentLeague: League?
    
    private init() {
        // Load mock data
        loadMockData()
    }
    
    func getLeagues() -> [League] {
        leagues
    }
    
    func getLeague(by id: String) -> League? {
        leagues.first { $0.id == id }
    }
    
    func createLeague(name: String, commissionerId: String, maxTeams: Int = 10, budget: Double = 100.0) -> League {
        let league = League(name: name, commissionerId: commissionerId, maxTeams: maxTeams, auctionBudget: budget)
        leagues.append(league)
        return league
    }
    
    func joinLeague(code: String, user: User, teamName: String) throws -> League? {
        guard let league = leagues.first(where: { $0.code == code }) else {
            throw LeagueError.leagueNotFound
        }
        
        guard league.members.count < league.maxTeams else {
            throw LeagueError.leagueFull
        }
        
        guard !league.members.contains(where: { $0.userId == user.id }) else {
            throw LeagueError.alreadyJoined
        }
        
        let member = LeagueMember(userId: user.id, user: user, teamName: teamName, budgetRemaining: league.auctionBudget)
        league.members.append(member)
        
        return league
    }
    
    func leaveLeague(leagueId: String, userId: String) {
        guard let index = leagues.firstIndex(where: { $0.id == leagueId }) else { return }
        leagues[index].members.removeAll { $0.userId == userId }
    }
    
    private func loadMockData() {
        // Add some sample leagues
        let sampleLeague = League(name: "IPL Champions 2024", commissionerId: "system", maxTeams: 8, auctionBudget: 100.0)
        leagues = [sampleLeague]
    }
}

// MARK: - League Errors
enum LeagueError: LocalizedError {
    case leagueNotFound
    case leagueFull
    case alreadyJoined
    case notCommissioner
    
    var errorDescription: String? {
        switch self {
        case .leagueNotFound:
            return "League not found with this code"
        case .leagueFull:
            return "League is full"
        case .alreadyJoined:
            return "You have already joined this league"
        case .notCommissioner:
            return "Only commissioner can perform this action"
        }
    }
}
