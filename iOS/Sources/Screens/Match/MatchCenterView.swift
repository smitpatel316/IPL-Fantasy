import SwiftUI

// MARK: - Match Center View
struct MatchCenterView: View {
    @StateObject private var viewModel = MatchViewModel()
    
    var body: some View {
        NavigationStack {
            ZStack {
                AppColors.background
                    .ignoresSafeArea()
                
                ScrollView {
                    VStack(spacing: AppSpacing.lg) {
                        // Live Match Card
                        if let match = viewModel.currentMatch {
                            liveMatchCard(match)
                        }
                        
                        // Category Breakdown
                        categoryBreakdown
                        
                        // Player Performances
                        playerPerformances
                    }
                    .padding(AppSpacing.md)
                }
            }
            .navigationTitle("Match Center")
            .navigationBarTitleDisplayMode(.large)
        }
    }
    
    private func liveMatchCard(_ match: LiveMatch) -> some View {
        VStack(spacing: AppSpacing.lg) {
            // Match Header
            HStack {
                VStack(alignment: .leading, spacing: AppSpacing.xs) {
                    Text(match.leagueName)
                        .font(AppFonts.caption)
                        .foregroundColor(AppColors.textSecondary)
                    
                    Text("Week \(match.week)")
                        .font(AppFonts.headline)
                        .fontWeight(.bold)
                        .foregroundColor(AppColors.textPrimary)
                }
                
                Spacer()
                
                // Live indicator
                HStack(spacing: AppSpacing.xs) {
                    Circle()
                        .fill(AppColors.error)
                        .frame(width: 8, height: 8)
                    Text("LIVE")
                        .font(AppFonts.caption)
                        .fontWeight(.bold)
                        .foregroundColor(AppColors.error)
                }
            }
            
            // Teams Score
            HStack(spacing: 0) {
                // Home Team
                VStack(spacing: AppSpacing.sm) {
                    Circle()
                        .fill(AppColors.primary.opacity(0.2))
                        .frame(width: 60, height: 60)
                        .overlay(
                            Text(String(match.homeTeam.name.prefix(1)))
                                .font(AppFonts.title)
                                .fontWeight(.bold)
                                .foregroundColor(AppColors.primary)
                        )
                    
                    Text(match.homeTeam.name)
                        .font(AppFonts.subheadline)
                        .fontWeight(.semibold)
                        .foregroundColor(AppColors.textPrimary)
                        .lineLimit(1)
                    
                    Text("\(match.homeTeam.points)")
                        .font(.system(size: 36, weight: .bold))
                        .foregroundColor(AppColors.textPrimary)
                }
                .frame(maxWidth: .infinity)
                
                // VS
                VStack(spacing: AppSpacing.xs) {
                    Text("VS")
                        .font(AppFonts.headline)
                        .fontWeight(.bold)
                        .foregroundColor(AppColors.textMuted)
                    
                    Text("vs")
                        .font(AppFonts.caption)
                        .foregroundColor(AppColors.textMuted)
                }
                .padding(.top, AppSpacing.lg)
                
                // Away Team
                VStack(spacing: AppSpacing.sm) {
                    Circle()
                        .fill(AppColors.accent.opacity(0.2))
                        .frame(width: 60, height: 60)
                        .overlay(
                            Text(String(match.awayTeam.name.prefix(1)))
                                .font(AppFonts.title)
                                .fontWeight(.bold)
                                .foregroundColor(AppColors.accent)
                        )
                    
                    Text(match.awayTeam.name)
                        .font(AppFonts.subheadline)
                        .fontWeight(.semibold)
                        .foregroundColor(AppColors.textPrimary)
                        .lineLimit(1)
                    
                    Text("\(match.awayTeam.points)")
                        .font(.system(size: 36, weight: .bold))
                        .foregroundColor(AppColors.textPrimary)
                }
                .frame(maxWidth: .infinity)
            }
            
            // Winner Prediction
            if match.homeTeam.points != match.awayTeam.points {
                HStack {
                    let leader = match.homeTeam.points > match.awayTeam.points ? match.homeTeam.name : match.awayTeam.name
                    let lead = abs(match.homeTeam.points - match.awayTeam.points)
                    Text("\(leader) leading by \(lead) points")
                        .font(AppFonts.caption)
                        .foregroundColor(AppColors.textSecondary)
                }
            }
            
            // Last Updated
            Text("Last updated: \(viewModel.lastUpdated)")
                .font(AppFonts.caption)
                .foregroundColor(AppColors.textMuted)
        }
        .padding(AppSpacing.lg)
        .background(AppColors.card)
        .cornerRadius(AppCornerRadius.card)
    }
    
    private var categoryBreakdown: some View {
        VStack(alignment: .leading, spacing: AppSpacing.md) {
            Text("Category Breakdown")
                .font(AppFonts.headline)
                .foregroundColor(AppColors.textPrimary)
            
            ForEach(viewModel.categories) { category in
                CategoryRow(category: category)
            }
        }
    }
    
    private var playerPerformances: some View {
        VStack(alignment: .leading, spacing: AppSpacing.md) {
            Text("Top Performers")
                .font(AppFonts.headline)
                .foregroundColor(AppColors.textPrimary)
            
            ForEach(viewModel.topPerformers) { player in
                PlayerPerformanceRow(player: player)
            }
        }
    }
}

