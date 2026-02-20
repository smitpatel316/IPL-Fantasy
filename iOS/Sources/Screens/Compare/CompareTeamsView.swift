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
                
                ScrollView {
                    VStack(spacing: AppSpacing.lg) {
                        // Team Selectors
                        teamSelectors
                        
                        // Comparison Stats
                        if let team1 = viewModel.selectedTeam1, let team2 = viewModel.selectedTeam2 {
                            comparisonCard(team1: team1, team2: team2)
                        }
                    }
                    .padding(AppSpacing.md)
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
            VStack(alignment: .leading, spacing: AppSpacing.sm) {
                Text("Team 1")
                    .font(AppFonts.caption)
                    .foregroundColor(AppColors.textSecondary)
                
                Menu {
                    ForEach(viewModel.allTeams) { team in
                        Button(team.name) {
                            viewModel.selectedTeam1 = team
                        }
                    }
                } label: {
                    HStack {
                        Text(viewModel.selectedTeam1?.name ?? "Select")
                            .font(AppFonts.subheadline)
                            .foregroundColor(AppColors.textPrimary)
                        Spacer()
                        Image(systemName: "chevron.down")
                            .font(.system(size: 12))
                            .foregroundColor(AppColors.textMuted)
                    }
                    .padding(AppSpacing.md)
                    .background(AppColors.surface)
                    .cornerRadius(AppCornerRadius.small)
                }
            }
            
            // VS
            Text("VS")
                .font(AppFonts.headline)
                .fontWeight(.bold)
                .foregroundColor(AppColors.textMuted)
                .padding(.top, AppSpacing.lg)
            
            // Team 2
            VStack(alignment: .leading, spacing: AppSpacing.sm) {
                Text("Team 2")
                    .font(AppFonts.caption)
                    .foregroundColor(AppColors.textSecondary)
                
                Menu {
                    ForEach(viewModel.allTeams) { team in
                        Button(team.name) {
                            viewModel.selectedTeam2 = team
                        }
                    }
                } label: {
                    HStack {
                        Text(viewModel.selectedTeam2?.name ?? "Select")
                            .font(AppFonts.subheadline)
                            .foregroundColor(AppColors.textPrimary)
                        Spacer()
                        Image(systemName: "chevron.down")
                            .font(.system(size: 12))
                            .foregroundColor(AppColors.textMuted)
                    }
                    .padding(AppSpacing.md)
                    .background(AppColors.surface)
                    .cornerRadius(AppCornerRadius.small)
                }
            }
        }
        .padding(AppSpacing.md)
        .background(AppColors.card)
        .cornerRadius(AppCornerRadius.medium)
    }
    
    private func comparisonCard(team1: TeamComparison, team2: TeamComparison) -> some View {
        VStack(spacing: AppSpacing.md) {
            // Header
            HStack {
                VStack {
                    Text(team1.name)
                        .font(AppFonts.subheadline)
                        .fontWeight(.bold)
                        .foregroundColor(AppColors.textPrimary)
                    Text("\(team1.totalPoints) pts")
                        .font(AppFonts.headline)
                        .foregroundColor(AppColors.primary)
                }
                .frame(maxWidth: .infinity)
                
                Text("vs")
                    .font(AppFonts.caption)
                    .foregroundColor(AppColors.textMuted)
                
                VStack {
                    Text(team2.name)
                        .font(AppFonts.subheadline)
                        .fontWeight(.bold)
                        .foregroundColor(AppColors.textPrimary)
                    Text("\(team2.totalPoints) pts")
                        .font(AppFonts.headline)
                        .foregroundColor(AppColors.accent)
                }
                .frame(maxWidth: .infinity)
            }
            
            Divider().background(AppColors.textMuted.opacity(0.3))
            
            // Categories
            VStack(spacing: AppSpacing.sm) {
                ComparisonRow(
                    label: "Total Points",
                    value1: team1.totalPoints,
                    value2: team2.totalPoints,
                    higherIsBetter: true
                )
                
                ComparisonRow(
                    label: "Batsmen Avg",
                    value1: team1.batsmenAvg,
                    value2: team2.batsmenAvg,
                    higherIsBetter: true
                )
                
                ComparisonRow(
                    label: "Bowlers Avg",
                    value1: team1.bowlersAvg,
                    value2: team2.bowlersAvg,
                    higherIsBetter: true
                )
                
                ComparisonRow(
                    label: "Overseas Players",
                    value1: team1.overseasCount,
                    value2: team2.overseasCount,
                    higherIsBetter: true
                )
                
                ComparisonRow(
                    label: "Star Power",
                    value1: team1.starPlayers,
                    value2: team2.starPlayers,
                    higherIsBetter: true
                )
                
                ComparisonRow(
                    label: "Budget Remaining",
                    value1: Int(team1.budgetRemaining),
                    value2: Int(team2.budgetRemaining),
                    higherIsBetter: true
                )
            }
            
            // Winner
            let.totalPoints > team winner = team12.totalPoints ? team1.name : team2.name
            let diff = abs(team1.totalPoints - team2.totalPoints)
            
            HStack {
                Image(systemName: "trophy.fill")
                    .foregroundColor(.yellow)
                Text("\(winner) leads by \(diff) points")
                    .font(AppFonts.subheadline)
                    .foregroundColor(AppColors.textPrimary)
            }
            .padding(.top, AppSpacing.sm)
        }
        .padding(AppSpacing.lg)
        .background(AppColors.card)
        .cornerRadius(AppCornerRadius.card)
    }
}

