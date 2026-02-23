import Foundation
import Combine

// MARK: - League Service
class LeagueService {
    static let shared = LeagueService()
    
    @Published var leagues: [League] = []
    @Published var currentLeague: League?
    
    private let api = APIService.shared
    
    private init() {}
    
    // MARK: - Fetch Leagues
    func fetchLeagues() async throws -> [League] {
        let leagueResponses: [LeagueResponse] = try await api.get("/leagues")
        leagues = leagueResponses.map { $0.toLeague() }
        return leagues
    }
    
    // MARK: - Get League Details
    func getLeagueDetails(id: String) async throws -> League {
        let response: LeagueDetailResponse = try await api.get("/leagues/\(id)")
        currentLeague = response.toLeague()
        return currentLeague!
    }
    
    // MARK: - Create League
    func createLeague(name: String, maxTeams: Int = 10, budget: Double = 100.0) async throws -> League {
        let body = CreateLeagueRequest(name: name, maxTeams: maxTeams, auctionBudget: budget)
        let response: LeagueResponse = try await api.post("/leagues", body: body)
        let league = response.toLeague()
        leagues.append(league)
        return league
    }
    
    // MARK: - Join League
    func joinLeague(code: String, teamName: String) async throws -> League {
        let body = JoinLeagueRequest(code: code, teamName: teamName)
        let _: JoinLeagueResponse = try await api.post("/leagues/join", body: body)
        
        // After joining, fetch updated leagues
        let leagueResponses: [LeagueResponse] = try await api.get("/leagues")
        leagues = leagueResponses.map { $0.toLeague() }
        
        // Find and return the joined league
        if let league = leagues.first(where: { $0.code == code.uppercased() }) {
            currentLeague = league
            return league
        }
        
        throw LeagueError.leagueNotFound
    }
    
    // MARK: - Validate Invite Code (Public - no auth required)
    func validateInviteCode(_ code: String) async throws -> InviteValidationResult {
        let response: InviteValidationResponse = try await api.get("/leagues/invite/\(code)", requiresAuth: false)
        return InviteValidationResult(
            valid: response.valid,
            league: response.league.map {
                InviteLeagueInfo(
                    id: $0.id,
                    name: $0.name,
                    code: $0.code,
                    maxTeams: $0.maxTeams,
                    currentTeams: $0.currentTeams,
                    isFull: $0.isFull,
                    status: "open"
                )
            }
        )
    }
    
    // MARK: - Get Invite Link
    func getInviteLink(leagueId: String) async throws -> InviteLink {
        let response: InviteLinkResponse = try await api.get("/leagues/\(leagueId)/invite")
        return InviteLink(
            leagueId: response.leagueId,
            leagueName: response.leagueName,
            code: response.code,
            inviteUrl: response.inviteUrl
        )
    }
    
    // MARK: - Regenerate Invite Code (Commissioner only)
    func regenerateInviteCode(leagueId: String) async throws -> String {
        let response: RegenerateInviteResponse = try await api.post("/leagues/\(leagueId)/invite/regenerate")
        return response.code
    }
    
    // MARK: - Mock Data Methods (for development/testing)
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
        guard let index = leagues.firstIndex(where: { $0.code == code }) else {
            throw LeagueError.leagueNotFound
        }

        guard leagues[index].members.count < leagues[index].maxTeams else {
            throw LeagueError.leagueFull
        }

        guard !leagues[index].members.contains(where: { $0.userId == user.id }) else {
            throw LeagueError.alreadyJoined
        }

        let member = LeagueMember(userId: user.id, user: user, teamName: teamName, budgetRemaining: leagues[index].auctionBudget)
        leagues[index].members.append(member)

        return leagues[index]
    }
    
    func leaveLeague(leagueId: String, userId: String) {
        guard let index = leagues.firstIndex(where: { $0.id == leagueId }) else { return }
        leagues[index].members.removeAll { $0.userId == userId }
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

// MARK: - API Request/Response Models

// Request models
struct CreateLeagueRequest: Encodable {
    let name: String
    let maxTeams: Int
    let auctionBudget: Double
}

struct JoinLeagueRequest: Encodable {
    let code: String
    let teamName: String
}

// Response models
struct LeagueResponse: Decodable {
    let id: String
    let name: String
    let code: String
    let commissionerId: String
    let maxTeams: Int
    let auctionBudget: Double
    let status: String
    let createdAt: String
    let isCommissioner: Bool?
    let teamName: String?
    let memberCount: Int?
    
    func toLeague() -> League {
        let leagueStatus = League.LeagueStatus(rawValue: status) ?? .open
        return League(
            id: id,
            name: name,
            commissionerId: commissionerId,
            maxTeams: maxTeams,
            auctionBudget: auctionBudget,
            createdAt: ISO8601DateFormatter().date(from: createdAt) ?? Date(),
            status: leagueStatus,
            members: []
        )
    }
}

struct LeagueDetailResponse: Decodable {
    let id: String
    let name: String
    let code: String
    let commissionerId: String
    let maxTeams: Int
    let auctionBudget: Double
    let status: String
    let createdAt: String
    let members: [LeagueMemberResponse]
    
    func toLeague() -> League {
        let leagueStatus = League.LeagueStatus(rawValue: status) ?? .open
        let leagueMembers = members.map { member -> LeagueMember in
            LeagueMember(
                id: member.id,
                userId: member.userId,
                user: member.user.map { userResponse in
                    User(
                        id: userResponse.id,
                        email: userResponse.email ?? "",
                        displayName: userResponse.displayName ?? ""
                    )
                },
                teamName: member.teamName,
                isCommissioner: member.isCommissioner,
                budgetRemaining: member.budgetRemaining,
                joinedAt: ISO8601DateFormatter().date(from: member.joinedAt) ?? Date()
            )
        }
        
        return League(
            id: id,
            name: name,
            commissionerId: commissionerId,
            maxTeams: maxTeams,
            auctionBudget: auctionBudget,
            createdAt: ISO8601DateFormatter().date(from: createdAt) ?? Date(),
            status: leagueStatus,
            members: leagueMembers
        )
    }
}

struct LeagueMemberResponse: Decodable {
    let id: String
    let userId: String
    let teamName: String
    let isCommissioner: Bool
    let budgetRemaining: Double
    let joinedAt: String
    let user: UserResponse?
}

struct UserResponse: Decodable {
    let id: String
    let email: String?
    let displayName: String?
    let avatarUrl: String?
}

struct JoinLeagueResponse: Decodable {
    let message: String
    let leagueId: String
}

// Invite validation response
struct InviteValidationResponse: Decodable {
    let valid: Bool
    let league: InviteLeagueResponse?
}

struct InviteLeagueResponse: Decodable {
    let id: String
    let name: String
    let code: String
    let maxTeams: Int
    let currentTeams: Int
    let isFull: Bool
    let status: String
}

struct InviteValidationResult {
    let valid: Bool
    let league: InviteLeagueInfo?
}

// Invite link response
struct InviteLinkResponse: Decodable {
    let leagueId: String
    let leagueName: String
    let code: String
    let inviteUrl: String
}

struct InviteLink {
    let leagueId: String
    let leagueName: String
    let code: String
    let inviteUrl: String
}

// Regenerate invite response
struct RegenerateInviteResponse: Decodable {
    let message: String
    let code: String
}

// MARK: - Invite League Info
struct InviteLeagueInfo: Identifiable {
    let id: String
    let name: String
    let code: String
    let maxTeams: Int
    let currentTeams: Int
    let isFull: Bool
    var status: String
}
