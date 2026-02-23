import SwiftUI

// MARK: - User League (for list display)
struct UserLeague: Identifiable {
    let id: String
    var name: String
    var code: String
    var status: League.LeagueStatus
    var membersCount: Int
    
    init(id: String, name: String, code: String, status: League.LeagueStatus, membersCount: Int) {
        self.id = id
        self.name = name
        self.code = code
        self.status = status
        self.membersCount = membersCount
    }
}

// MARK: - League Auto-Pick List View
struct LeagueAutoPickListView: View {
    @StateObject private var viewModel = LeagueListViewModel()
    var onSelectLeague: (String, String) -> Void
    
    var body: some View {
        ZStack {
            AppColors.background
                .ignoresSafeArea()
            
            if viewModel.isLoading {
                ProgressView()
                    .frame(maxWidth: .infinity, maxHeight: .infinity)
            } else if viewModel.leagues.isEmpty {
                emptyState
            } else {
                leagueList
            }
        }
        .navigationTitle("Select League")
        .navigationBarTitleDisplayMode(.inline)
        .task {
            await viewModel.loadLeagues()
        }
    }
    
    private var emptyState: some View {
        VStack(spacing: AppSpacing.lg) {
            Image(systemName: "trophy")
                .font(.system(size: 50))
                .foregroundColor(AppColors.textMuted)
            
            Text("No Leagues")
                .font(AppFonts.headline)
                .foregroundColor(AppColors.textPrimary)
            
            Text("Join or create a league to configure auto-pick settings")
                .font(AppFonts.body)
                .foregroundColor(AppColors.textSecondary)
                .multilineTextAlignment(.center)
        }
        .padding(AppSpacing.xl)
    }
    
    private var leagueList: some View {
        ScrollView {
            VStack(spacing: AppSpacing.sm) {
                ForEach(viewModel.leagues) { league in
                    NavigationLink {
                        AutoPickSettingsView(
                            leagueId: league.id,
                            leagueName: league.name
                        )
                    } label: {
                        LeagueRow(league: league)
                    }
                }
            }
            .padding(AppSpacing.md)
        }
    }
}

struct LeagueRow: View {
    let league: UserLeague
    
    var body: some View {
        HStack(spacing: AppSpacing.md) {
            // League Icon
            ZStack {
                Circle()
                    .fill(AppColors.primary.opacity(0.2))
                    .frame(width: 44, height: 44)
                
                Text(String(league.name.prefix(1)).uppercased())
                    .font(AppFonts.headline)
                    .fontWeight(.bold)
                    .foregroundColor(AppColors.primary)
            }
            
            // League Info
            VStack(alignment: .leading, spacing: 2) {
                Text(league.name)
                    .font(AppFonts.subheadline)
                    .fontWeight(.semibold)
                    .foregroundColor(AppColors.textPrimary)
                
                Text("\(league.membersCount) teams")
                    .font(AppFonts.caption)
                    .foregroundColor(AppColors.textSecondary)
            }
            
            Spacer()
            
            Image(systemName: "chevron.right")
                .font(.system(size: 14, weight: .semibold))
                .foregroundColor(AppColors.textMuted)
        }
        .padding(AppSpacing.md)
        .background(AppColors.card)
        .cornerRadius(AppCornerRadius.medium)
    }
}

// MARK: - Mock League List ViewModel

@MainActor
class LeagueListViewModel: ObservableObject {
    @Published var leagues: [UserLeague] = []
    @Published var isLoading = false
    
    func loadLeagues() async {
        isLoading = true
        
        // In production, would fetch from API
        // For now, use mock data
        try? await Task.sleep(nanoseconds: 500_000_000)
        
        leagues = [
            UserLeague(id: "l1", name: "IPL Champions 2026", code: "CHAMP", maxTeams: 10, status: .open, membersCount: 8),
            UserLeague(id: "l2", name: "Sunday League", code: "SUN", maxTeams: 12, status: .active, membersCount: 10),
            UserLeague(id: "l3", name: "Workplace Fantasy", code: "WORK", maxTeams: 8, status: .drafting, membersCount: 6),
        ]
        
        isLoading = false
    }
}

#Preview {
    NavigationStack {
        LeagueAutoPickListView { _, _ in }
    }
}
