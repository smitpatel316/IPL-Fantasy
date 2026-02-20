import SwiftUI

// MARK: - Profile View
struct ProfileView: View {
    @EnvironmentObject var authViewModel: AuthViewModel
    @StateObject private var viewModel = ProfileViewModel()
    
    var body: some View {
        NavigationStack {
            ZStack {
                AppColors.background
                    .ignoresSafeArea()
                
                ScrollView {
                    VStack(spacing: AppSpacing.lg) {
                        // Profile Header
                        profileHeader
                        
                        // Stats
                        statsSection
                        
                        // Achievements
                        achievementsSection
                        
                        // Settings List
                        settingsSection
                        
                        // Logout
                        logoutButton
                    }
                    .padding(AppSpacing.md)
                }
            }
            .navigationTitle("Profile")
            .navigationBarTitleDisplayMode(.large)
        }
    }
    
    private var profileHeader: some View {
        VStack(spacing: AppSpacing.md) {
            // Avatar
            ZStack {
                Circle()
                    .fill(AppColors.primary.opacity(0.2))
                    .frame(width: 100, height: 100)
                
                Text(viewModel.displayName.prefix(1).uppercased())
                    .font(.system(size: 40, weight: .bold))
                    .foregroundColor(AppColors.primary)
            }
            
            // Name
            Text(viewModel.displayName)
                .font(AppFonts.title)
                .fontWeight(.bold)
                .foregroundColor(AppColors.textPrimary)
            
            // Email
            Text(viewModel.email)
                .font(AppFonts.body)
                .foregroundColor(AppColors.textSecondary)
            
            // Edit Button
            Button(action: {}) {
                Text("Edit Profile")
                    .font(AppFonts.subheadline)
                    .fontWeight(.medium)
                    .foregroundColor(AppColors.primary)
                    .padding(.horizontal, AppSpacing.lg)
                    .padding(.vertical, AppSpacing.sm)
                    .background(AppColors.primary.opacity(0.1))
                    .cornerRadius(AppCornerRadius.medium)
            }
        }
        .padding(AppSpacing.lg)
        .frame(maxWidth: .infinity)
        .background(AppColors.card)
        .cornerRadius(AppCornerRadius.card)
    }
    
    private var statsSection: some View {
        VStack(alignment: .leading, spacing: AppSpacing.md) {
            Text("Lifetime Stats")
                .font(AppFonts.headline)
                .foregroundColor(AppColors.textPrimary)
            
            HStack(spacing: AppSpacing.md) {
                StatBox(title: "Leagues", value: "\(viewModel.stats.leaguesJoined)", icon: "person.3")
                StatBox(title: "Wins", value: "\(viewModel.stats.championships)", icon: "trophy.fill")
                StatBox(title: "Points", value: formatPoints(viewModel.stats.totalPoints), icon: "star.fill")
            }
            
            HStack(spacing: AppSpacing.md) {
                StatBox(title: "Best Rank", value: "#\(viewModel.stats.bestRank)", icon: "chart.bar")
                StatBox(title: "Seasons", value: "\(viewModel.stats.seasonsPlayed)", icon: "calendar")
            }
        }
    }
    
    private var achievementsSection: some View {
        VStack(alignment: .leading, spacing: AppSpacing.md) {
            Text("Achievements")
                .font(AppFonts.headline)
                .foregroundColor(AppColors.textPrimary)
            
            LazyVGrid(columns: [
                GridItem(.flexible()),
                GridItem(.flexible()),
                GridItem(.flexible())
            ], spacing: AppSpacing.md) {
                ForEach(viewModel.achievements) { achievement in
                    AchievementBadge(achievement: achievement)
                }
            }
        }
    }
    
    private var settingsSection: some View {
        VStack(alignment: .leading, spacing: AppSpacing.md) {
            Text("Settings")
                .font(AppFonts.headline)
                .foregroundColor(AppColors.textPrimary)
            
            VStack(spacing: 0) {
                SettingsRow(icon: "bell", title: "Notifications", color: AppColors.warning)
                Divider().background(AppColors.textMuted.opacity(0.2))
                SettingsRow(icon: "lock", title: "Privacy", color: AppColors.primary)
                Divider().background(AppColors.textMuted.opacity(0.2))
                SettingsRow(icon: "questionmark.circle", title: "Help & Support", color: AppColors.success)
                Divider().background(AppColors.textMuted.opacity(0.2))
                SettingsRow(icon: "doc.text", title: "Terms of Service", color: AppColors.textMuted)
                Divider().background(AppColors.textMuted.opacity(0.2))
                SettingsRow(icon: "info.circle", title: "About", color: AppColors.textMuted)
            }
            .background(AppColors.card)
            .cornerRadius(AppCornerRadius.medium)
        }
    }
    
