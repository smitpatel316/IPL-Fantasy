import SwiftUI

// MARK: - Register View
struct RegisterView: View {
    @EnvironmentObject var authViewModel: AuthViewModel
    @Environment(\.dismiss) var dismiss
    @State private var email = ""
    @State private var password = ""
    @State private var confirmPassword = ""
    @State private var displayName = ""
    @State private var isLoading = false
    @State private var errorMessage: String?

    var body: some View {
        ZStack {
            AppColors.background
                .ignoresSafeArea()

            ScrollView {
                VStack(spacing: AppSpacing.lg) {
                    // Header
                    VStack(spacing: AppSpacing.sm) {
                        Image(systemName: "cricket.bat.and.ball")
                            .font(.system(size: 60))
                            .foregroundColor(AppColors.primary)

                        Text("Create Account")
                            .font(AppFonts.title)
                            .fontWeight(.bold)
                            .foregroundColor(AppColors.textPrimary)

                        Text("Join the fantasy league")
                            .font(AppFonts.body)
                            .foregroundColor(AppColors.textSecondary)
                    }
                    .padding(.top, AppSpacing.xl)

                    // Form
                    VStack(spacing: AppSpacing.md) {
                        AppTextField(placeholder: "Display Name", text: $displayName)

                        AppTextField(placeholder: "Email", text: $email, keyboardType: .emailAddress)

                        AppTextField(placeholder: "Password", text: $password, isSecure: true)

                        AppTextField(placeholder: "Confirm Password", text: $confirmPassword, isSecure: true)
                    }
                    .padding(.horizontal, AppSpacing.lg)

                    // Error Message
                    if let error = errorMessage {
                        Text(error)
                            .font(AppFonts.caption)
                            .foregroundColor(AppColors.error)
                            .padding(.horizontal, AppSpacing.lg)
                    }

                    // Register Button
                    PrimaryButton(title: "Create Account", action: register, isLoading: isLoading)
                        .padding(.horizontal, AppSpacing.lg)
                        .padding(.top, AppSpacing.md)

                    // Login Link
                    loginLink
                        .padding(.top, AppSpacing.md)
                }
            }
        }
    }

    private var loginLink: some View {
        HStack(spacing: AppSpacing.xs) {
            Text("Already have an account?")
                .font(AppFonts.body)
                .foregroundColor(AppColors.textSecondary)

            Button(action: { dismiss() }) {
                Text("Log In")
                    .font(AppFonts.body)
                    .fontWeight(.semibold)
                    .foregroundColor(AppColors.primary)
            }
        }
    }

    private func register() {
        guard !displayName.isEmpty else {
            errorMessage = "Please enter your name"
            return
        }

        guard email.contains("@") else {
            errorMessage = "Please enter a valid email"
            return
        }

        guard password.count >= 6 else {
            errorMessage = "Password must be at least 6 characters"
            return
        }

        guard password == confirmPassword else {
            errorMessage = "Passwords do not match"
            return
        }

        isLoading = true
        errorMessage = nil

        Task {
            do {
                try await authViewModel.register(email: email, password: password, displayName: displayName)
            } catch {
                errorMessage = error.localizedDescription
            }
            isLoading = false
        }
    }
}
