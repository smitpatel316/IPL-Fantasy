import SwiftUI

// MARK: - AI Recommendations View
struct AIRecommendationsView: View {
    @StateObject private var viewModel = AIRecommendationsViewModel()
    
    var body: some View {
        NavigationStack {
            ZStack {
                AppColors.background
                    .ignoresSafeArea()
                
                ScrollView {
                    VStack(spacing: AppSpacing.lg) {
                        // AI Insights Card
                        insightsCard
                        
                        // Recommended Players
                        recommendationsSection
                        
                        // Value Picks
                        valuePicksSection
                        
                        // Avoid Players
                        avoidSection
                        
                        // Matchup Analysis
                        matchupAnalysis
                    }
                    .padding(AppSpacing.md)
                }
            }
            .navigationTitle("AI Insights")
            .navigationBarTitleDisplayMode(.large)
        }
    }
    
    private var insightsCard: some View {
        VStack(alignment: .leading, spacing: AppSpacing.md) {
            HStack {
                Image(systemName: "brain.head.profile")
                    .font(.system(size: 24))
                    .foregroundColor(AppColors.primary)
                
                Text("AI Analysis")
                    .font(AppFonts.headline)
                    .foregroundColor(AppColors.textPrimary)
                
                Spacer()
                
                Text("Updated: Just now")
                    .font(AppFonts.caption)
                    .foregroundColor(AppColors.textMuted)
            }
            
            Text("Based on recent form, pitch conditions, and opponent analysis")
                .font(AppFonts.body)
                .foregroundColor(AppColors.textSecondary)
            
            // Key Insights
            VStack(alignment: .leading, spacing: AppSpacing.sm) {
                InsightRow(icon: "flame.fill", text: "Power hitters performing well in Wankhede", color: .orange)
                InsightRow(icon: "drop.fill", text: "Swing bowling advantage due to morning moisture", color: .blue)
                InsightRow(icon: "person.fill.questionmark", text: "Rohit Sharma has poor record vs left-arm pacers", color: AppColors.warning)
            }
        }
        .padding(AppSpacing.lg)
        .background(AppColors.card)
        .cornerRadius(AppCornerRadius.card)
    }
    
    private var recommendationsSection: some View {
        VStack(alignment: .leading, spacing: AppSpacing.md) {
            HStack {
                Text("Recommended Players")
                    .font(AppFonts.headline)
                    .foregroundColor(AppColors.textPrimary)
                
                Spacer()
                
                Text("Based on ML model")
                    .font(AppFonts.caption)
                    .foregroundColor(AppColors.textMuted)
            }
            
            ForEach(viewModel.recommendations) { player in
                AIRecommendationRow(player: player)
            }
        }
    }
    
    private var valuePicksSection: some View {
        VStack(alignment: .leading, spacing: AppSpacing.md) {
            HStack {
                Text("Best Value Picks")
                    .font(AppFonts.headline)
                    .foregroundColor(AppColors.textPrimary)
                
                Spacer()
                
                Text("High ROI")
                    .font(AppFonts.caption)
                    .foregroundColor(AppColors.success)
            }
            
            ForEach(viewModel.valuePicks) { player in
                ValuePickRow(player: player)
            }
        }
    }
    
    private var avoidSection: some View {
        VStack(alignment: .leading, spacing: AppSpacing.md) {
            HStack {
                Text("Players to Avoid")
                    .font(AppFonts.headline)
                    .foregroundColor(AppColors.textPrimary)
                
                Spacer()
                
                Text("Low confidence")
                    .font(AppFonts.caption)
                    .foregroundColor(AppColors.error)
            }
            
            ForEach(viewModel.avoidPlayers) { player in
                AvoidPlayerRow(player: player)
            }
        }
    }
    