struct CategoryRow: View {
    let category: MatchCategory
    
    var body: some View {
        HStack {
            Text(category.name)
                .font(AppFonts.subheadline)
                .foregroundColor(AppColors.textPrimary)
                .frame(width: 100, alignment: .leading)
            
            Text("\(Int(category.homeValue))")
                .font(AppFonts.subheadline)
                .fontWeight(.semibold)
                .foregroundColor(category.homeWon ? AppColors.success : AppColors.textSecondary)
                .frame(maxWidth: .infinity)
            
            Image(systemName: category.homeWon ? "checkmark.circle.fill" : "xmark.circle.fill")
                .foregroundColor(category.homeWon ? AppColors.success : AppColors.error)
                .frame(width: 30)
            
            Text("\(Int(category.awayValue))")
                .font(AppFonts.subheadline)
                .fontWeight(.semibold)
                .foregroundColor(category.awayWon ? AppColors.success : AppColors.textSecondary)
                .frame(maxWidth: .infinity)
                .multilineTextAlignment(.trailing)
        }
        .padding(AppSpacing.md)
        .background(AppColors.card)
        .cornerRadius(AppCornerRadius.small)
    }
}

struct PlayerPerformanceRow: View {
    let player: PlayerPerformance
    
    var body: some View {
        HStack(spacing: AppSpacing.md) {
            Circle()
                .fill(Color(hex: player.teamColor).opacity(0.2))
                .frame(width: 40, height: 40)
                .overlay(
                    Text(player.name.prefix(1))
                        .font(AppFonts.caption)
                        .fontWeight(.bold)
                        .foregroundColor(Color(hex: player.teamColor))
                )
            
            VStack(alignment: .leading, spacing: AppSpacing.xs) {
                Text(player.name)
                    .font(AppFonts.subheadline)
                    .fontWeight(.semibold)
                    .foregroundColor(AppColors.textPrimary)
                
                Text(player.team)
                    .font(AppFonts.caption)
                    .foregroundColor(AppColors.textSecondary)
            }
            
            Spacer()
            
            VStack(alignment: .trailing, spacing: AppSpacing.xs) {
                Text("+\(player.points) pts")
                    .font(AppFonts.subheadline)
                    .fontWeight(.bold)
                    .foregroundColor(AppColors.success)
                
                Text(player.highlights)
                    .font(AppFonts.caption)
                    .foregroundColor(AppColors.textMuted)
            }
        }
        .padding(AppSpacing.md)
        .background(AppColors.card)
        .cornerRadius(AppCornerRadius.small)
    }
}

// MARK: - Match View Model
@MainActor
class MatchViewModel: ObservableObject {
    @Published var currentMatch: LiveMatch?
    @Published var categories: [MatchCategory] = []
    @Published var topPerformers: [PlayerPerformance] = []
    @Published var lastUpdated = "Just now"
    
    init() {
        loadMockData()
    }
    
    func loadMockData() {
        currentMatch = LiveMatch(
            id: "1",
            leagueName: "Sunday League",
            week: 8,
            homeTeam: TeamScore(name: "Fire", points: 1245),
            awayTeam: TeamScore(name: "Bolt", points: 1198)
        )
        
        categories = [
            MatchCategory(name: "Total Points", homeValue: 1245, awayValue: 1198, homeWon: true),
            MatchCategory(name: "Boundaries", homeValue: 45, awayValue: 38, homeWon: true),
            MatchCategory(name: "Wickets", homeValue: 12, awayValue: 15, homeWon: false),
            MatchCategory(name: "Milestones", homeValue: 2, awayValue: 1, homeWon: true),
            MatchCategory(name: "Strike Rate", homeValue: 142, awayValue: 138, homeWon: true),
            MatchCategory(name: "Economy", homeValue: 7.2, awayValue: 7.8, homeWon: true),
            MatchCategory(name: "Catches", homeValue: 8, awayValue: 10, homeWon: false),
        ]
        
        topPerformers = [
            PlayerPerformance(name: "Jasprit Bumrah", team: "MI", teamColor: "#1E88E5", points: 62, highlights: "3 wickets"),
            PlayerPerformance(name: "Rohit Sharma", team: "MI", teamColor: "#1E88E5", points: 52, highlights: "45 runs"),
            PlayerPerformance(name: "Ravindra Jadeja", team: "CSK", teamColor: "#FDB913", points: 45, highlights: "2 wickets, 28 runs"),
            PlayerPerformance(name: "Andre Russell", team: "KKR", teamColor: "#552583", points: 42, highlights: "38 runs, 1 wicket"),
        ]
    }
}

struct LiveMatch: Identifiable {
    let id: String
    let leagueName: String
    let week: Int
    let homeTeam: TeamScore
    let awayTeam: TeamScore
}

struct TeamScore {
    let name: String
    let points: Int
}

struct MatchCategory: Identifiable {
    let id = UUID()
    let name: String
    let homeValue: Double
    let awayValue: Double
    
    var homeWon: Bool {
        if name == "Economy" {
            return homeValue < awayValue
        }
        return homeValue > awayValue
    }
    
    var awayWon: Bool {
        !homeWon
    }
}

struct PlayerPerformance: Identifiable {
    let id = UUID()
    let name: String
    let team: String
    let teamColor: String
    let points: Int
    let highlights: String
}
