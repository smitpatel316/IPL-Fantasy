import Foundation
import Combine

// MARK: - Auth Service (Simple)
@MainActor
class AuthService: ObservableObject {
    static let shared = AuthService()
    
    @Published private(set) var isAuthenticated = false
    @Published private(set) var currentUser: User?
    
    private let api = APIService.shared
    private let keychain = KeychainHelper.shared
    
    private init() {
        loadStoredSession()
    }
    
    // MARK: - Load Session
    
    private func loadStoredSession() {
        guard let token = keychain.get("auth_token"),
              let userData = UserDefaults.standard.data(forKey: "current_user"),
              let user = try? JSONDecoder().decode(User.self, from: userData) else {
            return
        }
        
        api.setAuthToken(token)
        currentUser = user
        isAuthenticated = true
    }
    
    // MARK: - Register
    
    func register(email: String, password: String, displayName: String) async throws {
        let request = RegisterRequest(email: email, password: password, displayName: displayName)
        
        let response: AuthResponse = try await api.post("/auth/register", body: request)
        
        handleAuthResponse(response)
    }
    
    // MARK: - Login
    
    func login(email: String, password: String) async throws {
        let request = LoginRequest(email: email, password: password)
        
        let response: AuthResponse = try await api.post("/auth/login", body: request)
        
        handleAuthResponse(response)
    }
    
    // MARK: - Logout
    
    func logout() {
        keychain.delete("auth_token")
        UserDefaults.standard.removeObject(forKey: "current_user")
        
        api.setAuthToken(nil)
        currentUser = nil
        isAuthenticated = false
    }
    
    // MARK: - Private
    
    private func handleAuthResponse(_ response: AuthResponse) {
        // Save token
        keychain.set(response.token, forKey: "auth_token")
        
        // Save user
        currentUser = response.user
        isAuthenticated = true
        
        if let data = try? JSONEncoder().encode(response.user) {
            UserDefaults.standard.set(data, forKey: "current_user")
        }
        
        api.setAuthToken(response.token)
    }
}

// MARK: - Keychain Helper
class KeychainHelper {
    static let shared = KeychainHelper()
    
    private let service = "com.iplfantasy.pro"
    
    func set(_ value: String, forKey key: String) {
        guard let data = value.data(using: .utf8) else { return }
        
        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: service,
            kSecAttrAccount as String: key
        ]
        
        SecItemDelete(query as CFDictionary)
        
        let addQuery: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: service,
            kSecAttrAccount as String: key,
            kSecValueData as String: data
        ]
        
        SecItemAdd(addQuery as CFDictionary, nil)
    }
    
    func get(_ key: String) -> String? {
        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: service,
            kSecAttrAccount as String: key,
            kSecReturnData as String: true,
            kSecMatchLimit as String: kSecMatchLimitOne
        ]
        
        var result: AnyObject?
        let status = SecItemCopyMatching(query as CFDictionary, &result)
        
        guard status == errSecSuccess,
              let data = result as? Data,
              let string = String(data: data, encoding: .utf8) else {
            return nil
        }
        
        return string
    }
    
    func delete(_ key: String) {
        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: service,
            kSecAttrAccount as String: key
        ]
        
        SecItemDelete(query as CFDictionary)
    }
}

// MARK: - Models
struct RegisterRequest: Encodable {
    let email: String
    let password: String
    let displayName: String
}

struct LoginRequest: Encodable {
    let email: String
    let password: String
}

struct OAuthRequest: Encodable {
    let idToken: String
    
    enum CodingKeys: String, CodingKey {
        case idToken = "id_token"
    }
}

struct AppleRequest: Encodable {
    let idToken: String
    let fullName: String?
    
    enum CodingKeys: String, CodingKey {
        case idToken = "id_token"
        case fullName
    }
}

struct AuthResponse: Decodable {
    let token: String
    let user: User
}

struct User: Codable {
    let id: String
    let email: String
    let displayName: String
    let avatarUrl: String?
}