struct ComparisonRow: View {
    let label: String
    let value1: Int
    let value2: Int
    let higherIsBetter: Bool
    
    var body: some View {
        HStack {
            Text("\(value1)")
                .font(AppFonts.body)
                .fontWeight(.semibold)
                .foregroundColor(winner == 1 ? AppColors.success : AppColors.textPrimary)
                .frame(width: 60, alignment: .leading)
            
            Text(label)
                .font(AppFonts.caption)
                .foregroundColor(AppColors.textSecondary)
                .frame(maxWidth: .infinity)
            
            Text("\(value2)")
                .font(AppFonts.body)
                .fontWeight(.semibold)
                .foregroundColor(winner == 2 ? AppColors.success : AppColors.textPrimary)
                .frame(width: 60, alignment: .trailing)
        }
    }
    
    var winner: Int {
        if higherIsBetter {
            return value1 > value2 ? 1 : (value2 > value1 ? 2 : 0)
        } else {
            return value1 < value2 ? 1 : (value2 < value1 ? 2 : 0)
        }
    }
}

// MARK: - Compare Teams View Model
@MainActor
class CompareTeamsViewModel: ObservableObject {
    @Published var selectedTeam1: TeamComparison? = nil
    @Published var selectedTeam2: TeamComparison? = nil
    @Published var allTeams: [TeamComparison] = []
    
    init() {
        loadMockTeams()
        // Auto-select first two
        if allTeams.count >= 2 {
            selectedTeam1 = allTeams[0]
            selectedTeam2 = allTeams[1]
        }
    }
    
    private func loadMockTeams() {
        allTeams = [
            TeamComparison(id: "1", name: "Team Fire", totalPoints: 1245, batsmenAvg: 78, bowlersAvg: 52, overseasCount: 3, starPlayers: 4, budgetRemaining: 7.5),
            TeamComparison(id: "2", name: "Team Bolt", totalPoints: 1198, batsmenAvg: 72, bowlersAvg: 58, overseasCount: 4, starPlayers: 3, budgetRemaining: 5.0),
            TeamComparison(id: "3", name: "Team Star", totalPoints: 1156, batsmenAvg: 68, bowlersAvg: 62, overseasCount: 2, starPlayers: 5, budgetRemaining: 8.0),
            TeamComparison(id: "4", name: "Team Crown", totalPoints: 1089, batsmenAvg: 65, bowlersAvg: 55, overseasCount: 3, starPlayers: 2, budgetRemaining: 10.5),
            TeamComparison(id: "5", name: "Team Rocket", totalPoints: 1023, batsmenAvg: 58, bowlersAvg: 48, overseasCount: 4, starPlayers: 2, budgetRemaining: 12.0),
        ]
    }
}

struct TeamComparison: Identifiable {
    let id: String
    let name: String
    let totalPoints: Int
    let batsmenAvg: Int
    let bowlersAvg: Int
    let overseasCount: Int
    let starPlayers: Int
    let budgetRemaining: Double
}
