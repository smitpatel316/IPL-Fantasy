import Foundation
import Combine

// MARK: - Auto-Pick Service
class AutoPickService {
    static let shared = AutoPickService()
    
    private let api = APIService.shared
    @Published private(set) var settingsCache: [String: AutoPickSettings] = [:]
    
    private init() {}
    
    // MARK: - Get Settings for League
    
    func getSettings(leagueId: String) async throws -> AutoPickSettings {
        let settings: AutoPickSettings = try await api.get("/auto-pick/league/\(leagueId)")
        
        // Cache the settings
        await MainActor.run {
            settingsCache[leagueId] = settings
        }
        
        return settings
    }
    
    // MARK: - Save Settings
    
    func saveSettings(_ settings: AutoPickSettings) async throws -> AutoPickSettings {
        let body = AutoPickSettingsRequest(
            isEnabled: settings.isEnabled,
            favoritePlayers: settings.favoritePlayers,
            preferredRoles: settings.preferredRoles.map { $0.rawValue },
            maxPrice: settings.maxPrice,
            autoBidEnabled: settings.autoBidEnabled,
            autoBidIncrement: settings.autoBidIncrement
        )
        
        let saved: AutoPickSettings = try await api.post(
            "/auto-pick/league/\(settings.leagueId)",
            body: body
        )
        
        // Update cache
        await MainActor.run {
            settingsCache[settings.leagueId] = saved
        }
        
        return saved
    }
    
    // MARK: - Get All Settings
    
    func getAllSettings() async throws -> [AutoPickSettings] {
        let settings: [AutoPickSettings] = try await api.get("/auto-pick")
        return settings
    }
    
    // MARK: - Trigger Auto-Pick
    
    func triggerAutoPick(leagueId: String, draftId: String, playerId: String) async throws -> AutoPickTriggerResponse {
        let body = TriggerAutoPickRequest(draftId: draftId, playerId: playerId)
        
        let response: AutoPickTriggerResponse = try await api.post(
            "/auto-pick/league/\(leagueId)/trigger",
            body: body
        )
        
        return response
    }
    
    // MARK: - Clear Cache
    
    func clearCache() {
        settingsCache.removeAll()
    }
    
    // MARK: - Check if Auto-Pick is Enabled for League
    
    func isAutoPickEnabled(leagueId: String) -> Bool {
        return settingsCache[leagueId]?.isEnabled ?? false
    }
}

// MARK: - Request Models

private struct AutoPickSettingsRequest: Encodable {
    let isEnabled: Bool
    let favoritePlayers: [String]
    let preferredRoles: [String]
    let maxPrice: Double
    let autoBidEnabled: Bool
    let autoBidIncrement: Double
    
    enum CodingKeys: String, CodingKey {
        case isEnabled = "isEnabled"
        case favoritePlayers = "favoritePlayers"
        case preferredRoles = "preferredRoles"
        case maxPrice = "maxPrice"
        case autoBidEnabled = "autoBidEnabled"
        case autoBidIncrement = "autoBidIncrement"
    }
}

private struct TriggerAutoPickRequest: Encodable {
    let draftId: String
    let playerId: String
}
