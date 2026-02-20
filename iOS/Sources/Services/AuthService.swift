import Foundation

// MARK: - Auth Service
class AuthService {
    static let shared = AuthService()
    private let userDefaults = UserDefaults.standard
    private let currentUserKey = "currentUser"
    
    private init() {}
    
    func getCurrentUser() -> User? {
        guard let data = userDefaults.data(forKey: currentUserKey),
              let user = try? JSONDecoder().decode(User.self, from: data) else {
            return nil
        }
        return user
    }
    
    func login(email: String, password: String) async throws -> User {
        // Simulate network delay
        try await Task.sleep(nanoseconds: 1_000_000_000)
        
        // Mock validation
        guard email.contains("@") else {
            throw AuthError.invalidEmail
        }
        
        guard password.count >= 6 else {
            throw AuthError.invalidPassword
        }
        
        // Create mock user
        let user = User(
            id: UUID().uuidString,
            email: email,
            displayName: email.components(separatedBy: "@").first ?? "User"
        )
        
        saveUser(user)
        return user
    }
    
    func register(email: String, password: String, displayName: String) async throws -> User {
        // Simulate network delay
        try await Task.sleep(nanoseconds: 1_000_000_000)
        
        // Mock validation
        guard email.contains("@") else {
            throw AuthError.invalidEmail
        }
        
        guard password.count >= 6 else {
            throw AuthError.invalidPassword
        }
        
        guard !displayName.isEmpty else {
            throw AuthError.invalidDisplayName
        }
        
        // Create new user
        let user = User(
            id: UUID().uuidString,
            email: email,
            displayName: displayName
        )
        
        saveUser(user)
        return user
    }
    
    func logout() {
        userDefaults.removeObject(forKey: currentUserKey)
    }
    
    private func saveUser(_ user: User) {
        if let data = try? JSONEncoder().encode(user) {
            userDefaults.set(data, forKey: currentUserKey)
        }
    }
}

// MARK: - Auth Errors
enum AuthError: LocalizedError {
    case invalidEmail
    case invalidPassword
    case invalidDisplayName
    case userNotFound
    case networkError
    
    var errorDescription: String? {
        switch self {
        case .invalidEmail:
            return "Please enter a valid email address"
        case .invalidPassword:
            return "Password must be at least 6 characters"
        case .invalidDisplayName:
            return "Please enter your name"
        case .userNotFound:
            return "User not found"
        case .networkError:
            return "Network error. Please try again."
        }
    }
}
