import SwiftUI

// MARK: - Standings View
struct StandingsView: View {
    @StateObject private var viewModel = StandingsViewModel()
    
    var body: some View {
        NavigationStack {
            ZStack {
                AppColors.background
                    .ignoresSafeArea()
                
                VStack(spacing: 0) {
                    // Week Selector
                    weekSelector
                    
                    // Standings Table
                    standingsTable
                }
            }
            .navigationTitle("Standings")
            .navigationBarTitleDisplayMode(.large)
        }
    }
    
    private var weekSelector: some View {
        ScrollView(.horizontal, showsIndicators: false) {
            HStack(spacing: AppSpacing.sm) {
                ForEach(1...14, id: \.self) { week in
                    Button(action: { viewModel.selectedWeek = week }) {
                        Text("W\(week)")
                            .font(AppFonts.caption)
                            .fontWeight(viewModel.selectedWeek == week ? .bold : .regular)
                            .foregroundColor(viewModel.selectedWeek == week ? .white : AppColors.textPrimary)
                            .padding(.horizontal, AppSpacing.md)
                            .padding(.vertical, AppSpacing.sm)
                            .background(viewModel.selectedWeek == week ? AppColors.primary : AppColors.card)
                            .cornerRadius(AppCornerRadius.small)
                    }
                }
            }
            .padding(AppSpacing.md)
        }
        .background(AppColors.card)
    }
    
    private var standingsTable: some View {
        ScrollView {
            LazyVStack(spacing: AppSpacing.sm) {
                // Header
                HStack {
                    Text("#")
                        .font(AppFonts.caption)
                        .fontWeight(.bold)
                        .foregroundColor(AppColors.textMuted)
                        .frame(width: 30)
                    
                    Text("Team")
                        .font(AppFonts.caption)
                        .fontWeight(.bold)
                        .foregroundColor(AppColors.textMuted)
                        .frame(maxWidth: .infinity, alignment: .leading)
                    
                    Text("W-L-T")
                        .font(AppFonts.caption)
                        .fontWeight(.bold)
                        .foregroundColor(AppColors.textMuted)
                        .frame(width: 60)
                    
                    Text("Pts")
                        .font(AppFonts.caption)
                        .fontWeight(.bold)
                        .foregroundColor(AppColors.textMuted)
                        .frame(width: 40)
                    
                    Text("Categories")
                        .font(AppFonts.caption)
                        .fontWeight(.bold)
                        .foregroundColor(AppColors.textMuted)
                        .frame(width: 80)
                }
                .padding(.horizontal, AppSpacing.md)
                .padding(.vertical, AppSpacing.sm)
                
                Divider()
                
                // Rows
                ForEach(viewModel.standings) { team in
                    StandingRow(team: team, rank: viewModel.standings.firstIndex(where: { $0.id == team.id })! + 1)
                }
            }
            .padding(AppSpacing.md)
        }
    }
}

struct StandingRow: View {
    let team: StandingTeam
    let rank: Int
    
    var body: some View {
        HStack {
            // Rank
            ZStack {
                if rank <= 4 {
                    Circle()
                        .fill(AppColors.success.opacity(0.2))
                        .frame(width: 30, height: 30)
                }
                Text("\(rank)")
                    .font(AppFonts.subheadline)
                    .fontWeight(rank <= 4 ? .bold : .regular)
                    .foregroundColor(rank <= 4 ? AppColors.success : AppColors.textSecondary)
            }
            
            // Team
            HStack(spacing: AppSpacing.sm) {
                Circle()
                    .fill(AppColors.primary.opacity(0.3))
                    .frame(width: 32, height: 32)
                    .overlay(
                        Text(String(team.name.prefix(1)))
                            .font(AppFonts.caption)
                            .fontWeight(.bold)
                            .foregroundColor(AppColors.textPrimary)
                    )
                
                Text(team.name)
                    .font(AppFonts.subheadline)
                    .fontWeight(.semibold)
                    .foregroundColor(AppColors.textPrimary)
            }
            .frame(maxWidth: .infinity, alignment: .leading)
            
            // W-L-T
            Text("\(team.wins)-\(team.losses)-\(team.ties)")
                .font(AppFonts.caption)
                .foregroundColor(AppColors.textSecondary)
                .frame(width: 60)
            
            // Points
            Text("\(team.points)")
                .font(AppFonts.subheadline)
                .fontWeight(.bold)
                .foregroundColor(AppColors.textPrimary)
                .frame(width: 40)
            
            // Categories
            HStack(spacing: 2) {
                Text("\(team.categoriesWon)")
                    .font(AppFonts.caption)
                    .foregroundColor(AppColors.success)
                Text("-")
                    .font(AppFonts.caption)
                    .foregroundColor(AppColors.textMuted)
                Text("\(team.categoriesLost)")
                    .font(AppFonts.caption)
                    .foregroundColor(AppColors.error)
            }
            .frame(width: 80)
        }
        .padding(.horizontal, AppSpacing.md)
        .padding(.vertical, AppSpacing.sm)
        .background(rank % 2 == 0 ? AppColors.card.opacity(0.5) : AppColors.card)
        .cornerRadius(AppCornerRadius.small)
    }
}

// MARK: - Standings View Model
@MainActor
class StandingsViewModel: ObservableObject {
    @Published var selectedWeek = 1
    @Published var standings: [StandingTeam] = []
    
    init() {
        loadMockStandings()
    }
    
    func loadMockStandings() {
        standings = [
            StandingTeam(id: "1", name: "Team Fire", wins: 12, losses: 2, ties: 1, points: 25, categoriesWon: 98, categoriesLost: 42),
            StandingTeam(id: "2", name: "Team Bolt", wins: 11, losses: 3, ties: 1, points: 23, categoriesWon: 95, categoriesLost: 45),
            StandingTeam(id: "3", name: "Team Star", wins: 10, losses: 4, ties: 1, points: 21, categoriesWon: 88, categoriesLost: 52),
            StandingTeam(id: "4", name: "Team Crown", wins: 9, losses: 5, ties: 1, points: 19, categoriesWon: 82, categoriesLost: 58),
            StandingTeam(id: "5", name: "Team Rocket", wins: 8, losses: 6, ties: 1, points: 17, categoriesWon: 75, categoriesLost: 65),
            StandingTeam(id: "6", name: "Team Wave", wins: 7, losses: 7, ties: 1, points: 15, categoriesWon: 68, categoriesLost: 72),
            StandingTeam(id: "7", name: "Team Storm", wins: 6, losses: 8, ties: 1, points: 13, categoriesWon: 62, categoriesLost: 78),
            StandingTeam(id: "8", name: "Team Frost", wins: 5, losses: 9, ties: 1, points: 11, categoriesWon: 55, categoriesLost: 85),
            StandingTeam(id: "9", name: "Team Shadow", wins: 3, losses: 11, ties: 1, points: 7, categoriesWon: 42, categoriesLost: 98),
            StandingTeam(id: "10", name: "Team Mist", wins: 2, losses: 12, ties: 1, points: 5, categoriesWon: 35, categoriesLost: 105),
        ]
    }
}

struct StandingTeam: Identifiable {
    let id: String
    let name: String
    let wins: Int
    let losses: Int
    let ties: Int
    let points: Int
    let categoriesWon: Int
    let categoriesLost: Int
}
