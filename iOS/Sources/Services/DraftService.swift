import Foundation
import Combine

// MARK: - Draft Service
class DraftService {
    static let shared = DraftService()
    
    @Published var players: [Player] = []
    @Published var unsoldPlayers: [Player] = []
    @Published var currentPlayer: Player?
    @Published var currentBid: Double = 0
    @Published var currentBidder: LeagueMember?
    @Published var isDraftActive = false
    @Published var draftTimer: Int = 60
    
    private var timer: Timer?
    
    private init() {
        loadMockPlayers()
    }
    
    func startDraft() {
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
    
    func placeBid(amount: Double, bidder: LeagueMember) {
        guard amount > currentBid else { return }
        currentBid = amount
        currentBidder = bidder
        resetTimer()
    }
    
    func soldPlayer(to member: LeagueMember) {
        guard var player = currentPlayer else { return }
        
        player.isSold = true
        player.currentBid = currentBid
        player.ownerId = member.userId
        
        if let index = players.firstIndex(where: { $0.id == player.id }) {
            players[index] = player
        }
        
        nextPlayer()
    }
    
    func unsoldPlayer() {
        guard var player = currentPlayer else { return }
        
        player.isSold = true
        player.currentBid = 0
        
        if let index = players.firstIndex(where: { $0.id == player.id }) {
            players[index] = player
        }
        
        nextPlayer()
    }
    
    private func nextPlayer() {
        guard !unsoldPlayers.isEmpty else {
            stopDraft()
            currentPlayer = nil
            return
        }
        
        currentPlayer = unsoldPlayers.removeFirst()
        currentBid = currentPlayer?.basePrice ?? 0
        currentBidder = nil
        resetTimer()
    }
    
    private func startTimer() {
        timer = Timer.scheduledTimer(withTimeInterval: 1.0, repeats: true) { [weak self] _ in
            Task { @MainActor in
                self?.draftTimer -= 1
                if self?.draftTimer == 0 {
                    // Auto-sold to current bidder or unsold
                    if self?.currentBidder != nil {
                        self?.soldPlayer(to: self!.currentBidder!)
                    } else {
                        self?.unsoldPlayer()
                    }
                }
            }
        }
    }
    
    private func resetTimer() {
        draftTimer = 60
    }
    
    private func loadMockPlayers() {
        players = [
            // Star Batsmen
            Player(name: "Virat Kohli", role: .batsman, team: "RCB", basePrice: 18.0),
            Player(name: "Rohit Sharma", role: .batsman, team: "MI", basePrice: 18.0),
            Player(name: "Shubman Gill", role: .batsman, team: "GT", basePrice: 16.0),
            Player(name: "KL Rahul", role: .wicketKeeper, team: "LSG", basePrice: 14.0),
            Player(name: "Ruturaj Gaikwad", role: .batsman, team: "CSK", basePrice: 12.0),
            Player(name: "Shreyas Iyer", role: .batsman, team: "KKR", basePrice: 12.0),
            Player(name: "David Warner", role: .batsman, team: "DC", basePrice: 12.0),
            Player(name: "Faf du Plessis", role: .batsman, team: "RCB", basePrice: 12.0),
            
            // All Rounders
            Player(name: "Hardik Pandya", role: .allRounder, team: "MI", basePrice: 16.0),
            Player(name: "Ravichandran Ashwin", role: .allRounder, team: "RR", basePrice: 12.0),
            Player(name: "Andre Russell", role: .allRounder, team: "KKR", basePrice: 12.0),
            Player(name: "Sunil Narine", role: .allRounder, team: "KKR", basePrice: 10.0),
            Player(name: "Axar Patel", role: .allRounder, team: "DC", basePrice: 10.0),
            Player(name: "Shardul Thakur", role: .allRounder, team: "DC", basePrice: 8.0),
            Player(name: "Mohammed Siraj", role: .allRounder, team: "RCB", basePrice: 8.0),
            
            // Bowlers
            Player(name: "Jasprit Bumrah", role: .bowler, team: "MI", basePrice: 18.0),
            Player(name: "Mohammed Shami", role: .bowler, team: "GT", basePrice: 14.0),
            Player(name: "Rashid Khan", role: .bowler, team: "GT", basePrice: 14.0),
            Player(name: "Bhuvneshwar Kumar", role: .bowler, team: "SRH", basePrice: 12.0),
            Player(name: "Kuldeep Yadav", role: .bowler, team: "DC", basePrice: 10.0),
            Player(name: "Yuzvendra Chahal", role: .bowler, team: "RR", basePrice: 10.0),
            Player(name: "Prasidh Krishna", role: .bowler, team: "GT", basePrice: 8.0),
            Player(name: "Avesh Khan", role: .bowler, team: "LSG", basePrice: 8.0),
            
            // Wicket Keepers
            Player(name: "MS Dhoni", role: .wicketKeeper, team: "CSK", basePrice: 12.0),
            Player(name: "Ishan Kishan", role: .wicketKeeper, team: "MI", basePrice: 12.0),
            Player(name: "Sanju Samson", role: .wicketKeeper, team: "RR", basePrice: 10.0),
            Player(name: "Rishabh Pant", role: .wicketKeeper, team: "DC", basePrice: 14.0),
            
            // More Batsmen
            Player(name: "Suryakumar Yadav", role: .batsman, team: "MI", basePrice: 14.0),
            Player(name: "Tilak Varma", role: .batsman, team: "MI", basePrice: 8.0),
            Player(name: "Riyan Parvar", role: .batsman, team: "RR", basePrice: 6.0),
            Player(name: "Abhishek Sharma", role: .batsman, team: "SRH", basePrice: 6.0),
        ]
        
        unsoldPlayers = players
    }
}
