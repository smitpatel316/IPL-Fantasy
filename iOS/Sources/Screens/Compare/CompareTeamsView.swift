import SwiftUI

// MARK: - Compare Teams View
struct CompareTeamsView: View {
    @StateObject private var viewModel = CompareTeamsViewModel()
    @Environment(\.dismiss) var dismiss
    
    var body: some View {
        NavigationStack {
            ZStack {
                AppColors.background
                    .ignoresSafeArea()
                
                VStack(spacing: 0) {
                    // Team Selectors
                    teamSelectors
                    
                    // Comparison
                    if let team1 = viewModel.selectedTeam1, let team2 = viewModel.selectedTeam2 {
                        comparisonView(team1: team1, team2: team2)
                    } else {
                        emptyState
                    }
                }
            }
            .navigationTitle("Compare Teams")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .navigationBarLeading) {
                    Button("Close") { dismiss() }
                        .foregroundColor(AppColors.primary)
                }
            }
        }
    }
    
    private var teamSelectors: some View {
        HStack(spacing: AppSpacing.md) {
            // Team 1
            Menu {
                ForEach(viewModel.allTeams) { team in
                    Button(action: { viewModel.selectedTeam1 = team }) {
                        Text(team.name)
                    }
                }
            } label: {
                HStack {
                    Text(viewModel.selectedTeam1?.name ?? "Select Team")
                        .font(AppFonts.subheadline)
                        .foregroundColor(AppColors.textPrimary)
                    Spacer()
                    Image(systemName: "chevron.down")
                        .foregroundColor(AppColors.textMuted)
                }
                .padding(AppSpacing.md)
                .background(AppColors.surface)
                .cornerRadius(AppCornerRadius.small)
            }
            
            // VS
            Text("VS")
                .font(AppFonts.headline)
                .fontWeight(.bold)
                .foregroundColor(AppColors.textMuted)
            
            // Team 2
            Menu {
                ForEach(viewModel.allTeams) { team in
                    Button(action: { viewModel.selectedTeam2 = team }) {
                        Text(team.name)
                    }
                }
            } label: {
                HStack {
                    Text(viewModel.selectedTeam2?.name ?? "Select Team")
                        .font(AppFonts.subheadline)
                        .foregroundColor(AppColors.textPrimary)
                    Spacer()
                    Image(systemName: "chevron.down")
                        .foregroundColor(AppColors.textMuted)
                }
                .padding(AppSpacing.md)
                .background(AppColors.surface)
                .cornerRadius(AppCornerRadius.small)
            }
        }
        .padding(AppSpacing.md)
        .background(AppColors.card)
    }
    
    private func comparisonView(team1: TeamComparison, team2: TeamComparison) -> some View {
        ScrollView {
            VStack(spacing: AppSpacing.md) {
                // Header - Team names and win prediction
                HStack {
                    VStack {
                        Text(team1.name)
                            .font(AppFonts.headline)
                            .fontWeight(.bold)
                            .foregroundColor(AppColors.textPrimary)
                        Text("\(team1.totalPoints) pts")
                            .font(AppFonts.subheadline)
                            .foregroundColor(AppColors.success)
                    }
                    .frame(maxWidth: .infinity)
                    
                    VStack {
                        Text("Prediction")
                            .font(AppFonts.caption)
                            .foregroundColor(AppColors.textMuted)
                        Text("\(viewModel.winProbability)%")
                            .font(AppFonts.title)
                            .fontWeight(.bold)
                            .foregroundColor(AppColors.accent)
                    }
                    
                    VStack {
                        Text(team2.name)
                            .font(AppFonts.headline)
                            .fontWeight(.bold)
                            .foregroundColor(AppColors.textPrimary)
                        Text("\(team2.totalPoints) pts")
                            .font(AppFonts.subheadline)
                            .foregroundColor(AppColors.success)
                    }
                    .frame(maxWidth: .infinity)
                }
                .padding(AppSpacing.md)
                
                // Category Comparison
                VStack(spacing: AppSpacing.sm) {
                    ComparisonRow(category: "Total Points", value1: team1.totalPoints, value2: team2.totalPoints, higher1: team1.totalPoints > team2.totalPoints)
                    ComparisonRow(category: "Batsmen", value1: team1.battingPoints, value2: team2.battingPoints, higher1: team1.battingPoints > team2.battingPoints)
                    ComparisonRow(category: "Bowlers", value1: team1.bowlingPoints, value2: team2.bowlingPoints, higher1: team1.bowlingPoints > team2.bowlingPoints)
                    ComparisonRow(category: "All-Rounders", value1: team1.allrounderPoints, value2: team2.allrounderPoints, higher1: team1.allrounderPoints > team2.allrounderPoints)
                    ComparisonRow(category: "Star Players", value1: team1.starCount, value2: team2.starCount, higher1: team1.starCount > team2.starCount, isInteger: true)
                    ComparisonRow(category: "Budget Remaining", value1: team1.budgetRemaining, value2: team2.budgetRemaining, higher1: team1.budgetRemaining > team2.budgetRemaining)
                }
                .padding(AppSpacing.md)
                .background(AppColors.card)
                .cornerRadius(AppCornerRadius.medium)
                
                // Key Players Comparison
                VStack(alignment: .leading, spacing: AppSpacing.md) {
                    Text("Key Players")
                        .font(AppFonts.headline)
                        .foregroundColor(AppColors.textPrimary)
                    
                    HStack(spacing: AppSpacing.md) {
                        VStack(alignment: .leading, spacing: AppSpacing.xs) {
                            ForEach(team1.topPlayers.prefix(3)) { player in
                                Text("• \(player.name)")
                                    .font(AppFonts.caption)
                                    .foregroundColor(AppColors.textSecondary)
                            }
                        }
                        
                        Spacer()
                        
                        VStack(alignment: .trailing, spacing: AppSpacing.xs) {
                            ForEach(team2.topPlayers.prefix(3)) { player in
                                Text("• \(player.name)")
                                    .font(AppFonts.caption)
                                    .foregroundColor(AppColors.textSecondary)
                            }
                        }
                    }
                }
                .padding(AppSpacing.md)
                .background(AppColors.card)
                .cornerRadius(AppCornerRadius.medium)
            }
            .padding(AppSpacing.md)
        }
    }
    
    private var emptyState: some View {
        VStack(spacing: AppSpacing.md) {
            Image(systemName: "arrow.left.arrow.right")
                .font(.system(size: 48))
                .foregroundColor(AppColors.textMuted)
            
            Text("Select two teams to compare")
                .font(AppFonts.body)
                .foregroundColor(AppColors.textSecondary)
        }
        .frame(maxHeight: .infinity)
    }
}

