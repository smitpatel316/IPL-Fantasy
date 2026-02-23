import Foundation
import Combine

// MARK: - Draft Service
class DraftService {
    static let shared = DraftService()
    
    // Auction draft state
    @Published private(set) var players: [Player] = []
    @Published private(set) var unsoldPlayers: [Player] = []
    @Published private(set) var currentPlayer: Player?
    @Published private(set) var currentBid: Double = 0
    @Published private(set) var currentBidder: LeagueMember?
    
    // Common state
    @Published private(set) var isDraftActive = false
    @Published private(set) var draftTimer: Int = 60
    @Published private(set) var draftType: DraftType = .auction
    
    // Auto-pick state
    private var autoPickSettings: [String: AutoPickSettings] = [:] // leagueId -> settings
    private var currentLeagueId: String = ""
    private var currentUserId: String = ""
    private var currentDraftId: String = ""
    
    // Snake draft state
    @Published private(set) var snakePicks: [SnakePick] = []
    @Published private(set) var currentPickNumber: Int = 0
    @Published private(set) var availablePlayers: [Player] = []
    @Published private(set) var currentPickTeamName: String?
    @Published private(set) var currentPickDisplayName: String?
    
    private var timer: Timer?
    private let timerSubject = PassthroughSubject<Int, Never>()
    private let api = APIService.shared
    private let autoPickService = AutoPickService.shared
    
    // Auto-pick trigger threshold (seconds before timer expires)
    private let autoPickThreshold = 5
    
    var timerPublisher: AnyPublisher<Int, Never> {
        timerSubject.eraseToAnyPublisher()
    }
    
    private init() {
        loadMockPlayers()
    }
    
    // MARK: - Auto-Pick Configuration
    
    func setCurrentLeague(_ leagueId: String, draftId: String) {
        currentLeagueId = leagueId
        currentDraftId = draftId
    }
    
    func setCurrentUser(_ userId: String) {
        currentUserId = userId
    }
    
    func updateAutoPickSettings(_ settings: AutoPickSettings) {
        autoPickSettings[settings.leagueId] = settings
    }
    
    func loadAutoPickSettings(leagueId: String) async {
        do {
            let settings = try await autoPickService.getSettings(leagueId: leagueId)
            autoPickSettings[leagueId] = settings
        } catch {
            print("Failed to load auto-pick settings: \(error)")
        }
    }
    
    // MARK: - Draft Type
    
    func setDraftType(_ type: DraftType) {
        draftType = type
    }
    
    // MARK: - Auction Draft Methods
    
    func startAuctionDraft() {
        guard !isDraftActive else { return }
        
        isDraftActive = true
        draftType = .auction
        unsoldPlayers = players.filter { !$0.isSold }
        nextPlayer()
        startTimer()
    }
    
    func stopDraft() {
        isDraftActive = false
        timer?.invalidate()
        timer = nil
    }
    
    func placeBid(amount: Double, bidder: LeagueMember) -> Bool {
        guard amount > currentBid else { return false }
        
        guard let budget = getMemberBudget(bidder.id), budget >= amount else { return false }
        
        currentBid = amount
        currentBidder = bidder
        resetTimer()
        return true
    }
    
    private func getMemberBudget(_ memberId: String) -> Double? {
        return 100.0
    }
    
    func soldPlayer(to member: LeagueMember) -> Bool {
        guard var player = currentPlayer else { return false }
        
        player.isSold = true
        player.currentBid = currentBid
        player.ownerId = member.userId
        
        if let index = players.firstIndex(where: { $0.id == player.id }) {
            players[index] = player
        }
        
        nextPlayer()
        return true
    }
    
    func unsoldPlayer() -> Bool {
        guard var player = currentPlayer else { return false }
        
        player.isSold = true
        player.currentBid = 0
        
        if let index = players.firstIndex(where: { $0.id == player.id }) {
            players[index] = player
        }
        
        nextPlayer()
        return true
    }
    
    private func nextPlayer() {
        guard !unsoldPlayers.isEmpty else {
            stopDraft()
            currentPlayer = nil
            currentBid = 0
            currentBidder = nil
            return
        }
        
        currentPlayer = unsoldPlayers.removeFirst()
        currentBid = currentPlayer?.basePrice ?? 0
        currentBidder = nil
        resetTimer()
    }
    
    // MARK: - Snake Draft API Methods
    
    func fetchDraftType(leagueId: String) async throws -> DraftType {
        let response: DraftTypeResponse = try await api.get("/drafts/league/\(leagueId)/type")
        return DraftType(rawValue: response.draftType) ?? .auction
    }
    
    func setDraftType(leagueId: String, type: DraftType) async throws {
        let body = SetDraftTypeRequest(draftType: type.rawValue)
        let _: DraftTypeResponse = try await api.post("/drafts/league/\(leagueId)/type", body: body)
        draftType = type
    }
    
