import Foundation
import Combine

// MARK: - Draft View Model
@MainActor
class DraftViewModel: ObservableObject {
    @Published var players: [Player] = []
    @Published var currentPlayer: Player?
    @Published var currentBid: Double = 0
    @Published var currentBidder: LeagueMember?
    @Published var isDraftActive = false
    @Published var draftTimer: Int = 60
    @Published var bidHistory: [BidHistoryEntry] = []
    @Published var teamBudgets: [String: Double] = [:]
    
    private let draftService = DraftService.shared
    private var cancellables = Set<AnyCancellable>()
    
    init() {
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
    }
    
    func startDraft(members: [LeagueMember]) {
        // Initialize budgets
        for member in members {
            teamBudgets[member.id] = 100.0
        }
        
        bidHistory = []
        draftService.startDraft()
    }
    
    func stopDraft() {
        draftService.stopDraft()
    }
    
    func placeBid(member: LeagueMember, amount: Double) {
        // Check budget
        guard let budget = teamBudgets[member.id], budget >= amount else {
            return
        }
        
        draftService.placeBid(amount: amount, bidder: member)
    }
    
    func confirmSale() {
        guard let bidder = currentBidder else { return }
        
        // Deduct budget
        teamBudgets[bidder.id] = (teamBudgets[bidder.id] ?? 0) - currentBid
        
        // Add to bid history
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
    
    func getBudget(for memberId: String) -> Double {
        teamBudgets[memberId] ?? 0
    }
}

// MARK: - Bid History Entry
struct BidHistoryEntry: Identifiable {
    let id = UUID()
    let playerName: String
    let soldTo: String
    let amount: Double
}