// MARK: - Comparison Row
struct ComparisonRow: View {
    let category: String
    let value1: Int
    let value2: Int
    let higher1: Bool
    var isInteger: Bool = false
    
    var body: some View {
        HStack {
            Text("\(value1)")
                .font(AppFonts.subheadline)
                .fontWeight(.bold)
                .foregroundColor(higher1 ? AppColors.success : AppColors.textSecondary)
                .frame(maxWidth: .infinity, alignment: .leading)
            
            VStack(spacing: 2) {
                Text(category)
                    .font(AppFonts.caption)
                    .foregroundColor(AppColors.textMuted)
                Image(systemName: higher1 ? "chevron.left" : "chevron.right")
                    .font(.system(size: 10))
                    .foregroundColor(AppColors.textMuted)
            }
            
            Text("\(value2)")
                .font(AppFonts.subheadline)
                .fontWeight(.bold)
                .foregroundColor(!higher1 ? AppColors.success : AppColors.textSecondary)
                .frame(maxWidth: .infinity, alignment: .trailing)
        }
        .padding(.vertical, AppSpacing.xs)
    }
}

// MARK: - Compare Teams View Model
@MainActor
class CompareTeamsViewModel: ObservableObject {
    @Published var allTeams: [TeamComparison] = []
    @Published var selectedTeam1: TeamComparison?
    @Published var selectedTeam2: TeamComparison?
    @Published var winProbability: Int = 50
    
    init() {
        loadMockTeams()
    }
    
    private func loadMockTeams() {
        allTeams = [
            TeamComparison(id: "1", name: "Team Fire", totalPoints: 1245, battingPoints: 560, bowlingPoints: 320, allrounderPoints: 280, starCount: 3, budgetRemaining: 7, topPlayers: [
                Player(name: "Jasprit Bumrah", points: 156),
                Player(name: "Virat Kohli", points: 145),
                Player(name: "Andre Russell", points: 132)
            ]),
            TeamComparison(id: "2", name: "Team Bolt", totalPoints: 1198, battingPoints: 520, bowlingPoints: 380, allrounderPoints: 240, starCount: 2, budgetRemaining: 12, topPlayers: [
                Player(name: "Rashid Khan", points: 148),
                Player(name: "KL Rahul", points: 138),
                Player(name: "Mohammed Shami", points: 125)
            ]),
            TeamComparison(id: "3", name: "Team Star", totalPoints: 1156, battingPoints: 480, bowlingPoints: 350, allrounderPoints: 290, starCount: 2, budgetRemaining: 5, topPlayers: [
                Player(name: "Rohit Sharma", points: 142),
                Player(name: "Hardik Pandya", points: 128),
                Player(name: "Ravindra Jadeja", points: 118)
            ]),
        ]
        
        selectedTeam1 = allTeams[0]
        selectedTeam2 = allTeams[1]
        calculateProbability()
    }
    
    private func calculateProbability() {
        guard let t1 = selectedTeam1, let t2 = selectedTeam2 else {
            winProbability = 50
            return
        }
        
        let total = t1.totalPoints + t2.totalPoints
        winProbability = Int((Double(t1.totalPoints) / Double(total)) * 100)
    }
}

struct TeamComparison: Identifiable {
    let id: String
    let name: String
    let totalPoints: Int
    let battingPoints: Int
    let bowlingPoints: Int
    let allrounderPoints: Int
    let starCount: Int
    let budgetRemaining: Int
    let topPlayers: [Player]
}

struct Player {
    let name: String
    let points: Int
}