    private var logoutButton: some View {
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
    }
    
    private func formatPoints(_ points: Int) -> String {
        if points >= 1000 {
            return "\(points / 1000)k"
        }
        return "\(points)"
    }
}

struct StatBox: View {
    let title: String
    let value: String
    let icon: String
    
    var body: some View {
        VStack(spacing: AppSpacing.sm) {
            Image(systemName: icon)
                .font(.system(size: 20))
                .foregroundColor(AppColors.primary)
            
            Text(value)
                .font(AppFonts.headline)
                .fontWeight(.bold)
                .foregroundColor(AppColors.textPrimary)
            
            Text(title)
                .font(AppFonts.caption)
                .foregroundColor(AppColors.textSecondary)
        }
        .frame(maxWidth: .infinity)
        .padding(AppSpacing.md)
        .background(AppColors.card)
        .cornerRadius(AppCornerRadius.medium)
    }
}

struct AchievementBadge: View {
    let achievement: Achievement
    
    var body: some View {
        VStack(spacing: AppSpacing.xs) {
            ZStack {
                Circle()
                    .fill(achievement.earned ? achievement.color.opacity(0.2) : AppColors.surface)
                    .frame(width: 60, height: 60)
                
                Image(systemName: achievement.icon)
                    .font(.system(size: 24))
                    .foregroundColor(achievement.earned ? achievement.color : AppColors.textMuted)
            }
            
            Text(achievement.name)
                .font(AppFonts.small)
                .foregroundColor(achievement.earned ? AppColors.textPrimary : AppColors.textMuted)
                .multilineTextAlignment(.center)
        }
    }
}

struct SettingsRow: View {
    let icon: String
    let title: String
    let color: Color
    
    var body: some View {
        Button(action: {}) {
            HStack(spacing: AppSpacing.md) {
                Image(systemName: icon)
                    .font(.system(size: 18))
                    .foregroundColor(color)
                    .frame(width: 24)
                
                Text(title)
                    .font(AppFonts.body)
                    .foregroundColor(AppColors.textPrimary)
                
                Spacer()
                
                Image(systemName: "chevron.right")
                    .font(.system(size: 14))
                    .foregroundColor(AppColors.textMuted)
            }
            .padding(AppSpacing.md)
        }
    }
}

// MARK: - Profile View Model
@MainActor
class ProfileViewModel: ObservableObject {
    @Published var displayName = "John Doe"
    @Published var email = "john@example.com"
    @Published var stats = UserStats()
    @Published var achievements: [Achievement] = []
    
    init() {
        loadMockData()
    }
    
    private func loadMockData() {
        stats = UserStats(
            leaguesJoined: 15,
            championships: 3,
            totalPoints: 45230,
            bestRank: 12,
            seasonsPlayed: 5
        )
        
        achievements = [
            Achievement(id: "1", name: "Champion", icon: "trophy.fill", color: .yellow, earned: true),
            Achievement(id: "2", name: "First Win", icon: "star.fill", color: AppColors.success, earned: true),
            Achievement(id: "3", name: "Trader", icon: "arrow.left.arrow.right", color: AppColors.accent, earned: true),
            Achievement(id: "4", name: "Dedicated", icon: "calendar", color: AppColors.primary, earned: true),
            Achievement(id: "5", name: "High Scorer", icon: "flame.fill", color: .orange, earned: false),
            Achievement(id: "6", name: "Perfect Team", icon: "checkmark.seal.fill", color: AppColors.success, earned: false),
        ]
    }
}

struct UserStats {
    var leaguesJoined: Int = 0
    var championships: Int = 0
    var totalPoints: Int = 0
    var bestRank: Int = 0
    var seasonsPlayed: Int = 0
}

struct Achievement: Identifiable {
    let id: String
    let name: String
    let icon: String
    let color: Color
    let earned: Bool
}
