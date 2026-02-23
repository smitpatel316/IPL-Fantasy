import Foundation
import Combine

// MARK: - Draft View Model
@MainActor
class DraftViewModel: ObservableObject {
    // Auction draft state
    @Published var players: [Player] = []
    @Published var currentPlayer: Player?
    @Published var currentBid: Double = 0
    @Published var currentBidder: LeagueMember?
    
    // Common state
    @Published var isDraftActive = false
    @Published var draftTimer: Int = 60
    @Published var bidHistory: [BidHistoryEntry] = []
    @Published var teamBudgets: [String: Double] = [:]
    @Published var draftType: DraftType = .auction
    
    // Snake draft state
    @Published var snakePicks: [SnakePick] = []
    @Published var currentPickNumber: Int = 0
    @Published var availablePlayers: [Player] = []
    @Published var currentPickTeamName: String?
    @Published var currentPickDisplayName: String?
    
    private let draftService = DraftService.shared
    private var cancellables = Set<AnyCancellable>()
    
    init() {
        // Auction state bindings
        draftService.$players
            .receive(on: DispatchQueue.main)
            .assign(to: &$players)
        
        draftService.$currentPlayer
            .receive(on: DispatchQueue.main)
            .assign(to: &$currentPlayer)
        
        draftService.$currentBid
            .receive(on: DispatchQueue.main)
            .assign(to: &$currentBid)
        
        draftService.$currentBidder
            .receive(on: DispatchQueue.main)
            .assign(to: &$currentBidder)
        
        draftService.$isDraftActive
            .receive(on: DispatchQueue.main)
            .assign(to: &$isDraftActive)
        
        draftService.$draftTimer
            .receive(on: DispatchQueue.main)
            .assign(to: &$draftTimer)
        
        draftService.$draftType
            .receive(on: DispatchQueue.main)
            .assign(to: &$draftType)
        
        // Snake draft bindings
        draftService.$snakePicks
            .receive(on: DispatchQueue.main)
            .assign(to: &$snakePicks)
        
        draftService.$currentPickNumber
            .receive(on: DispatchQueue.main)
            .assign(to: &$currentPickNumber)
        
        draftService.$availablePlayers
            .receive(on: DispatchQueue.main)
            .assign(to: &$availablePlayers)
        
        draftService.$currentPickTeamName
            .receive(on: DispatchQueue.main)
            .assign(to: &$currentPickTeamName)
        
        draftService.$currentPickDisplayName
            .receive(on: DispatchQueue.main)
            .assign(to: &$currentPickDisplayName)
    }
    
    // MARK: - Draft Control
    
    @MainActor
    func startDraft(members: [LeagueMember], type: DraftType = .auction, leagueId: String = "") {
        // Initialize budgets
        for member in members {
            teamBudgets[member.id] = 100.0
        }
        
        bidHistory = []
        
        if type == .snake {
            if !leagueId.isEmpty {
                Task {
                    do {
                        try await draftService.startSnakeDraft(leagueId: leagueId)
                    } catch {
                        print("Error starting snake draft: \(error)")
                        // Fall back to local
                        draftService.startSnakeDraftLocal()
                    }
                }
            } else {
                draftService.startSnakeDraftLocal()
            }
        } else {
            draftService.setDraftType(.auction)
            draftService.startAuctionDraft()
        }
    }
    
    func stopDraft() {
        draftService.stopDraft()
    }
    
    // MARK: - API Integration
    
    @MainActor
    func loadDraftState(leagueId: String) async {
        do {
            let type = try await draftService.fetchDraftType(leagueId: leagueId)
            draftType = type
            
            if type == .snake {
                try await draftService.fetchSnakePicks(leagueId: leagueId)
            }
        } catch {
            print("Error loading draft state: \(error)")
        }
    }
    
    // MARK: - Auction Methods
    
    func placeBid(member: LeagueMember, amount: Double) {
        guard let budget = teamBudgets[member.id], budget >= amount else {
            return
        }
        
        draftService.placeBid(amount: amount, bidder: member)
    }
    
    func confirmSale() {
        guard let bidder = currentBidder else { return }
        
        teamBudgets[bidder.id] = (teamBudgets[bidder.id] ?? 0) - currentBid
        
        if let player = currentPlayer {
            let entry = BidHistoryEntry(
                playerName: player.name,
                soldTo: bidder.teamName,
                amount: currentBid
            )
            bidHistory.insert(entry, at: 0)
        }
        
        draftService.soldPlayer(to: bidder)
    }
    
    func markUnsold() {
        if let player = currentPlayer {
            let entry = BidHistoryEntry(
                playerName: player.name,
                soldTo: "Unsold",
                amount: 0
            )
            bidHistory.insert(entry, at: 0)
        }
        
        draftService.unsoldPlayer()
    }
    
    // MARK: - Snake Draft Methods
    
    @MainActor
    func makePick(playerId: String, leagueId: String) async {
        do {
            try await draftService.makeSnakePick(playerId: playerId, leagueId: leagueId)
        } catch {
            print("Error making pick: \(error)")
        }
    }
    
    @MainActor
    func skipPick(leagueId: String) async {
        do {
            try await draftService.skipSnakePick(leagueId: leagueId)
        } catch {
            print("Error skipping pick: \(error)")
        }
    }
    
    // MARK: - Helpers
    
    func getBudget(for memberId: String) -> Double {
        teamBudgets[memberId] ?? 0
    }
    
    func isSnakeDraft() -> Bool {
        draftType == .snake
    }
}

// MARK: - Bid History Entry
struct BidHistoryEntry: Identifiable {
    let id = UUID()
    let playerName: String
    let soldTo: String
    let amount: Double
}
