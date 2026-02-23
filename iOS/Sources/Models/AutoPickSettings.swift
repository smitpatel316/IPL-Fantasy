import Foundation

// MARK: - Auto-Pick Settings Model
struct AutoPickSettings: Codable, Identifiable {
    var id: String?
    var leagueId: String
    var leagueName: String?
    var isEnabled: Bool
    var favoritePlayers: [String]
    var preferredRoles: [Player.PlayerRole]
    var maxPrice: Double
    var autoBidEnabled: Bool
    var autoBidIncrement: Double
    
    init(
        id: String? = nil,
        leagueId: String,
        leagueName: String? = nil,
        isEnabled: Bool = false,
        favoritePlayers: [String] = [],
        preferredRoles: [Player.PlayerRole] = [],
        maxPrice: Double = 100.00,
        autoBidEnabled: Bool = false,
        autoBidIncrement: Double = 1.00
    ) {
        self.id = id
        self.leagueId = leagueId
        self.leagueName = leagueName
        self.isEnabled = isEnabled
        self.favoritePlayers = favoritePlayers
        self.preferredRoles = preferredRoles
        self.maxPrice = maxPrice
        self.autoBidEnabled = autoBidEnabled
        self.autoBidIncrement = autoBidIncrement
    }
    
    // Codable enum workaround for preferredRoles
    enum CodingKeys: String, CodingKey {
        case id
        case leagueId = "league_id"
        case leagueName = "league_name"
        case isEnabled = "is_enabled"
        case favoritePlayers = "favorite_players"
        case preferredRoles = "preferred_roles"
        case maxPrice = "max_price"
        case autoBidEnabled = "auto_bid_enabled"
        case autoBidIncrement = "auto_bid_increment"
    }
    
    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        id = try container.decodeIfPresent(String.self, forKey: .id)
        leagueId = try container.decode(String.self, forKey: .leagueId)
        leagueName = try container.decodeIfPresent(String.self, forKey: .leagueName)
        isEnabled = try container.decode(Bool.self, forKey: .isEnabled)
        favoritePlayers = try container.decodeIfPresent([String].self, forKey: .favoritePlayers) ?? []
        maxPrice = try container.decode(Double.self, forKey: .maxPrice)
        autoBidEnabled = try container.decode(Bool.self, forKey: .autoBidEnabled)
        autoBidIncrement = try container.decode(Double.self, forKey: .autoBidIncrement)
        
        // Handle preferred roles - decode as strings then convert
        if let roleStrings = try container.decodeIfPresent([String].self, forKey: .preferredRoles) {
            preferredRoles = roleStrings.compactMap { Player.PlayerRole(rawValue: $0) }
        } else {
            preferredRoles = []
        }
    }
    
    func encode(to encoder: Encoder) throws {
        var container = encoder.container(keyedBy: CodingKeys.self)
        try container.encodeIfPresent(id, forKey: .id)
        try container.encode(leagueId, forKey: .leagueId)
        try container.encodeIfPresent(leagueName, forKey: .leagueName)
        try container.encode(isEnabled, forKey: .isEnabled)
        try container.encode(favoritePlayers, forKey: .favoritePlayers)
        try container.encode(preferredRoles.map { $0.rawValue }, forKey: .preferredRoles)
        try container.encode(maxPrice, forKey: .maxPrice)
        try container.encode(autoBidEnabled, forKey: .autoBidEnabled)
        try container.encode(autoBidIncrement, forKey: .autoBidIncrement)
    }
}

// MARK: - Auto-Pick Trigger Response
struct AutoPickTriggerResponse: Codable {
    let autoPickTriggered: Bool
    let playerId: String?
    let bidAmount: Double?
    let reason: String
    
    enum CodingKeys: String, CodingKey {
        case autoPickTriggered = "auto_pick_triggered"
        case playerId = "player_id"
        case bidAmount = "bid_amount"
        case reason
    }
}
