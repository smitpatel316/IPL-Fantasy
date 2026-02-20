import SwiftUI

// MARK: - Dashboard View
struct DashboardView: View {
    @EnvironmentObject var authViewModel: AuthViewModel
    @StateObject private var leagueViewModel = LeagueViewModel()
    
    var body: some View {
        NavigationStack {
            ZStack {
                AppColors.background
                    .ignoresSafeArea()
                
                ScrollView {
                    VStack(spacing: AppSpacing.lg) {
                        // Welcome Header
                        welcomeHeader
                        
                        // Quick Stats
                        quickStats
                        
                        // Active Matches
                        activeMatchesSection
                        
                        // Your Leagues
                        yourLeaguesSection
                    }
                    .padding(AppSpacing.md)
                }
            }
            .navigationTitle("Dashboard")
            .navigationBarTitleDisplayMode(.large)
            .toolbar {
                ToolbarItem(placement: .navigationBarTrailing) {
                    Button(action: { authViewModel.logout() }) {
                        Image(systemName: "rectangle.portrait.and.arrow.right")
                            .foregroundColor(AppColors.primary)
                    }
                }
            }
        }
    }
    
    private var welcomeHeader: some View {
        VStack(alignment: .leading, spacing: AppSpacing.sm) {
            Text("Welcome back,")
                .font(AppFonts.subheadline)
                .foregroundColor(AppColors.textSecondary)
            
            Text(authViewModel.currentUser?.displayName ?? "User")
                .font(AppFonts.title)
                .fontWeight(.bold)
                .foregroundColor(AppColors.textPrimary)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
    }
    
    private var quickStats: some View {
        HStack(spacing: AppSpacing.md) {
            StatCard(title: "Leagues", value: "\(leagueViewModel.leagues.count)", icon: "person.3.fill", color: AppColors.primary)
            StatCard(title: "Matches", value: "0", icon: "sportscourt.fill", color: AppColors.accent)
            StatCard(title: "Points", value: "0", icon: "star.fill", color: AppColors.success)
        }
    }
    
    private var activeMatchesSection: some View {
        VStack(alignment: .leading, spacing: AppSpacing.md) {
            Text("Live Matches")
                .font(AppFonts.headline)
                .foregroundColor(AppColors.textPrimary)
            
            // Mock live match
            CardView {
                HStack {
                    VStack(alignment: .leading, spacing: AppSpacing.xs) {
                        Text("MI vs CSK")
                            .font(AppFonts.subheadline)
                            .fontWeight(.bold)
                            .foregroundColor(AppColors.textPrimary)
                        
                        Text("TATA IPL 2024")
                            .font(AppFonts.caption)
                            .foregroundColor(AppColors.textSecondary)
                    }
                    
                    Spacer()
                    
                    VStack(alignment: .trailing, spacing: AppSpacing.xs) {
                        Text("MI 156/3")
                            .font(AppFonts.subheadline)
                            .foregroundColor(AppColors.textPrimary)
                        
                        HStack(spacing: AppSpacing.xs) {
                            Circle()
                                .fill(AppColors.error)
                                .frame(width: 6, height: 6)
                            Text("LIVE")
                                .font(AppFonts.small)
                                .fontWeight(.bold)
                                .foregroundColor(AppColors.error)
                        }
                    }
                }
            }
        }
    }
    
    private var yourLeaguesSection: some View {
        VStack(alignment: .leading, spacing: AppSpacing.md) {
            HStack {
                Text("Your Leagues")
                    .font(AppFonts.headline)
                    .foregroundColor(AppColors.textPrimary)
                
                Spacer()
                
                NavigationLink(destination: LeagueListView()) {
                    Text("See All")
                        .font(AppFonts.caption)
                        .foregroundColor(AppColors.primary)
                }
            }
            
            if leagueViewModel.leagues.isEmpty {
                EmptyStateView(
                    icon: "person.3",
                    title: "No Leagues Yet",
                    message: "Create or join a league to get started",
                    buttonTitle: "Join League"
                )
                .frame(height: 200)
            } else {
                ForEach(leagueViewModel.leagues.prefix(3)) { league in
                    LeagueCard(league: league)
                }
            }
        }
    }
}

// MARK: - Stat Card
struct StatCard: View {
    let title: String
    let value: String
    let icon: String
    let color: Color
    
    var body: some View {
        VStack(spacing: AppSpacing.sm) {
            Image(systemName: icon)
                .font(.system(size: 24))
                .foregroundColor(color)
            
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

// MARK: - League Card
struct LeagueCard: View {
    let league: League
    
    var body: some View {
        NavigationLink(destination: LeagueDetailView(league: league)) {
            CardView {
                HStack {
                    VStack(alignment: .leading, spacing: AppSpacing.xs) {
                        Text(league.name)
                            .font(AppFonts.subheadline)
                            .fontWeight(.bold)
                            .foregroundColor(AppColors.textPrimary)
                        
                        HStack(spacing: AppSpacing.sm) {
                            Text("\(league.members.count)/\(league.maxTeams) Teams")
                                .font(AppFonts.caption)
                                .foregroundColor(AppColors.textSecondary)
                            
                            Text("•")
                                .foregroundColor(AppColors.textMuted)
                            
                            BadgeView(text: league.status.rawValue.capitalized, color: statusColor)
                        }
                    }
                    
                    Spacer()
                    
                    Image(systemName: "chevron.right")
                        .foregroundColor(AppColors.textMuted)
                }
            }
        }
        .buttonStyle(PlainButtonStyle())
    }
    
    private var statusColor: Color {
        switch league.status {
        case .open: return AppColors.success
        case .drafting: return AppColors.warning
        case .active: return AppColors.primary
        case .completed: return AppColors.textMuted
        }
    }
}
