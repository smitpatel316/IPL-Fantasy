import Foundation
import Combine

// MARK: - Auth Service
@MainActor
class AuthService: ObservableObject {
    static let shared = AuthService()
    
    @Published private(set) var isAuthenticated = false
    @Published private(set) var currentUser: User?
    
    private let api = APIService.shared
    private var cancellables = Set<AnyCancellable>()
    private let keychain = KeychainHelper.shared
    
    private init() {
        loadStoredSession()
    }
    
    // MARK: - Session Management
    
    private func loadStoredSession() {
        guard let token = keychain.get("access_token"),
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
        
        try handleAuthResponse(response)
    }
    
    // MARK: - Login
    
    func login(email: String, password: String) async throws {
        let request = LoginRequest(email: email, password: password)
        
        let response: AuthResponse = try await api.post("/auth/login", body: request)
        
        try handleAuthResponse(response)
    }
    
    // MARK: - Logout
    
    func logout() async {
        do {
            try await api.post("/auth/logout", body: EmptyRequest())
        } catch {
            // Continue even if logout fails
        }
        
        clearSession()
    }
    
    // MARK: - Refresh Token
    
    func refreshToken() async throws {
        guard let refreshToken = keychain.get("refresh_token") else {
            throw AuthError.noRefreshToken
        }
        
        let request = RefreshRequest(refreshToken: refreshToken)
        
        let response: RefreshResponse = try await api.post("/auth/refresh", body: request)
        
        try saveTokens(access: response.accessToken, refresh: response.refreshToken)
    }
    
    // MARK: - Change Password
    
    func changePassword(current: String, new: String) async throws {
        let request = ChangePasswordRequest(currentPassword: current, newPassword: new)
        
        _ = try await api.post("/auth/change-password", body: request, requiresAuth: true)
        
        // After password change, clear session
        clearSession()
    }
    
    // MARK: - Private Helpers
    
    private func handleAuthResponse(_ response: AuthResponse) throws {
        try saveTokens(access: response.accessToken, refresh: response.refreshToken)
        
        currentUser = response.user
        isAuthenticated = true
        
        // Store user data
        if let data = try? JSONEncoder().encode(response.user) {
            UserDefaults.standard.set(data, forKey: "current_user")
        }
    }
    
    private func saveTokens(access: String, refresh: String) throws {
        keychain.set(access, forKey: "access_token")
        keychain.set(refresh, forKey: "refresh_token")
        api.setAuthToken(access)
    }
    
    private func clearSession() {
        keychain.delete("access_token")
        keychain.delete("refresh_token")
        UserDefaults.standard.removeObject(forKey: "current_user")
        
        api.setAuthToken(nil)
        currentUser = nil
        isAuthenticated = false
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

// MARK: - Auth Errors
enum AuthError: LocalizedError {
    case noRefreshToken
    case sessionExpired
    case invalidCredentials
    
    var errorDescription: String? {
        switch self {
        case .noRefreshToken: return "Session expired. Please log in again."
        case .sessionExpired: return "Your session has expired. Please log in again."
        case .invalidCredentials: return "Invalid email or password."
        }
    }
}

// MARK: - Request Models
struct RegisterRequest: Encodable {
    let email: String
    let password: String
    let displayName: String
}

struct LoginRequest: Encodable {
    let email: String
    let password: String
}

struct RefreshRequest: Encodable {
    let refreshToken: String
}

struct ChangePasswordRequest: Encodable {
    let currentPassword: String
    let newPassword: String
}

struct EmptyRequest: Encodable {}

// MARK: - Response Models
struct AuthResponse: Decodable {
    let accessToken: String
    let refreshToken: String
    let user: User
    
    enum CodingKeys: String, CodingKey {
        case accessToken = "access_token"
        case refreshToken = "refresh_token"
        case user
    }
}

struct RefreshResponse: Decodable {
    let accessToken: String
    let refreshToken: String
    
    enum CodingKeys: String, CodingKey {
        case accessToken = "access_token"
        case refreshToken = "refresh_token"
    }
}

struct User: Codable {
    let id: String
    let email: String
    let displayName: String
    let avatarUrl: String?
    let createdAt: Date?
}
