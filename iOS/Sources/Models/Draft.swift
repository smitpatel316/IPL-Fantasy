import Foundation

// MARK: - Snake Pick Model
struct SnakePick: Identifiable, Codable, Hashable {
    let id: String
    let pickNumber: Int
    let round: Int
    let teamPosition: Int
    var leagueMemberId: String?
    var playerId: String?
    var teamName: String?
    var displayName: String?
    var playerName: String?
    var playerRole: String?
    var playerTeam: String?
    var isDrafting: Bool
    var isSkipped: Bool
    
    var isMade: Bool {
        playerId != nil
    }
}

// MARK: - Draft Type
enum DraftType: String, Codable {
    case auction
    case snake
}

// MARK: - Draft Response (from API)
struct DraftResponse: Codable {
    let id: String
    let leagueId: String
    let draftType: String?
    let status: String
    let currentPickNumber: Int?
    let currentPlayer: Player?
    let currentBid: Double?
    let currentBidder: LeagueMember?
    let timerSeconds: Int?
    let createdAt: String?
    
    enum CodingKeys: String, CodingKey {
        case id, leagueId, status, currentPlayer, currentBid, currentBidder, createdAt
        case draftType = "draft_type"
        case currentPickNumber = "current_pick_number"
        case timerSeconds = "timer_seconds"
    }
}

// MARK: - Snake Draft Picks Response
struct SnakePicksResponse: Codable {
    let draftId: String
    let draftStatus: String
    let currentPickNumber: Int?
    let currentPick: SnakePick?
    let picks: [SnakePick]
    let availablePlayers: [Player]
}