    private var matchupAnalysis: some View {
        VStack(alignment: .leading, spacing: AppSpacing.md) {
            Text("Matchup Analysis")
                .font(AppFonts.headline)
                .foregroundColor(AppColors.textPrimary)
            
            ForEach(viewModel.matchupAnalysis) { matchup in
                MatchupAnalysisCard(matchup: matchup)
            }
        }
    }
}

struct InsightRow: View {
    let icon: String
    let text: String
    let color: Color
    
    var body: some View {
        HStack(spacing: AppSpacing.sm) {
            Image(systemName: icon)
                .foregroundColor(color)
                .frame(width: 20)
            
            Text(text)
                .font(AppFonts.caption)
                .foregroundColor(AppColors.textSecondary)
        }
    }
}

struct AIRecommendationRow: View {
    let player: AIRecommendedPlayer
    
    var body: some View {
        HStack(spacing: AppSpacing.md) {
            // Confidence indicator
            Circle()
                .fill(confidenceColor)
                .frame(width: 8, height: 8)
            
            VStack(alignment: .leading, spacing: AppSpacing.xs) {
                HStack {
                    Text(player.name)
                        .font(AppFonts.subheadline)
                        .fontWeight(.semibold)
                        .foregroundColor(AppColors.textPrimary)
                    
                    Text(player.team)
                        .font(AppFonts.caption)
                        .foregroundColor(AppColors.textMuted)
                }
                
                Text(player.reason)
                    .font(AppFonts.caption)
                    .foregroundColor(AppColors.textSecondary)
                    .lineLimit(2)
            }
            
            Spacer()
            
            VStack(alignment: .trailing, spacing: AppSpacing.xs) {
                Text("\(player.projectedPoints) pts")
                    .font(AppFonts.subheadline)
                    .fontWeight(.bold)
                    .foregroundColor(AppColors.success)
                
                Text("₹\(Int(player.price))Cr")
                    .font(AppFonts.caption)
                    .foregroundColor(AppColors.accent)
            }
        }
        .padding(AppSpacing.md)
        .background(AppColors.card)
        .cornerRadius(AppCornerRadius.medium)
    }
    
    private var confidenceColor: Color {
        switch player.confidence {
        case 90...: return AppColors.success
        case 70..<90: return AppColors.warning
        default: return AppColors.error
        }
    }
}

struct ValuePickRow: View {
    let player: AIRecommendedPlayer
    
    var body: some View {
        HStack(spacing: AppSpacing.md) {
            Image(systemName: "star.fill")
                .foregroundColor(.yellow)
                .frame(width: 24)
            
            VStack(alignment: .leading, spacing: AppSpacing.xs) {
                Text(player.name)
                    .font(AppFonts.subheadline)
                    .foregroundColor(AppColors.textPrimary)
                
                Text("\(player.roi)% ROI")
                    .font(AppFonts.caption)
                    .foregroundColor(AppColors.success)
            }
            
            Spacer()
            
            Text("₹\(Int(player.price))Cr")
                .font(AppFonts.subheadline)
                .foregroundColor(AppColors.accent)
        }
        .padding(AppSpacing.md)
        .background(AppColors.card)
        .cornerRadius(AppCornerRadius.medium)
    }
}

struct AvoidPlayerRow: View {
    let player: AIRecommendedPlayer
    
    var body: some View {
        HStack(spacing: AppSpacing.md) {
            Image(systemName: "exclamationmark.triangle.fill")
                .foregroundColor(AppColors.error)
                .frame(width: 24)
            
            VStack(alignment: .leading, spacing: AppSpacing.xs) {
                Text(player.name)
                    .font(AppFonts.subheadline)
                    .foregroundColor(AppColors.textPrimary)
                
                Text(player.reason)
                    .font(AppFonts.caption)
                    .foregroundColor(AppColors.textSecondary)
                    .lineLimit(1)
            }
            
            Spacer()
        }
        .padding(AppSpacing.md)
        .background(AppColors.error.opacity(0.1))
        .cornerRadius(AppCornerRadius.medium)
    }
}

