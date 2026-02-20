import SwiftUI

// MARK: - Settings View
struct SettingsView: View {
    @EnvironmentObject var authViewModel: AuthViewModel
    @AppStorage("notificationsEnabled") private var notificationsEnabled = true
    @AppStorage("soundEnabled") private var soundEnabled = true
    @AppStorage("hapticsEnabled") private var hapticsEnabled = true
    @AppStorage("darkModeEnabled") private var darkModeEnabled = true
    
    var body: some View {
        NavigationStack {
            ZStack {
                AppColors.background
                    .ignoresSafeArea()
                
                ScrollView {
                    VStack(spacing: AppSpacing.lg) {
                        // Notifications
                        settingsSection(title: "Notifications") {
                            SettingsToggle(
                                icon: "bell.fill",
                                title: "Push Notifications",
                                subtitle: "Match updates, league activity",
                                isOn: $notificationsEnabled
                            )
                            
                            SettingsToggle(
                                icon: "envelope.fill",
                                title: "Email Notifications",
                                subtitle: "Weekly summaries, promotions",
                                isOn: $notificationsEnabled
                            )
                        }
                        
                        // Sound & Haptics
                        settingsSection(title: "Sound & Feel") {
                            SettingsToggle(
                                icon: "speaker.wave.2.fill",
                                title: "Sound Effects",
                                subtitle: "App sounds",
                                isOn: $soundEnabled
                            )
                            
                            SettingsToggle(
                                icon: "iphone.radiowaves.left.and.right",
                                title: "Haptic Feedback",
                                subtitle: "Vibration on interactions",
                                isOn: $hapticsEnabled
                            )
                        }
                        
                        // Appearance
                        settingsSection(title: "Appearance") {
                            SettingsToggle(
                                icon: "moon.fill",
                                title: "Dark Mode",
                                subtitle: "Use dark theme",
                                isOn: $darkModeEnabled
                            )
                        }
                        
                        // Data & Privacy
                        settingsSection(title: "Data & Privacy") {
                            SettingsRow(icon: "arrow.down.doc", title: "Download My Data", color: AppColors.primary)
                            SettingsRow(icon: "trash", title: "Delete Account", color: AppColors.error)
                        }
                        
                        // About
                        settingsSection(title: "About") {
                            SettingsInfoRow(title: "Version", value: "1.0.0")
                            SettingsInfoRow(title: "Build", value: "2026.02.20")
                            SettingsRow(icon: "doc.text", title: "Terms of Service", color: AppColors.textMuted)
                            SettingsRow(icon: "hand.raised", title: "Privacy Policy", color: AppColors.textMuted)
                            SettingsRow(icon: "questionmark.circle", title: "Help Center", color: AppColors.textMuted)
                        }
                        
                        // Logout
                        Button(action: { authViewModel.logout() }) {
                            Text("Log Out")
                                .font(AppFonts.subheadline)
                                .fontWeight(.semibold)
                                .foregroundColor(AppColors.error)
                                .frame(maxWidth: .infinity)
                                .padding(.vertical, AppSpacing.md)
                                .background(AppColors.error.opacity(0.1))
                                .cornerRadius(AppCornerRadius.medium)
                        }
                        .padding(.top, AppSpacing.md)
                    }
                    .padding(AppSpacing.md)
                }
            }
            .navigationTitle("Settings")
            .navigationBarTitleDisplayMode(.large)
        }
    }
    
    private func settingsSection<Content: View>(title: String, @ViewBuilder content: () -> Content) -> some View {
        VStack(alignment: .leading, spacing: AppSpacing.sm) {
            Text(title)
                .font(AppFonts.headline)
                .foregroundColor(AppColors.textPrimary)
            
            VStack(spacing: 0) {
                content()
            }
            .background(AppColors.card)
            .cornerRadius(AppCornerRadius.medium)
        }
    }
}

struct SettingsToggle: View {
    let icon: String
    let title: String
    let subtitle: String
    @Binding var isOn: Bool
    
    var body: some View {
        HStack(spacing: AppSpacing.md) {
            Image(systemName: icon)
                .font(.system(size: 18))
                .foregroundColor(AppColors.primary)
                .frame(width: 24)
            
            VStack(alignment: .leading, spacing: 2) {
                Text(title)
                    .font(AppFonts.body)
                    .foregroundColor(AppColors.textPrimary)
                
                Text(subtitle)
                    .font(AppFonts.caption)
                    .foregroundColor(AppColors.textSecondary)
            }
            
            Spacer()
            
            Toggle("", isOn: $isOn)
                .tint(AppColors.primary)
        }
        .padding(AppSpacing.md)
    }
}

struct SettingsInfoRow: View {
    let title: String
    let value: String
    
    var body: some View {
        HStack {
            Text(title)
                .font(AppFonts.body)
                .foregroundColor(AppColors.textPrimary)
            
            Spacer()
            
            Text(value)
                .font(AppFonts.body)
                .foregroundColor(AppColors.textSecondary)
        }
        .padding(AppSpacing.md)
    }
}
