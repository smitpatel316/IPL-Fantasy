import SwiftUI

// MARK: - Settings View
struct SettingsView: View {
    @EnvironmentObject var authViewModel: AuthViewModel
    @AppStorage("notificationsEnabled") private var notificationsEnabled = true
    @AppStorage("autoBidEnabled") private var autoBidEnabled = false
    @State private var showingLogoutAlert = false
    
    var body: some View {
        NavigationStack {
            ZStack {
                AppColors.background
                    .ignoresSafeArea()
                
                List {
                    // Profile Section
                    Section {
                        HStack(spacing: AppSpacing.md) {
                            ZStack {
                                Circle()
                                    .fill(AppColors.primary.opacity(0.2))
                                    .frame(width: 60, height: 60)
                                
                                Text("JD")
                                    .font(AppFonts.headline)
                                    .fontWeight(.bold)
                                    .foregroundColor(AppColors.primary)
                            }
                            
                            VStack(alignment: .leading, spacing: AppSpacing.xs) {
                                Text("John Doe")
                                    .font(AppFonts.subheadline)
                                    .fontWeight(.bold)
                                    .foregroundColor(AppColors.textPrimary)
                                
                                Text("john@example.com")
                                    .font(AppFonts.caption)
                                    .foregroundColor(AppColors.textSecondary)
                            }
                            
                            Spacer()
                            
                            Button(action: {}) {
                                Text("Edit")
                                    .font(AppFonts.caption)
                                    .foregroundColor(AppColors.primary)
                            }
                        }
                        .padding(.vertical, AppSpacing.sm)
                    }
                    
                    // Notifications Section
                    Section("Notifications") {
                        Toggle(isOn: $notificationsEnabled) {
                            HStack {
                                Image(systemName: "bell.fill")
                                    .foregroundColor(AppColors.primary)
                                    .frame(width: 24)
                                Text("Push Notifications")
                            }
                        }
                        
                        Toggle(isOn: .constant(true)) {
                            HStack {
                                Image(systemName: "envelope.fill")
                                    .foregroundColor(AppColors.primary)
                                    .frame(width: 24)
                                Text("Email Updates")
                            }
                        }
                    }
                    
                    // Draft Settings
                    Section("Draft Settings") {
                        Toggle(isOn: $autoBidEnabled) {
                            HStack {
                                Image(systemName: "bolt.fill")
                                    .foregroundColor(AppColors.warning)
                                    .frame(width: 24)
                                VStack(alignment: .leading, spacing: 2) {
                                    Text("Auto-Bid")
                                    Text("Automatically bid up to your limit")
                                        .font(AppFonts.small)
                                        .foregroundColor(AppColors.textMuted)
                                }
                            }
                        }
                        
                        NavigationLink(destination: Text("Draft Templates")) {
                            HStack {
                                Image(systemName: "doc.text.fill")
                                    .foregroundColor(AppColors.accent)
                                    .frame(width: 24)
                                Text("Draft Templates")
                            }
                        }
                    }
                    
                    // League Settings
                    Section("League") {
                        NavigationLink(destination: Text("Manage Leagues")) {
                            HStack {
                                Image(systemName: "person.3.fill")
                                    .foregroundColor(AppColors.primary)
                                    .frame(width: 24)
                                Text("My Leagues")
                            }
                        }
                        
                        NavigationLink(destination: Text("Create League")) {
                            HStack {
                                Image(systemName: "plus.circle.fill")
                                    .foregroundColor(AppColors.success)
                                    .frame(width: 24)
                                Text("Create League")
                            }
                        }
                    }
                    
                    // Support
                    Section("Support") {
                        NavigationLink(destination: Text("Help Center")) {
                            HStack {
                                Image(systemName: "questionmark.circle.fill")
                                    .foregroundColor(AppColors.primary)
                                    .frame(width: 24)
                                Text("Help Center")
                            }
                        }
                        
                        NavigationLink(destination: Text("Feedback")) {
                            HStack {
                                Image(systemName: "star.fill")
                                    .foregroundColor(AppColors.accent)
                                    .frame(width: 24)
                                Text("Send Feedback")
                            }
                        }
                        
                        NavigationLink(destination: Text("About")) {
                            HStack {
                                Image(systemName: "info.circle.fill")
                                    .foregroundColor(AppColors.textMuted)
                                    .frame(width: 24)
                                Text("About")
                            }
                        }
                    }
                    
                    // Account
                    Section {
                        Button(action: { showingLogoutAlert = true }) {
                            HStack {
                                Image(systemName: "rectangle.portrait.and.arrow.right")
                                    .foregroundColor(AppColors.error)
                                    .frame(width: 24)
                                Text("Log Out")
                                    .foregroundColor(AppColors.error)
                            }
                        }
                    }
                }
                .scrollContentBackground(.hidden)
            }
            .navigationTitle("Settings")
            .navigationBarTitleDisplayMode(.large)
            .alert("Log Out", isPresented: $showingLogoutAlert) {
                Button("Cancel", role: .cancel) {}
                Button("Log Out", role: .destructive) {
                    authViewModel.logout()
                }
            } message: {
                Text("Are you sure you want to log out?")
            }
        }
    }
}
