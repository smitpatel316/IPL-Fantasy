import SwiftUI

// MARK: - Stats Detail View
struct StatsDetailView: View {
    @StateObject private var viewModel = StatsDetailViewModel()
    
    var body: some View {
        NavigationStack {
            ZStack {
                AppColors.background
                    .ignoresSafeArea()
                
                ScrollView {
                    VStack(spacing: AppSpacing.lg) {
                        // Overview Cards
                        overviewSection
                        
                        // Points Breakdown
                        pointsBreakdownSection
                        
                        // Category Performance
                        categorySection
                        
                        // History Chart
                        historySection
                    }
                    .padding(AppSpacing.md)
                }
            }
            .navigationTitle("Statistics")
            .navigationBarTitleDisplayMode(.large)
        }
    }
    
    private var overviewSection: some View {
        HStack(spacing: AppSpacing.md) {
            StatCard(title: "Total Points", value: "\(viewModel.totalPoints)", icon: "star.fill", color: .yellow)
            StatCard(title: "This Week", value: "+\(viewModel.weeklyPoints)", icon: "arrow.up", color: .green)
        }
    }
    
    private var pointsBreakdownSection: some View {
        VStack(alignment: .leading, spacing: AppSpacing.md) {
            Text("Points Breakdown")
                .font(AppFonts.headline)
                .foregroundColor(AppColors.textPrimary)
            
            VStack(spacing: AppSpacing.sm) {
                PointsBar(label: "Batting", points: viewModel.battingPoints, total: viewModel.totalPoints, color: .green)
                PointsBar(label: "Bowling", points: viewModel.bowlingPoints, total: viewModel.totalPoints, color: .red)
                PointsBar(label: "Fielding", points: viewModel.fieldingPoints, total: viewModel.totalPoints, color: .blue)
                PointsBar(label: "Milestones", points: viewModel.milestonePoints, total: viewModel.totalPoints, color: .purple)
            }
        }
        .padding(AppSpacing.md)
        .background(AppColors.card)
        .cornerRadius(AppCornerRadius.medium)
    }
    
    private var categorySection: some View {
        VStack(alignment: .leading, spacing: AppSpacing.md) {
            Text("Category Performance")
                .font(AppFonts.headline)
                .foregroundColor(AppColors.textPrimary)
            
            LazyVGrid(columns: [GridItem(.flexible()), GridItem(.flexible())], spacing: AppSpacing.sm) {
                CategoryCard(title: "Wins", value: "\(viewModel.categoryWins)", icon: "trophy.fill", color: .green)
                CategoryCard(title: "Losses", value: "\(viewModel.categoryLosses)", icon: "xmark.circle.fill", color: .red)
                CategoryCard(title: "Ties", value: "\(viewModel.categoryTies)", icon: "equal.circle.fill", color: .gray)
                CategoryCard(title: "Win Rate", value: "\(viewModel.winRate)%", icon: "chart.pie.fill", color: .blue)
            }
        }
    }
    
    private var historySection: some View {
        VStack(alignment: .leading, spacing: AppSpacing.md) {
            Text("Points History")
                .font(AppFonts.headline)
                .foregroundColor(AppColors.textPrimary)
            
            // Simple bar chart representation
            HStack(alignment: .bottom, spacing: 4) {
                ForEach(viewModel.historyPoints, id: \.self) { points in
                    RoundedRectangle(cornerRadius: 4)
                        .fill(AppColors.primary)
                        .frame(width: 30, height: CGFloat(points) / 10)
                }
            }
            .frame(height: 100)
            .padding(AppSpacing.md)
            .background(AppColors.card)
            .cornerRadius(AppCornerRadius.medium)
            
            // Week labels
            HStack {
                ForEach(Array(viewModel.historyWeeks.enumerated()), id: \.offset) { index, week in
                    if index % 2 == 0 {
                        Text(week)
                            .font(AppFonts.small)
                            .foregroundColor(AppColors.textMuted)
                            .frame(maxWidth: .infinity)
                    }
                }
            }
        }
    }
}

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
                .font(AppFonts.title)
                .fontWeight(.bold)
                .foregroundColor(AppColors.textPrimary)
            
            Text(title)
                .font(AppFonts.caption)
                .foregroundColor(AppColors.textSecondary)
        }
        .frame(maxWidth: .infinity)
        .padding(AppSpacing.lg)
        .background(AppColors.card)
        .cornerRadius(AppCornerRadius.medium)
    }
}

struct PointsBar: View {
    let label: String
    let points: Int
    let total: Int
    let color: Color
    
    var body: some View {
        VStack(alignment: .leading, spacing: AppSpacing.xs) {
            HStack {
                Text(label)
                    .font(AppFonts.caption)
                    .foregroundColor(AppColors.textSecondary)
                
                Spacer()
                
                Text("\(points) pts")
                    .font(AppFonts.caption)
                    .fontWeight(.semibold)
                    .foregroundColor(AppColors.textPrimary)
            }
            
            GeometryReader { geometry in
                ZStack(alignment: .leading) {
                    RoundedRectangle(cornerRadius: 4)
                        .fill(AppColors.surface)
                        .frame(height: 8)
                    
                    RoundedRectangle(cornerRadius: 4)
                        .fill(color)
                        .frame(width: geometry.size.width * CGFloat(points) / CGFloat(max(total, 1)), height: 8)
                }
            }
            .frame(height: 8)
        }
    }
}

struct CategoryCard: View {
    let title: String
    let value: String
    let icon: String
    let color: Color
    
    var body: some View {
        VStack(spacing: AppSpacing.sm) {
            Image(systemName: icon)
                .font(.system(size: 20))
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

// MARK: - View Model
@MainActor
class StatsDetailViewModel: ObservableObject {
    @Published var totalPoints = 12450
    @Published var weeklyPoints = 1245
    @Published var battingPoints = 5602
    @Published var bowlingPoints = 3112
    @Published var fieldingPoints = 1868
    @Published var milestonePoints = 1245
    @Published var categoryWins = 485
    @Published var categoryLosses = 412
    @Published var categoryTies = 23
    @Published var winRate = 54
    @Published var historyPoints = [1200, 980, 1150, 1320, 1080, 1245]
    @Published var historyWeeks = ["W1", "W2", "W3", "W4", "W5", "W6"]
}
