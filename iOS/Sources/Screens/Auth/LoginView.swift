import SwiftUI

// MARK: - Login View
struct LoginView: View {
    @EnvironmentObject var authViewModel: AuthViewModel
    @State private var isShowingRegister = false
    
    var body: some View {
        NavigationStack {
            ZStack {
                AppColors.background
                    .ignoresSafeArea()
                
                ScrollView {
                    VStack(spacing: AppSpacing.xl) {
                        // Logo/Header
                        VStack(spacing: AppSpacing.md) {
                            Image(systemName: "cricket.bat.and.ball")
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
                        .padding(.bottom, AppSpacing.lg)
                        
                        // Login Form
                        VStack(spacing: AppSpacing.md) {
                            AppTextField(
                                placeholder: "Email",
                                text: $authViewModel.email,
                                keyboardType: .emailAddress
                            )
                            
                            AppTextField(
                                placeholder: "Password",
                                text: $authViewModel.password,
                                isSecure: true
                            )
                            
                            if let error = authViewModel.errorMessage {
                                Text(error)
                                    .font(AppFonts.caption)
                                    .foregroundColor(AppColors.error)
                                    .frame(maxWidth: .infinity, alignment: .leading)
                            }
                        }
                        .padding(.horizontal, AppSpacing.md)
                        
                        // Login Button
                        PrimaryButton(
                            title: "Login",
                            action: {
                                Task {
                                    await authViewModel.login()
                                }
                            },
                            isLoading: authViewModel.isLoading
                        )
                        .padding(.horizontal, AppSpacing.md)
                        
                        // Divider
                        HStack {
                            Rectangle()
                                .fill(AppColors.textMuted)
                                .frame(height: 1)
                            
                            Text("OR")
                                .font(AppFonts.caption)
                                .foregroundColor(AppColors.textMuted)
                            
                            Rectangle()
                                .fill(AppColors.textMuted)
                                .frame(height: 1)
                        }
                        .padding(.horizontal, AppSpacing.md)
                        
                        // Register Button
                        SecondaryButton(title: "Create Account") {
                            isShowingRegister = true
                        }
                        .padding(.horizontal, AppSpacing.md)
                        
                        Spacer()
                    }
                }
            }
            .navigationDestination(isPresented: $isShowingRegister) {
                RegisterView()
            }
        }
    }
}

// MARK: - Register View
struct RegisterView: View {
    @EnvironmentObject var authViewModel: AuthViewModel
    @Environment(\.dismiss) var dismiss
    
    var body: some View {
        ZStack {
            AppColors.background
                .ignoresSafeArea()
            
            ScrollView {
                VStack(spacing: AppSpacing.xl) {
                    // Header
                    VStack(spacing: AppSpacing.sm) {
                        Text("Create Account")
                            .font(AppFonts.title)
                            .fontWeight(.bold)
                            .foregroundColor(AppColors.textPrimary)
                        
                        Text("Join the fantasy league")
                            .font(AppFonts.body)
                            .foregroundColor(AppColors.textSecondary)
                    }
                    .padding(.top, AppSpacing.xxl)
                    
                    // Register Form
                    VStack(spacing: AppSpacing.md) {
                        AppTextField(
                            placeholder: "Full Name",
                            text: $authViewModel.displayName
                        )
                        
                        AppTextField(
                            placeholder: "Email",
                            text: $authViewModel.email,
                            keyboardType: .emailAddress
                        )
                        
                        AppTextField(
                            placeholder: "Password",
                            text: $authViewModel.password,
                            isSecure: true
                        )
                        
                        if let error = authViewModel.errorMessage {
                            Text(error)
                                .font(AppFonts.caption)
                                .foregroundColor(AppColors.error)
                                .frame(maxWidth: .infinity, alignment: .leading)
                        }
                    }
                    .padding(.horizontal, AppSpacing.md)
                    
                    // Register Button
                    PrimaryButton(
                        title: "Sign Up",
                        action: {
                            Task {
                                await authViewModel.register()
                                if authViewModel.isAuthenticated {
                                    dismiss()
                                }
                            }
                        },
                        isLoading: authViewModel.isLoading
                    )
                    .padding(.horizontal, AppSpacing.md)
                    
                    // Login Link
                    Button("Already have an account? Login") {
                        dismiss()
                    }
                    .font(AppFonts.caption)
                    .foregroundColor(AppColors.primary)
                    
                    Spacer()
                }
            }
        }
    }
}
