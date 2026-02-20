import SwiftUI

// MARK: - Analytics Dashboard View
struct AnalyticsView: View {
    @StateObject private var viewModel = AnalyticsViewModel()
    
    var body: some View {
        NavigationStack {
            ZStack {
                AppColors.background
                    .ignoresSafeArea()
                
                ScrollView {
                    VStack(spacing: AppSpacing.lg) {
                        // Summary Cards
                        summaryCards
                        
                        // Points Breakdown
                        pointsBreakdown
                        
                        // Top Players
                        topPlayers
                        
                        // Performance Trend
                        performanceTrend
                        
                        // Value Analysis
                        valueAnalysis
                    }
                    .padding(AppSpacing.md)
                }
            }
            .navigationTitle("Analytics")
            .navigationBarTitleDisplayMode(.large)
        }
    }
    
    private var summaryCards: some View {
        VStack(spacing: AppSpacing.md) {
            HStack(spacing: AppSpacing.md) {
                AnalyticsCard(
                    title: "Total Points",
                    value: "\(viewModel.totalPoints)",
                    icon: "star.fill",
                    color: AppColors.accent
                )
                
                AnalyticsCard(
                    title: "Rank",
                    value: "#\(viewModel.rank)",
                    icon: "chart.bar.fill",
                    color: AppColors.primary
                )
            }
            
            HStack(spacing: AppSpacing.md) {
                AnalyticsCard(
                    title: "Wins",
                    value: "\(viewModel.wins)",
                    icon: "checkmark.circle.fill",
                    color: AppColors.success
                )
                
                AnalyticsCard(
                    title: "Categories Won",
                    value: "\(viewModel.categoriesWon)",
                    icon: "square.grid.2x2.fill",
                    color: AppColors.warning
                )
            }
        }
    }
    
    private var pointsBreakdown: some View {
        VStack(alignment: .leading, spacing: AppSpacing.md) {
            Text("Points Breakdown")
                .font(AppFonts.headline)
                .foregroundColor(AppColors.textPrimary)
            
            VStack(spacing: AppSpacing.sm) {
                PointsBar(category: "Batting", points: viewModel.battingPoints, total: viewModel.totalPoints, color: AppColors.success)
                PointsBar(category: "Bowling", points: viewModel.bowlingPoints, total: viewModel.totalPoints, color: AppColors.error)
                PointsBar(category: "Fielding", points: viewModel.fieldingPoints, total: viewModel.totalPoints, color: AppColors.primary)
                PointsBar(category: "Milestones", points: viewModel.milestonePoints, total: viewModel.totalPoints, color: AppColors.accent)
            }
        }
        .padding(AppSpacing.md)
        .background(AppColors.card)
        .cornerRadius(AppCornerRadius.medium)
    }
    
    private var topPlayers: some View {
        VStack(alignment: .leading, spacing: AppSpacing.md) {
            Text("Top Players")
                .font(AppFonts.headline)
                .foregroundColor(AppColors.textPrimary)
            
            ForEach(viewModel.topPlayers) { player in
                TopPlayerRow(player: player)
            }
        }
        .padding(AppSpacing.md)
        .background(AppColors.card)
        .cornerRadius(AppCornerRadius.medium)
    }
    
    private var performanceTrend: some View {
        VStack(alignment: .leading, spacing: AppSpacing.md) {
            Text("Performance Trend")
                .font(AppFonts.headline)
                .foregroundColor(AppColors.textPrimary)
            
            // Simple bar chart
            HStack(alignment: .bottom, spacing: AppSpacing.xs) {
                ForEach(viewModel.weeklyPoints, id: \.week) { week in
                    VStack(spacing: 4) {
                        RoundedRectangle(cornerRadius: 4)
                            .fill(week.points > 1000 ? AppColors.success : AppColors.primary)
                            .frame(width: 30, height: CGFloat(week.points) / 20)
                        
                        Text("W\(week.week)")
                            .font(AppFonts.small)
                            .foregroundColor(AppColors.textMuted)
                    }
                }
            }
            .frame(height: 150)
            .padding(AppSpacing.md)
        }
        .padding(AppSpacing.md)
        .background(AppColors.card)
        .cornerRadius(AppCornerRadius.medium)
    }
    
    private var valueAnalysis: some View {
        VStack(alignment: .leading, spacing: AppSpacing.md) {
            Text("Value Analysis")
                .font(AppFonts.headline)
                .foregroundColor(AppColors.textPrimary)
            
            HStack {
                VStack(alignment: .leading, spacing: AppSpacing.xs) {
                    Text("Best Value")
                        .font(AppFonts.caption)
                        .foregroundColor(AppColors.textSecondary)
                    Text(viewModel.bestValuePlayer.name)
                        .font(AppFonts.subheadline)
                        .fontWeight(.semibold)
                        .foregroundColor(AppColors.textPrimary)
                    Text("\(Int(viewModel.bestValuePlayer.roi))% ROI")
                        .font(AppFonts.body)
                        .foregroundColor(AppColors.success)
                }
                
                Spacer()
                
                VStack(alignment: .trailing, spacing: AppSpacing.xs) {
                    Text("Worst Value")
                        .font(AppFonts.caption)
                        .foregroundColor(AppColors.textSecondary)
                    Text(viewModel.worstValuePlayer.name)
                        .font(AppFonts.subheadline)
                        .fontWeight(.semibold)
                        .foregroundColor(AppColors.textPrimary)
                    Text("\(Int(viewModel.worstValuePlayer.roi))% ROI")
                        .font(AppFonts.body)
                        .foregroundColor(AppColors.error)
                }
            }
        }
        .padding(AppSpacing.md)
        .background(AppColors.card)
        .cornerRadius(AppCornerRadius.medium)
    }
}

