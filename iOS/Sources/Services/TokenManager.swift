import Foundation
import Combine

// MARK: - Token Manager (handles auto-refresh)
class TokenManager {
    static let shared = TokenManager()
    
    private var refreshTask: Task<Void, Never>?
    private let keychain = KeychainHelper.shared
    
    private init() {}
    
    // Check if token needs refresh
    func shouldRefresh() -> Bool {
        guard let token = keychain.get("access_token") else {
            return false
        }
        
        // Decode JWT to check expiry
        let parts = token.split(separator: ".")
        guard parts.count == 3,
              let payload = Data(base64Encoded: String(parts[1]).base64Padded),
              let json = try? JSONSerialization.jsonObject(with: payload) as? [String: Any],
              let exp = json["exp"] as? TimeInterval else {
            return false
        }
        
        let expiryDate = Date(timeIntervalSince1970: exp)
        let buffer: TimeInterval = 60 // Refresh 1 minute before expiry
        
        return Date() > expiryDate - buffer
    }
    
    // Auto-refresh token if needed
    func refreshIfNeeded() async throws {
        // Don't refresh if already refreshing
        guard refreshTask == nil else {
            return try? await refreshTask?.value
        }
        
        // Check if we actually need to refresh
        guard shouldRefresh() else {
            return
        }
        
        refreshTask = Task {
            do {
                try await AuthService.shared.refreshToken()
            } catch {
                // If refresh fails, user needs to log in again
                AuthService.shared.logout()
            }
            refreshTask = nil
        }
        
        try? await refreshTask?.value
    }
}

// MARK: - String Base64 Extension
extension String {
    var base64Padded: String {
        let remainder = count % 4
        if remainder > 0 {
            return self + String(repeating: "=", count: 4 - remainder)
        }
        return self
    }
}

// MARK: - Interceptor for API calls
extension APIService {
    
    func authenticatedRequest<T: Decodable>(
        _ endpoint: String,
        method: HTTPMethod = .get,
        body: Encodable? = nil
    ) async throws -> T {
        // First, try to refresh if needed
        try await TokenManager.shared.refreshIfNeeded()
        
        // Make the request
        return try await self.request(endpoint, method: method, body: body, requiresAuth: true)
    }
}

// MARK: - Updated APIService with auto-refresh
extension APIService {
    
    // Generic request with automatic token refresh
    func requestWithAuth<T: Decodable>(
        _ endpoint: String,
        method: HTTPMethod = .get,
        body: Encodable? = nil
    ) async throws -> T {
        var lastError: Error?
        
        // Try up to 2 times (original + 1 retry after refresh)
        for attempt in 1...2 {
            do {
                // Check/refresh token before each attempt
                try await TokenManager.shared.refreshIfNeeded()
                
                return try await request(endpoint, method: method, body: body, requiresAuth: true)
                
            } catch APIError.unauthorized {
                // If unauthorized, force refresh and retry
                if attempt == 1 {
                    try await AuthService.shared.refreshToken()
                    lastError = nil
                } else {
                    // Second attempt failed, clear session
                    await MainActor.run {
                        AuthService.shared.logout()
                    }
                    throw AuthError.sessionExpired
                }
            }
        }
        
        throw lastError ?? APIError.unknown(0)
    }
}

// MARK: - Updated AuthService with longer refresh
extension AuthService {
    
    // Save tokens with longer expiry
    private func saveTokens(access: String, refresh: String) throws {
        // Access token - stored in memory only (short-lived)
        // Refresh token - stored in Keychain (long-lived)
        keychain.set(refresh, forKey: "refresh_token")
        
        // Save access token for immediate use
        keychain.set(access, forKey: "access_token")
        api.setAuthToken(access)
    }
}
