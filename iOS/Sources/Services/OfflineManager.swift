import Foundation
import Combine

// MARK: - Cache Manager
class CacheManager {
    static let shared = CacheManager()
    
    private let cache = NSCache<NSString, CachedResponse>()
    private let userDefaults = UserDefaults.standard
    
    private init() {
        cache.countLimit = 100
    }
    
    // MARK: - Cache Keys
    enum CacheKey: String {
        case leagues = "cached_leagues"
        case players = "cached_players"
        case standings = "cached_standings"
        case team = "cached_team"
        case lastSync = "last_sync_timestamp"
    }
    
    // MARK: - Save to Cache
    func save<T: Encodable>(_ object: T, forKey key: CacheKey) {
        do {
            let data = try JSONEncoder().encode(object)
            userDefaults.set(data, forKey: key.rawValue)
            userDefaults.set(Date(), forKey: CacheKey.lastSync.rawValue)
        } catch {
            print("Cache save error: \(error)")
        }
    }
    
    // MARK: - Load from Cache
    func load<T: Decodable>(_ type: T.Type, forKey key: CacheKey) -> T? {
        guard let data = userDefaults.data(forKey: key.rawValue) else { return nil }
        
        do {
            return try JSONDecoder().decode(type, forKey: key)
        } catch {
            print("Cache load error: \(error)")
            return nil
        }
    }
    
    // MARK: - Check if Cache is Valid
    func isCacheValid(maxAge: TimeInterval = 300) -> Bool { // 5 minutes default
        guard let lastSync = userDefaults.object(forKey: CacheKey.lastSync.rawValue) as? Date else {
            return false
        }
        
        return Date().timeIntervalSince(lastSync) < maxAge
    }
    
    // MARK: - Clear Cache
    func clearCache() {
        userDefaults.removeObject(forKey: CacheKey.leagues.rawValue)
        userDefaults.removeObject(forKey: CacheKey.players.rawValue)
        userDefaults.removeObject(forKey: CacheKey.standings.rawValue)
        userDefaults.removeObject(forKey: CacheKey.team.rawValue)
        userDefaults.removeObject(forKey: CacheKey.lastSync.rawValue)
        cache.removeAllObjects()
    }
}

// MARK: - Cached Response
struct CachedResponse {
    let data: Data
    let timestamp: Date
    
    var isValid: Bool {
        Date().timeIntervalSince(timestamp) < 300 // 5 minutes
    }
}

// MARK: - Offline Manager
class OfflineManager: ObservableObject {
    static let shared = OfflineManager()
    
    @Published var isOffline: Bool = false
    @Published var pendingActions: [PendingAction] = []
    
    private var networkMonitor: NWPathMonitor?
    private let monitorQueue = DispatchQueue(label: "NetworkMonitor")
    
    private init() {
        startMonitoring()
    }
    
    // MARK: - Network Monitoring
    private func startMonitoring() {
        networkMonitor = NWPathMonitor()
        networkMonitor?.pathUpdateHandler = { [weak self] path in
            DispatchQueue.main.async {
                self?.isOffline = path.status != .satisfied
                
                if path.status == .satisfied {
                    self?.syncPendingActions()
                }
            }
        }
        networkMonitor?.start(queue: monitorQueue)
    }
    
    // MARK: - Pending Actions
    func addPendingAction(_ action: PendingAction) {
        pendingActions.append(action)
        savePendingActions()
    }
    
    func syncPendingActions() {
        guard !pendingActions.isEmpty else { return }
        
        // Sync each pending action
        for action in pendingActions {
            executeAction(action)
        }
        
        // Clear pending actions
        pendingActions.removeAll()
        savePendingActions()
    }
    
    private func executeAction(_ action: PendingAction) {
        // Execute based on action type
        switch action.type {
        case .setLineup:
            // API call to set lineup
            break
        case .placeBid:
            // API call to place bid
            break
        case .makeTrade:
            // API call to make trade
            break
        }
    }
    
    private func savePendingActions() {
        CacheManager.shared.save(pendingActions, forKey: .leagues) // Reusing key for simplicity
    }
}

// MARK: - Pending Action
struct PendingAction: Codable {
    let id: String
    let type: ActionType
    let payload: Data
    let createdAt: Date
    
    enum ActionType: String, Codable {
        case setLineup
        case placeBid
        case makeTrade
    }
}

// MARK: - Network Monitor Import
import Network