// MARK: - Analytics Card
struct AnalyticsCard: View {
    let title: String
    let value: String
    let icon: String
    let color: Color
    
    var body: some View {
        VStack(alignment: .leading, spacing: AppSpacing.sm) {
            HStack {
                Image(systemName: icon)
                    .foregroundColor(color)
                Spacer()
            }
            
            Text(value)
                .font(AppFonts.title)
                .fontWeight(.bold)
                .foregroundColor(AppColors.textPrimary)
            
            Text(title)
                .font(AppFonts.caption)
                .foregroundColor(AppColors.textSecondary)
        }
        .padding(AppSpacing.md)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(AppColors.card)
        .cornerRadius(AppCornerRadius.medium)
    }
}

// MARK: - Points Bar
struct PointsBar: View {
    let category: String
    let points: Int
    let total: Int
    let color: Color
    
    var body: some View {
        VStack(alignment: .leading, spacing: AppSpacing.xs) {
            HStack {
                Text(category)
                    .font(AppFonts.caption)
                    .foregroundColor(AppColors.textSecondary)
                
                Spacer()
                
                Text("\(points) pts")
                    .font(AppFonts.caption)
                    .fontWeight(.semibold)
                    .foregroundColor(AppColors.textPrimary)
            }
            
            GeometryReader { geo in
                ZStack(alignment: .leading) {
                    RoundedRectangle(cornerRadius: 4)
                        .fill(AppColors.surface)
                        .frame(height: 8)
                    
                    RoundedRectangle(cornerRadius: 4)
                        .fill(color)
                        .frame(width: geo.size.width * CGFloat(points) / CGFloat(max(total, 1)), height: 8)
                }
            }
            .frame(height: 8)
        }
    }
}

// MARK: - Top Player Row
struct TopPlayerRow: View {
    let player: ValuePlayer
    
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
            
            VStack(alignment: .leading, spacing: 2) {
                Text(player.name)
                    .font(AppFonts.subheadline)
                    .fontWeight(.semibold)
                    .foregroundColor(AppColors.textPrimary)
                
                Text(player.team)
                    .font(AppFonts.caption)
                    .foregroundColor(AppColors.textSecondary)
            }
            
            Spacer()
            
            VStack(alignment: .trailing, spacing: 2) {
                Text("+\(player.points)")
                    .font(AppFonts.subheadline)
                    .fontWeight(.bold)
                    .foregroundColor(AppColors.success)
                
                Text("\(Int(player.roi))% value")
                    .font(AppFonts.small)
                    .foregroundColor(player.roi > 100 ? AppColors.success : AppColors.error)
            }
        }
    }
}

// MARK: - Analytics View Model
@MainActor
class AnalyticsViewModel: ObservableObject {
    @Published var totalPoints = 12450
    @Published var rank = 4
    @Published var wins = 45
    @Published var categoriesWon = 485
    
    @Published var battingPoints = 5602
    @Published var bowlingPoints = 3112
    @Published var fieldingPoints = 1868
    @Published var milestonePoints = 1245
    
    @Published var topPlayers: [ValuePlayer] = []
    @Published var weeklyPoints: [WeeklyPoints] = []
    @Published var bestValuePlayer = ValuePlayer(name: "Rinku Singh", team: "LSG", teamColor: "#4CAF50", points: 156, roi: 312)
    @Published var worstValuePlayer = ValuePlayer(name: "Expensive Player", team: "MI", teamColor: "#1E88E5", points: 120, roi: 67)
    
    init() {
        loadMockData()
    }
    
    private func loadMockData() {
        topPlayers = [
            ValuePlayer(name: "Jasprit Bumrah", team: "MI", teamColor: "#1E88E5", points: 468, roi: 260),
            ValuePlayer(name: "Virat Kohli", team: "RCB", teamColor: "#D32F2F", points: 412, roi: 229),
            ValuePlayer(name: "Rashid Khan", team: "GT", teamColor: "#4CAF50", points: 356, roi: 254),
            ValuePlayer(name: "Andre Russell", team: "KKR", teamColor: "#552583", points: 312, roi: 260),
            ValuePlayer(name: "Ravindra Jadeja", team: "CSK", teamColor: "#FDB913", points: 289, roi: 207),
        ]
        
        weeklyPoints = [
            WeeklyPoints(week: 1, points: 1156),
            WeeklyPoints(week: 2, points: 892),
            WeeklyPoints(week: 3, points: 1345),
            WeeklyPoints(week: 4, points: 1023),
            WeeklyPoints(week: 5, points: 1456),
            WeeklyPoints(week: 6, points: 987),
            WeeklyPoints(week: 7, points: 1234),
            WeeklyPoints(week: 8, points: 1245),
        ]
    }
}

struct ValuePlayer: Identifiable {
    let id = UUID()
    let name: String
    let team: String
    let teamColor: String
    let points: Int
    let roi: Double
}

struct WeeklyPoints: Identifiable {
    let id = UUID()
    let week: Int
    let points: Int
}