    func fetchSnakePicks(leagueId: String) async throws {
        let response: SnakePicksResponse = try await api.get("/drafts/league/\(leagueId)/picks")
        
        self.snakePicks = response.picks
        self.availablePlayers = response.availablePlayers
        self.currentPickNumber = response.currentPickNumber ?? 0
        
        if let currentPick = response.currentPick {
            self.currentPickTeamName = currentPick.teamName
            self.currentPickDisplayName = currentPick.displayName
        }
        
        self.isDraftActive = response.draftStatus == "active"
    }
    
    func startSnakeDraft(leagueId: String) async throws {
        // First set the draft type to snake
        try await setDraftType(leagueId: leagueId, type: .snake)
        
        // Then start the draft
        let response: DraftResponse = try await api.post("/drafts/league/\(leagueId)/start")
        
        isDraftActive = response.status == "active"
        draftType = .snake
        
        // Fetch picks
        try await fetchSnakePicks(leagueId: leagueId)
    }
    
    func makeSnakePick(playerId: String, leagueId: String) async throws {
        guard !currentDraftId.isEmpty else { return }
        
        let _: MakePickResponse = try await api.post("/drafts/\(currentDraftId)/pick", body: MakePickRequest(playerId: playerId))
        
        // Refresh picks after making one
        try await fetchSnakePicks(leagueId: leagueId)
    }
    
    func skipSnakePick(leagueId: String) async throws {
        guard !currentDraftId.isEmpty else { return }
        
        let _: SkipPickResponse = try await api.post("/drafts/\(currentDraftId)/skip-pick")
        
        // Refresh picks
        try await fetchSnakePicks(leagueId: leagueId)
    }
    
    // MARK: - Local Snake Draft (for mock/offline)
    
    func startSnakeDraftLocal() {
        guard !isDraftActive else { return }
        
        isDraftActive = true
        draftType = .snake
        loadMockPlayers()
        availablePlayers = players
        generateMockSnakePicks()
    }
    
    private func generateMockSnakePicks() {
        // Generate 15 rounds x 4 teams = 60 picks
        snakePicks = []
        let teams = ["Team A", "Team B", "Team C", "Team D"]
        
        for round in 1...15 {
            for position in 0..<4 {
                let pickNumber = (round - 1) * 4 + position + 1
                let isForward = round % 2 == 1
                let teamPosition = isForward ? position : (3 - position)
                
                snakePicks.append(SnakePick(
                    id: UUID().uuidString,
                    pickNumber: pickNumber,
                    round: round,
                    teamPosition: teamPosition,
                    leagueMemberId: nil,
                    playerId: nil,
                    teamName: teams[teamPosition],
                    displayName: nil,
                    playerName: nil,
                    playerRole: nil,
                    playerTeam: nil,
                    isDrafting: pickNumber == 1,
                    isSkipped: false
                ))
            }
        }
    }
    
    func makePick(playerId: String, draftId: String) async throws {
        guard draftType == .snake else { return }
        
        // In production, this would call the API
        // For now, simulate the pick locally
        if let playerIndex = availablePlayers.firstIndex(where: { $0.id == playerId }) {
            let player = availablePlayers.remove(at: playerIndex)
            
            // Update picks
            if currentPickNumber < snakePicks.count {
                snakePicks[currentPickNumber].playerId = playerId
                snakePicks[currentPickNumber].playerName = player.name
                snakePicks[currentPickNumber].playerRole = player.role.displayName
                snakePicks[currentPickNumber].playerTeam = player.team
            }
            
            currentPickNumber += 1
        }
    }
    
    // MARK: - Timer
    
    private func startTimer() {
        timer?.invalidate()
        
        timer = Timer.scheduledTimer(withTimeInterval: 1.0, repeats: true) { [weak self] _ in
            guard let self = self else { return }
            
            Task { @MainActor in
                self.draftTimer -= 1
                self.timerSubject.send(self.draftTimer)
                
                // Check for auto-pick trigger (when timer is about to expire)
                if self.draftTimer == self.autoPickThreshold && self.draftType == .auction {
                    await self.triggerAutoPickIfEnabled()
                }
                
                if self.draftTimer <= 0 && self.draftType == .auction {
                    if let bidder = self.currentBidder {
                        _ = self.soldPlayer(to: bidder)
                    } else {
                        _ = self.unsoldPlayer()
                    }
                }
            }
        }
    }
    
