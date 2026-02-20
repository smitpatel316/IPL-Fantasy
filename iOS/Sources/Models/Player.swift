import Foundation

// MARK: - Player Model
struct Player: Identifiable, Codable, Hashable {
    let id: String
    var name: String
    var role: PlayerRole
    var team: String
    var imageURL: String?
    var basePrice: Double
    var currentBid: Double?
    var isSold: Bool
    var ownerId: String?
    var stats: PlayerStats?
    
    enum PlayerRole: String, Codable, CaseIterable {
        case batsman = "BAT"
        case bowler = "BOWL"
        case allRounder = "AR"
        case wicketKeeper = "WK"
        
        var displayName: String {
            switch self {
            case .batsman: return "Batsman"
            case .bowler: return "Bowler"
            case .allRounder: return "All-Rounder"
            case .wicketKeeper: return "Wicket Keeper"
            }
        }
        
        var color: String {
            switch self {
            case .batsman: return "4CAF50"
            case .bowler: return "F44336"
            case .allRounder: return "9C27B0"
            case .wicketKeeper: return "2196F3"
            }
        }
    }
    
    init(id: String = UUID().uuidString, name: String, role: PlayerRole, team: String, basePrice: Double, imageURL: String? = nil) {
        self.id = id
        self.name = name
        self.role = role
        self.team = team
        self.basePrice = basePrice
        self.imageURL = imageURL
        self.isSold = false
        self.currentBid = nil
        self.ownerId = nil
        self.stats = nil
    }
}

// MARK: - Player Stats
struct PlayerStats: Codable, Hashable {
    var matches: Int
    var runs: Int
    var wickets: Int
    var average: Double
    var strikeRate: Double
    
    init(matches: Int = 0, runs: Int = 0, wickets: Int = 0) {
        self.matches = matches
        self.runs = runs
        self.wickets = wickets
        self.average = runs > 0 ? Double(runs) / Double(max(matches, 1)) : 0
        self.strikeRate = 0
    }
}

// MARK: - Team (User's fantasy team)
struct Team: Identifiable, Codable {
    let id: String
    var userId: String
    var leagueId: String
    var name: String
    var players: [TeamPlayer]
    var captainId: String?
    var viceCaptainId: String?
    var totalPoints: Double
    
    init(id: String = UUID().uuidString, userId: String, leagueId: String, name: String) {
        self.id = id
        self.userId = userId
        self.leagueId = leagueId
        self.name = name
        self.players = []
        self.totalPoints = 0
    }
    
    var playingXI: [TeamPlayer] {
        Array(players.prefix(11))
    }
    
    var bench: [TeamPlayer] {
        Array(players.suffix(from: min(11, players.count)))
    }
}

// MARK: - Team Player
struct TeamPlayer: Identifiable, Codable, Hashable {
    let id: String
    let playerId: String
    var player: Player
    var purchasePrice: Double
    var isPlaying: Bool
    var isCaptain: Bool
    var isViceCaptain: Bool
    
    init(player: Player, price: Double) {
        self.id = UUID().uuidString
        self.playerId = player.id
        self.player = player
        self.purchasePrice = price
        self.isPlaying = false
        self.isCaptain = false
        self.isViceCaptain = false
    }
}
