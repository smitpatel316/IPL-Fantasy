import Foundation
import Combine

// MARK: - Auth View Model
@MainActor
class AuthViewModel: ObservableObject {
    @Published var currentUser: User?
    @Published var isAuthenticated = false
    @Published var isLoading = false
    @Published var errorMessage: String?
    @Published var email = ""
    @Published var password = ""
    @Published var displayName = ""
    
    private let authService = AuthService.shared
    
    init() {
        checkAuthStatus()
    }
    
    func checkAuthStatus() {
        if let user = authService.getCurrentUser() {
            currentUser = user
            isAuthenticated = true
        }
    }
    
    func login() async {
        guard !email.isEmpty, !password.isEmpty else {
            errorMessage = "Please enter email and password"
            return
        }
        
        isLoading = true
        errorMessage = nil
        
        do {
            let user = try await authService.login(email: email, password: password)
            currentUser = user
            isAuthenticated = true
            clearForm()
        } catch {
            errorMessage = error.localizedDescription
        }
        
        isLoading = false
    }
    
    func register() async {
        guard !email.isEmpty, !password.isEmpty, !displayName.isEmpty else {
            errorMessage = "Please fill all fields"
            return
        }
        
        isLoading = true
        errorMessage = nil
        
        do {
            let user = try await authService.register(email: email, password: password, displayName: displayName)
            currentUser = user
            isAuthenticated = true
            clearForm()
        } catch {
            errorMessage = error.localizedDescription
        }
        
        isLoading = false
    }
    
    func logout() {
        authService.logout()
        currentUser = nil
        isAuthenticated = false
        clearForm()
    }
    
    private func clearForm() {
        email = ""
        password = ""
        displayName = ""
    }
}
