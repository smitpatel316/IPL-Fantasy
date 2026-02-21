import SwiftUI
import AuthenticationServices

// MARK: - Login View
struct LoginView: View {
    @EnvironmentObject var authViewModel: AuthViewModel
    @State private var email = ""
    @State private var password = ""
    @State private var isLoading = false
    @State private var errorMessage: String?
    
    var body: some View {
        NavigationStack {
            ZStack {
                AppColors.background
                    .ignoresSafeArea()
                
                ScrollView {
                    VStack(spacing: AppSpacing.xl) {
                        // Logo
                        logoSection
                        
                        // Email Login
                        emailSection
                        
                        // Divider
                        dividerSection
                        
                        // Social Login
                        socialSection
                        
                        // Sign Up Link
                        signUpLink
                    }
                    .padding(AppSpacing.lg)
                }
            }
            .navigationTitle("Login")
            .navigationBarTitleDisplayMode(.large)
            .navigationBarBackButtonHidden(true)
        }
    }
    
    private var logoSection: some View {
        VStack(spacing: AppSpacing.md) {
            Image(systemName: "cricket.bat.ball")
                .font(.system(size: 60))
                .foregroundColor(AppColors.primary)
            
            Text("IPL Fantasy Pro")
                .font(AppFonts.title)
                .fontWeight(.bold)
                .foregroundColor(AppColors.textPrimary)
            
            Text("Create your dream team")
                .font(AppFonts.body)
                .foregroundColor(AppColors.textSecondary)
        }
        .padding(.top, AppSpacing.xxl)
    }
    
    private var emailSection: some View {
        VStack(spacing: AppSpacing.md) {
            // Email
            TextField("Email", text: $email)
                .textFieldStyle(CustomTextFieldStyle())
                .textContentType(.emailAddress)
                .keyboardType(.emailAddress)
                .autocapitalization(.none)
                .disableAutocorrection(true)
            
            // Password
            SecureField("Password", text: $password)
                .textFieldStyle(CustomTextFieldStyle())
                .textContentType(.password)
            
            // Error message
            if let error = errorMessage {
                Text(error)
                    .font(AppFonts.caption)
                    .foregroundColor(AppColors.error)
            }
            
            // Login Button
            Button(action: login) {
                HStack {
                    if isLoading {
                        ProgressView()
                            .progressViewStyle(CircularProgressViewStyle(tint: .white))
                    } else {
                        Text("Login")
                    }
                }
                .font(AppFonts.subheadline)
                .fontWeight(.semibold)
                .foregroundColor(.white)
                .frame(maxWidth: .infinity)
                .padding(.vertical, AppSpacing.md)
                .background(email.isEmpty || password.isEmpty ? AppColors.textMuted : AppColors.primary)
                .cornerRadius(AppCornerRadius.medium)
            }
            .disabled(email.isEmpty || password.isEmpty || isLoading)
        }
    }
    
    private var dividerSection: some View {
        HStack {
            Rectangle()
                .fill(AppColors.textMuted.opacity(0.3))
                .frame(height: 1)
            
            Text("or")
                .font(AppFonts.caption)
                .foregroundColor(AppColors.textMuted)
            
            Rectangle()
                .fill(AppColors.textMuted.opacity(0.3))
                .frame(height: 1)
        }
    }
    
    private var socialSection: some View {
        VStack(spacing: AppSpacing.md) {
            // Google Sign In
            Button(action: signInWithGoogle) {
                HStack(spacing: AppSpacing.sm) {
                    Image(systemName: "g.circle.fill")
                        .font(.system(size: 20))
                    Text("Continue with Google")
                }
                .font(AppFonts.subheadline)
                .fontWeight(.medium)
                .foregroundColor(AppColors.textPrimary)
                .frame(maxWidth: .infinity)
                .padding(.vertical, AppSpacing.md)
                .background(AppColors.surface)
                .cornerRadius(AppCornerRadius.medium)
                .overlay(
                    RoundedRectangle(cornerRadius: AppCornerRadius.medium)
                        .stroke(AppColors.textMuted.opacity(0.3), lineWidth: 1)
                )
            }
            
            // Apple Sign In
            SignInWithAppleButton(.signIn) { result in
                handleAppleSignIn(result)
            }
            .signInWithAppleButtonStyle(.black)
            .frame(height: 50)
            .cornerRadius(AppCornerRadius.medium)
        }
    }
    
    private var signUpLink: some View {
        HStack(spacing: AppSpacing.xs) {
            Text("Don't have an account?")
                .font(AppFonts.body)
                .foregroundColor(AppColors.textSecondary)
            
            NavigationLink(destination: RegisterView().environmentObject(authViewModel)) {
                Text("Sign Up")
                    .font(AppFonts.body)
                    .fontWeight(.semibold)
                    .foregroundColor(AppColors.primary)
            }
        }
    }
    
    // MARK: - Actions
    
    private func login() {
        isLoading = true
        errorMessage = nil
        
        Task {
            do {
                try await authViewModel.login(email: email, password: password)
            } catch {
                errorMessage = error.localizedDescription
            }
            isLoading = false
        }
    }
    
    private func signInWithGoogle() {
        // In production, use GoogleSignIn SDK
        // For now, simulate with mock token
        Task {
            isLoading = true
            // Would call: GIDSignIn.sharedInstance().signIn()
            // For demo, use mock token
            try await authViewModel.loginWithGoogle(idToken: "mock_google_token")
            isLoading = false
        }
    }
    
    private func handleAppleSignIn(_ result: Result<ASAuthorization, Error>) {
        switch result {
        case .success(let authorization):
            if let credential = authorization.credential as? ASAuthorizationAppleIDCredential {
                let idToken = String(data: credential.identityToken ?? Data(), encoding: .utf8) ?? ""
                let fullName = [credential.fullName?.givenName, credential.fullName?.familyName]
                    .compactMap { $0 }
                    .joined(separator: " ")
                
                Task {
                    isLoading = true
                    try await authViewModel.loginWithApple(idToken: idToken, fullName: fullName.isEmpty ? nil : fullName)
                    isLoading = false
                }
            }
        case .failure(let error):
            errorMessage = error.localizedDescription
        }
    }
}

// MARK: - Custom Text Field Style
struct CustomTextFieldStyle: TextFieldStyle {
    func _body(configuration: TextField<Self._Label>) -> some View {
        configuration
            .padding(AppSpacing.md)
            .background(AppColors.surface)
            .foregroundColor(AppColors.textPrimary)
            .cornerRadius(AppCornerRadius.small)
            .overlay(
                RoundedRectangle(cornerRadius: AppCornerRadius.small)
                    .stroke(AppColors.textMuted.opacity(0.3), lineWidth: 1)
            )
    }
}
