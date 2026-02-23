import Foundation
import Combine

// MARK: - Auto-Pick Settings View Model
@MainActor
class AutoPickSettingsViewModel: ObservableObject {
    @Published var settings: AutoPickSettings
    @Published var availablePlayers: [Player] = []
    @Published var isLoading = false
    @Published var hasChanges = false
    @Published var showError = false
    @Published var errorMessage = ""
    
    private let autoPickService = AutoPickService.shared
    private var originalSettings: AutoPickSettings?
    
    init() {
        settings = AutoPickSettings(leagueId: "")
    }
    
    func loadSettings(leagueId: String) async {
        isLoading = true
        settings.leagueId = leagueId
        
        do {
            // Load settings
            let loadedSettings = try await autoPickService.getSettings(leagueId: leagueId)
            settings = loadedSettings
            originalSettings = loadedSettings
            
            // Load available players
            // In production, would fetch from PlayerService
            loadMockPlayers()
            
            hasChanges = false
        } catch {
            errorMessage = error.localizedDescription
            showError = true
            loadMockPlayers()
        }
        
        isLoading = false
    }
    
    func saveSettings() async {
        isLoading = true
        
        do {
            _ = try await autoPickService.saveSettings(settings)
            originalSettings = settings
            hasChanges = false
        } catch {
            errorMessage = error.localizedDescription
            showError = true
        }
        
        isLoading = false
    }
    
    func toggleFavoritePlayer(_ playerId: String) {
        if settings.favoritePlayers.contains(playerId) {
            settings.favoritePlayers.removeAll { $0 == playerId }
        } else {
            settings.favoritePlayers.append(playerId)
        }
        checkForChanges()
    }
    
    func togglePreferredRole(_ role: Player.PlayerRole) {
        if settings.preferredRoles.contains(role) {
            settings.preferredRoles.removeAll { $0 == role }
        } else {
            settings.preferredRoles.append(role)
        }
        checkForChanges()
    }
    
    private func checkForChanges() {
        guard let original = originalSettings else {
            hasChanges = true
            return
        }
        
        hasChanges = 
            settings.isEnabled != original.isEnabled ||
            settings.favoritePlayers != original.favoritePlayers ||
            settings.preferredRoles != original.preferredRoles ||
            settings.maxPrice != original.maxPrice ||
            settings.autoBidEnabled != original.autoBidEnabled ||
            settings.autoBidIncrement != original.autoBidIncrement
    }
    
    private func loadMockPlayers() {
        availablePlayers = [
            Player(id: "p1", name: "Virat Kohli", role: .batsman, team: "RCB", basePrice: 18.0),
            Player(id: "p2", name: "Rohit Sharma", role: .batsman, team: "MI", basePrice: 18.0),
            Player(id: "p3", name: "Jasprit Bumrah", role: .bowler, team: "MI", basePrice: 18.0),
            Player(id: "p4", name: "Shubman Gill", role: .batsman, team: "GT", basePrice: 16.0),
            Player(id: "p5", name: "KL Rahul", role: .wicketKeeper, team: "LSG", basePrice: 14.0),
            Player(id: "p6", name: "Ravindra Jadeja", role: .allRounder, team: "CSK", basePrice: 14.0),
            Player(id: "p7", name: "MS Dhoni", role: .wicketKeeper, team: "CSK", basePrice: 12.0),
            Player(id: "p8", name: "Hardik Pandya", role: .allRounder, team: "GT", basePrice: 16.0),
            Player(id: "p9", name: "Mohammed Siraj", role: .bowler, team: "RCB", basePrice: 10.0),
            Player(id: "p10", name: "Suryakumar Yadav", role: .batsman, team: "MI", basePrice: 14.0),
        ]
    }
}