struct MatchupAnalysisCard: View {
    let matchup: MatchupAnalysis
    
    var body: some View {
        VStack(alignment: .leading, spacing: AppSpacing.sm) {
            HStack {
                Text(matchup.team1)
                    .font(AppFonts.subheadline)
                    .fontWeight(.bold)
                    .foregroundColor(AppColors.textPrimary)
                
                Text("vs")
                    .font(AppFonts.caption)
                    .foregroundColor(AppColors.textMuted)
                
                Text(matchup.team2)
                    .font(AppFonts.subheadline)
                    .fontWeight(.bold)
                    .foregroundColor(AppColors.textPrimary)
            }
            
            Text(matchup.insight)
                .font(AppFonts.caption)
                .foregroundColor(AppColors.textSecondary)
            
            HStack {
                Text("Win Probability:")
                    .font(AppFonts.caption)
                    .foregroundColor(AppColors.textMuted)
                
                Text("\(matchup.winProbability)%")
                    .font(AppFonts.caption)
                    .fontWeight(.bold)
                    .foregroundColor(AppColors.success)
            }
        }
        .padding(AppSpacing.md)
        .background(AppColors.card)
        .cornerRadius(AppCornerRadius.medium)
    }
}

// MARK: - AI View Model
@MainActor
class AIRecommendationsViewModel: ObservableObject {
    @Published var recommendations: [AIRecommendedPlayer] = []
    @Published var valuePicks: [AIRecommendedPlayer] = []
    @Published var avoidPlayers: [AIRecommendedPlayer] = []
    @Published var matchupAnalysis: [MatchupAnalysis] = []
    
    init() {
        loadMockData()
    }
    
    private func loadMockData() {
        recommendations = [
            AIRecommendedPlayer(id: "1", name: "Jasprit Bumrah", team: "MI", price: 18, projectedPoints: 65, confidence: 92, reason: "Excellent form, bowling on home pitch", roi: 0),
            AIRecommendedPlayer(id: "2", name: "Virat Kohli", team: "RCB", price: 18, projectedPoints: 58, confidence: 88, reason: "Consistent scorer, good matchup", roi: 0),
            AIRecommendedPlayer(id: "3", name: "Rashid Khan", team: "GT", price: 14, projectedPoints: 52, confidence: 85, reason: "Wicket-taking threat in powerplay", roi: 0),
        ]
        
        valuePicks = [
            AIRecommendedPlayer(id: "4", name: "Tilak Varma", team: "MI", price: 6, projectedPoints: 45, confidence: 75, reason: "Young talent, high upside", roi: 280),
            AIRecommendedPlayer(id: "5", name: "Ravi Bishnoi", team: "LSG", price: 5, projectedPoints: 38, confidence: 70, reason: "Wicket-taker, economical", roi: 320),
        ]
        
        avoidPlayers = [
            AIRecommendedPlayer(id: "6", name: "Rohit Sharma", team: "MI", price: 16, projectedPoints: 35, confidence: 45, reason: "Poor form against left-arm pace"),
            AIRecommendedPlayer(id: "7", name: "KL Rahul", team: "LSG", price: 14, projectedPoints: 32, confidence: 40, reason: "Batting lower order concerns"),
        ]
        
        matchupAnalysis = [
            MatchupAnalysis(id: "1", team1: "MI", team2: "CSK", insight: "Spinners have dominated in recent matches at Wankhede", winProbability: 58),
            MatchupAnalysis(id: "2", team1: "RCB", team2: "KKR", insight: "High-scoring venue, pace bowlers have edge", winProbability: 52),
        ]
    }
}

struct AIRecommendedPlayer: Identifiable {
    let id: String
    let name: String
    let team: String
    let price: Double
    let projectedPoints: Int
    let confidence: Int
    let reason: String
    let roi: Int
}

struct MatchupAnalysis: Identifiable {
    let id: String
    let team1: String
    let team2: String
    let insight: String
    let winProbability: Int
}
