import Foundation

// MARK: - User Model
struct User: Identifiable, Codable {
    let id: String
    var email: String
    var displayName: String
    var avatarURL: String?
    var createdAt: Date
    
    init(id: String = UUID().uuidString, email: String, displayName: String, avatarURL: String? = nil) {
        self.id = id
        self.email = email
        self.displayName = displayName
        self.avatarURL = avatarURL
        self.createdAt = Date()
    }
}

// MARK: - League Model
struct League: Identifiable, Codable {
    let id: String
    var name: String
    var code: String
    var commissionerId: String
    var maxTeams: Int
    var auctionBudget: Double
    var createdAt: Date
    var status: LeagueStatus
    var members: [LeagueMember]
    
    enum LeagueStatus: String, Codable {
        case open
        case drafting
        case active
        case completed
    }
    
    init(id: String = UUID().uuidString, name: String, commissionerId: String, maxTeams: Int = 10, auctionBudget: Double = 100.0, createdAt: Date = Date(), status: LeagueStatus = .open, members: [LeagueMember] = []) {
        self.id = id
        self.name = name
        self.code = League.generateCode()
        self.commissionerId = commissionerId
        self.maxTeams = maxTeams
        self.auctionBudget = auctionBudget
        self.createdAt = createdAt
        self.status = status
        self.members = members
    }
    
    private static func generateCode() -> String {
        let characters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
        return String((0..<6).map { _ in characters.randomElement()! })
    }
}

// MARK: - League Member
struct LeagueMember: Identifiable, Codable {
    let id: String
    let userId: String
    var user: User?
    var teamName: String
    var budgetRemaining: Double
    var isCommissioner: Bool
    var joinedAt: Date
    
    init(id: String = UUID().uuidString, userId: String, user: User? = nil, teamName: String, isCommissioner: Bool = false, budgetRemaining: Double = 100.0, joinedAt: Date = Date()) {
        self.id = id
        self.userId = userId
        self.user = user
        self.teamName = teamName
        self.isCommissioner = isCommissioner
        self.budgetRemaining = budgetRemaining
        self.joinedAt = joinedAt
    }
}