    private func triggerAutoPickIfEnabled() async {
        guard !currentLeagueId.isEmpty,
              !currentDraftId.isEmpty,
              let player = currentPlayer else { return }
        
        // Check if auto-pick is enabled for this league
        guard let settings = autoPickSettings[currentLeagueId], 
              settings.isEnabled else { return }
        
        // Check if player matches preferences
        let isFavorite = settings.favoritePlayers.contains(player.id)
        let isPreferredRole = settings.preferredRoles.isEmpty || 
            settings.preferredRoles.contains(player.role)
        let withinBudget = player.basePrice <= settings.maxPrice
        
        let shouldAutoPick = isFavorite || (isPreferredRole && withinBudget)
        
        if shouldAutoPick {
            do {
                let response = try await autoPickService.triggerAutoPick(
                    leagueId: currentLeagueId,
                    draftId: currentDraftId,
                    playerId: player.id
                )
                
                if response.autoPickTriggered {
                    print("Auto-pick triggered for \(player.name): \(response.reason)")
                } else {
                    print("Auto-pick not triggered: \(response.reason)")
                }
            } catch {
                print("Auto-pick error: \(error)")
            }
        }
    }
    
    private func resetTimer() {
        draftTimer = 60
    }
    
    func resetForTesting() {
        stopDraft()
        draftTimer = 60
        currentBid = 0
        currentBidder = nil
        currentPickNumber = 0
        snakePicks = []
        loadMockPlayers()
    }
    
    private func loadMockPlayers() {
        players = [
            Player(name: "Virat Kohli", role: .batsman, team: "RCB", basePrice: 18.0),
            Player(name: "Rohit Sharma", role: .batsman, team: "MI", basePrice: 18.0),
            Player(name: "Jasprit Bumrah", role: .bowler, team: "MI", basePrice: 18.0),
            Player(name: "Shubman Gill", role: .batsman, team: "GT", basePrice: 16.0),
            Player(name: "KL Rahul", role: .wicketKeeper, team: "LSG", basePrice: 14.0),
            Player(name: "Hardik Pandya", role: .allRounder, team: "GT", basePrice: 14.0),
            Player(name: "Ravindra Jadeja", role: .allRounder, team: "CSK", basePrice: 14.0),
            Player(name: "Suryakumar Yadav", role: .batsman, team: "MI", basePrice: 12.0),
            Player(name: "Mohammed Siraj", role: .bowler, team: "RCB", basePrice: 10.0),
            Player(name: "Andre Russell", role: .allRounder, team: "KKR", basePrice: 12.0),
        ]
        
        unsoldPlayers = players
        availablePlayers = players
    }
}

// MARK: - API Request/Response Models

struct DraftTypeResponse: Codable {
    let id: String?
    let draftType: String
    let status: String?
    
    enum CodingKeys: String, CodingKey {
        case id, status
        case draftType = "draft_type"
    }
}

struct SetDraftTypeRequest: Codable {
    let draftType: String
    
    enum CodingKeys: String, CodingKey {
        case draftType = "draft_type"
    }
}

struct MakePickRequest: Codable {
    let playerId: String
    
    enum CodingKeys: String, CodingKey {
        case playerId = "player_id"
    }
}

struct MakePickResponse: Codable {
    let success: Bool
}

struct SkipPickResponse: Codable {
    let success: Bool
}

// MARK: - Draft Types
enum DraftType: String, Codable {
    case auction
    case snake
    case linear
}

// MARK: - Snake Pick
struct SnakePick: Codable, Identifiable {
    let id: String
    let pickNumber: Int
    let teamId: String
    let teamName: String
    let playerId: String?
    let playerName: String?
    let isCompleted: Bool

    enum CodingKeys: String, CodingKey {
        case id
        case pickNumber = "pick_number"
        case teamId = "team_id"
        case teamName = "team_name"
        case playerId = "player_id"
        case playerName = "player_name"
        case isCompleted = "is_completed"
    }
}

// MARK: - Auto Pick Settings
struct AutoPickSettings: Codable {
    var leagueId: String = ""
    var isEnabled: Bool
    var preferredRoles: [String]
    var maxPrice: Double
    var minProjectedPoints: Int
    var priorityStrategy: String

    init(leagueId: String = "") {
        self.leagueId = leagueId
        self.isEnabled = false
        self.preferredRoles = []
        self.maxPrice = 10.0
        self.minProjectedPoints = 0
        self.priorityStrategy = "projected_points"
    }
}

// MARK: - Auto Pick Service
class AutoPickService {
    static let shared = AutoPickService()
    private var settings: [String: AutoPickSettings] = [:]

    private init() {}

    func getSettings(forLeague leagueId: String) -> AutoPickSettings {
        return settings[leagueId] ?? AutoPickSettings()
    }

    func saveSettings(_ settings: AutoPickSettings, forLeague leagueId: String) {
        self.settings[leagueId] = settings
    }

    func selectPlayer(from players: [Player], with settings: AutoPickSettings) -> Player? {
        let filtered = players.filter { player in
            player.basePrice <= settings.maxPrice &&
            player.totalPoints >= settings.minProjectedPoints
        }
        return filtered.max(by: { $0.totalPoints < $1.totalPoints })
    }
}
