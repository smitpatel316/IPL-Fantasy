import Foundation
import Combine

// MARK: - Draft Service
class DraftService {
    static let shared = DraftService()
    
    @Published private(set) var players: [Player] = []
    @Published private(set) var unsoldPlayers: [Player] = []
    @Published private(set) var currentPlayer: Player?
    @Published private(set) var currentBid: Double = 0
    @Published private(set) var currentBidder: LeagueMember?
    @Published private(set) var isDraftActive = false
    @Published private(set) var draftTimer: Int = 60
    
    private var timer: Timer?
    private let timerSubject = PassthroughSubject<Int, Never>()
    
    var timerPublisher: AnyPublisher<Int, Never> {
        timerSubject.eraseToAnyPublisher()
    }
    
    private init() {
        loadMockPlayers()
    }
    
    func startDraft() {
        guard !isDraftActive else { return }
        
        isDraftActive = true
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
        
        // Find bidder's budget from league members
        guard let budget = getMemberBudget(bidder.id), budget >= amount else { return false }
        
        currentBid = amount
        currentBidder = bidder
        resetTimer()
        return true
    }
    
    private func getMemberBudget(_ memberId: String) -> Double? {
        // In production, would query from league members
        // For now, return a default
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
    
    private func startTimer() {
        timer?.invalidate()
        
        timer = Timer.scheduledTimer(withTimeInterval: 1.0, repeats: true) { [weak self] _ in
            guard let self = self else { return }
            
            Task { @MainActor in
                self.draftTimer -= 1
                self.timerSubject.send(self.draftTimer)
                
                if self.draftTimer <= 0 {
                    // Auto-sold to current bidder or unsold
                    if let bidder = self.currentBidder {
                        _ = self.soldPlayer(to: bidder)
                    } else {
                        _ = self.unsoldPlayer()
                    }
                }
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
        loadMockPlayers()
    }
    
    private func loadMockPlayers() {
        players = [
            Player(name: "Virat Kohli", role: .batsman, team: "RCB", basePrice: 18.0),
            Player(name: "Rohit Sharma", role: .batsman, team: "MI", basePrice: 18.0),
            Player(name: "Jasprit Bumrah", role: .bowler, team: "MI", basePrice: 18.0),
            Player(name: "Shubman Gill", role: .batsman, team: "GT", basePrice: 16.0),
            Player(name: "KL Rahul", role: .wicketKeeper, team: "LSG", basePrice: 14.0),
        ]
        
        unsoldPlayers = players
    }
}
