import Foundation
import Combine

// MARK: - Team View Model
@MainActor
class TeamViewModel: ObservableObject {
    @Published var squad: [Player] = []
    @Published var captain: Player?
    @Published var viceCaptain: Player?
    @Published var isLoading = false
    
    init() {
        loadMockSquad()
    }
    
    func loadMockSquad() {
        squad = [
            Player(name: "Rohit Sharma", role: .batsman, team: "MI", basePrice: 18, totalPoints: 245),
            Player(name: "Jasprit Bumrah", role: .bowler, team: "MI", basePrice: 18, totalPoints: 312),
            Player(name: "Hardik Pandya", role: .allRounder, team: "MI", basePrice: 16, totalPoints: 198),
            Player(name: "Suryakumar Yadav", role: .batsman, team: "MI", basePrice: 14, totalPoints: 178),
            Player(name: "Tilak Varma", role: .batsman, team: "MI", basePrice: 8, totalPoints: 145),
            Player(name: "Ishan Kishan", role: .wicketKeeper, team: "MI", basePrice: 12, totalPoints: 156),
            Player(name: "Virat Kohli", role: .batsman, team: "RCB", basePrice: 18, totalPoints: 298),
            Player(name: "Ravichandran Ashwin", role: .allRounder, team: "RR", basePrice: 12, totalPoints: 167),
            Player(name: "Andre Russell", role: .allRounder, team: "KKR", basePrice: 12, totalPoints: 189),
            Player(name: "Rashid Khan", role: .bowler, team: "GT", basePrice: 14, totalPoints: 234),
            Player(name: "Shubman Gill", role: .batsman, team: "GT", basePrice: 16, totalPoints: 212),
            Player(name: "Mohammed Shami", role: .bowler, team: "GT", basePrice: 14, totalPoints: 198),
            Player(name: "KL Rahul", role: .wicketKeeper, team: "LSG", basePrice: 14, totalPoints: 167),
            Player(name: "Ruturaj Gaikwad", role: .batsman, team: "CSK", basePrice: 12, totalPoints: 178),
            Player(name: "MS Dhoni", role: .wicketKeeper, team: "CSK", basePrice: 12, totalPoints: 145),
        ]
        
        // Set default captain and vice-captain
        captain = squad.first(where: { $0.name == "Rohit Sharma" })
        viceCaptain = squad.first(where: { $0.name == "Jasprit Bumrah" })
    }
    
    func selectCaptain(_ player: Player) {
        // If already captain, deselect
        if captain?.id == player.id {
            captain = nil
        } else {
            // If vice-captain, swap
            if viceCaptain?.id == player.id {
                viceCaptain = captain
            }
            captain = player
        }
    }
    
    func selectViceCaptain(_ player: Player) {
        // If already vice-captain, deselect
        if viceCaptain?.id == player.id {
            viceCaptain = nil
        } else {
            // If captain, swap
            if captain?.id == player.id {
                captain = viceCaptain
            }
            viceCaptain = player
        }
    }
    
    func saveTeam() {
        // Save to backend
        isLoading = true
        // Simulate API call
        DispatchQueue.main.asyncAfter(deadline: .now() + 1) {
            self.isLoading = false
        }
    }
    
    func calculateTotalPoints() -> Int {
        var total = squad.reduce(0) { $0 + $1.totalPoints }
        
        // Apply captain multiplier
        if let cap = captain {
            total += cap.totalPoints // Extra 100% for captain
        }
        
        // Apply vice-captain multiplier
        if let vc = viceCaptain {
            total += Int(Double(vc.totalPoints) * 0.5) // Extra 50% for vice
        }
        
        return total
    }
}
