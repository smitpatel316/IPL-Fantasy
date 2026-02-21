import SwiftUI
import Combine

// MARK: - Auth ViewModel
@MainActor
class AuthViewModel: ObservableObject {
    @Published var isAuthenticated = false
    @Published var currentUser: User?
    @Published var isLoading = false
    @Published var errorMessage: String?
    
    private let authService = AuthService.shared
    
    init() {
        // Check for existing session
        isAuthenticated = authService.isAuthenticated
        currentUser = authService.currentUser
    }
    
    // MARK: - Email Login/Register
    
    func login(email: String, password: String) async throws {
        isLoading = true
        errorMessage = nil
        
        do {
            try await authService.login(email: email, password: password)
            isAuthenticated = true
            currentUser = authService.currentUser
        } catch {
            errorMessage = error.localizedDescription
            throw error
        }
        
        isLoading = false
    }
    
    func register(email: String, password: String, displayName: String) async throws {
        isLoading = true
        errorMessage = nil
        
        do {
            try await authService.register(email: email, password: password, displayName: displayName)
            isAuthenticated = true
            currentUser = authService.currentUser
        } catch {
            errorMessage = error.localizedDescription
            throw error
        }
        
        isLoading = false
    }
    
    // MARK: - Google Sign In
    
    func loginWithGoogle(idToken: String) async throws {
        isLoading = true
        errorMessage = nil
        
        do {
            try await authService.loginWithGoogle(idToken: idToken)
            isAuthenticated = true
            currentUser = authService.currentUser
        } catch {
            errorMessage = error.localizedDescription
            throw error
        }
        
        isLoading = false
    }
    
    // MARK: - Apple Sign In
    
    func loginWithApple(idToken: String, fullName: String?) async throws {
        isLoading = true
        errorMessage = nil
        
        do {
            try await authService.loginWithApple(idToken: idToken, fullName: fullName)
            isAuthenticated = true
            currentUser = authService.currentUser
        } catch {
            errorMessage = error.localizedDescription
            throw error
        }
        
        isLoading = false
    }
    
    // MARK: - Logout
    
    func logout() {
        authService.logout()
        isAuthenticated = false
        currentUser = nil
    }
}
