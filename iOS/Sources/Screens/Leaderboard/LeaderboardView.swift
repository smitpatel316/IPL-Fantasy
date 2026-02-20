import SwiftUI

// MARK: - Leaderboard View
struct LeaderboardView: View {
    @StateObject private var viewModel = LeaderboardViewModel()
    @State private var selectedFilter: LeaderboardFilter = .global
    
    var body: some View {
        NavigationStack {
            ZStack {
                AppColors.background
                    .ignoresSafeArea()
                
                VStack(spacing: 0) {
                    // Filter Picker
                    filterPicker
                    
                    // Top 3 Podium
                    if selectedFilter == .global {
                        podiumSection
                    }
                    
                    // Leaderboard List
                    leaderboardList
                }
            }
            .navigationTitle("Leaderboard")
            .navigationBarTitleDisplayMode(.large)
        }
    }
    
    private var filterPicker: some View {
        Picker("Filter", selection: $selectedFilter) {
            ForEach(LeaderboardFilter.allCases, id: \.self) { filter in
                Text(filter.rawValue).tag(filter)
            }
        }
        .pickerStyle(SegmentedPickerStyle())
        .padding(AppSpacing.md)
        .background(AppColors.card)
    }
    
    private var podiumSection: some View {
        HStack(alignment: .bottom, spacing: AppSpacing.md) {
            // 2nd Place
            if viewModel.leaderboard.count > 1 {
                PodiumCard(rank: 2, team: viewModel.leaderboard[1], height: 100)
            }
            
            // 1st Place
            if !viewModel.leaderboard.isEmpty {
                PodiumCard(rank: 1, team: viewModel.leaderboard[0], height: 130)
            }
            
            // 3rd Place
            if viewModel.leaderboard.count > 2 {
                PodiumCard(rank: 3, team: viewModel.leaderboard[2], height: 80)
            }
        }
        .padding(AppSpacing.lg)
        .background(AppColors.surface)
    }
    
    private var leaderboardList: some View {
        ScrollView {
            LazyVStack(spacing: AppSpacing.sm) {
                ForEach(viewModel.leaderboard) { team in
                    LeaderboardRow(team: team)
                }
            }
            .padding(AppSpacing.md)
        }
    }
}

struct PodiumCard: View {
    let rank: Int
    let team: LeaderboardTeam
    let height: CGFloat
    
    var body: some View {
        VStack(spacing: AppSpacing.sm) {
            // Avatar
            ZStack {
                Circle()
                    .fill(rankColor.opacity(0.3))
                    .frame(width: 50, height: 50)
                
                Text(team.name.prefix(1))
                    .font(AppFonts.title)
                    .fontWeight(.bold)
                    .foregroundColor(rankColor)
            }
            
            // Rank
            Text("#\(rank)")
                .font(AppFonts.headline)
                .fontWeight(.bold)
                .foregroundColor(rankColor)
            
            // Name
            Text(team.name)
                .font(AppFonts.caption)
                .fontWeight(.semibold)
                .foregroundColor(AppColors.textPrimary)
                .lineLimit(1)
            
            // Points
            Text("\(team.points)")
                .font(AppFonts.subheadline)
                .fontWeight(.bold)
                .foregroundColor(AppColors.textPrimary)
        }
        .frame(width: 80, height: height + 80)
        .background(AppColors.card)
        .cornerRadius(AppCornerRadius.medium)
    }
    
    private var rankColor: Color {
        switch rank {
        case 1: return .yellow
        case 2: return .gray
        case 3: return .orange
        default: return AppColors.textMuted
        }
    }
}

struct LeaderboardRow: View {
    let team: LeaderboardTeam
    
    var body: some View {
        HStack(spacing: AppSpacing.md) {
            // Rank
            Text("#\(team.rank)")
                .font(AppFonts.subheadline)
                .fontWeight(.bold)
                .foregroundColor(team.rank <= 3 ? AppColors.primary : AppColors.textMuted)
                .frame(width: 40)
            
            // Avatar
            Circle()
                .fill(AppColors.primary.opacity(0.3))
                .frame(width: 40, height: 40)
                .overlay(
                    Text(team.name.prefix(1))
                        .font(AppFonts.subheadline)
                        .fontWeight(.bold)
                        .foregroundColor(AppColors.primary)
                )
            
            // Info
            VStack(alignment: .leading, spacing: AppSpacing.xs) {
                Text(team.name)
                    .font(AppFonts.subheadline)
                    .fontWeight(.semibold)
                    .foregroundColor(AppColors.textPrimary)
                
                Text("\(team.leagueName)")
                    .font(AppFonts.caption)
                    .foregroundColor(AppColors.textMuted)
            }
            
            Spacer()
            
            // Points
            VStack(alignment: .trailing, spacing: AppSpacing.xs) {
                Text("\(team.points)")
                    .font(AppFonts.subheadline)
                    .fontWeight(.bold)
                    .foregroundColor(AppColors.textPrimary)
                
                if team.rankChange != 0 {
                    HStack(spacing: 2) {
                        Image(systemName: team.rankChange > 0 ? "arrow.up" : "arrow.down")
                            .font(.system(size: 10))
                        Text("\(abs(team.rankChange))")
                            .font(AppFonts.small)
                    }
                    .foregroundColor(team.rankChange > 0 ? AppColors.success : AppColors.error)
                }
            }
        }
        .padding(AppSpacing.md)
        .background(AppColors.card)
        .cornerRadius(AppCornerRadius.medium)
    }
}

// MARK: - View Model
@MainActor
class LeaderboardViewModel: ObservableObject {
    @Published var leaderboard: [LeaderboardTeam] = []
    
    init() {
        loadMockData()
    }
    
    private func loadMockData() {
        leaderboard = [
            LeaderboardTeam(id: "1", name: "KingKohli", points: 15420, rank: 1, rankChange: 0, leagueName: "Global"),
            LeaderboardTeam(id: "2", name: "BCCI_PRO", points: 15380, rank: 2, rankChange: 2, leagueName: "Global"),
            LeaderboardTeam(id: "3", name: "SixerKing", points: 15245, rank: 3, rankChange: -1, leagueName: "Global"),
            LeaderboardTeam(id: "4", name: "FantasyAI", points: 15120, rank: 4, rankChange: 5, leagueName: "Global"),
            LeaderboardTeam(id: "5", name: "IPLFan2026", points: 15098, rank: 5, rankChange: 0, leagueName: "Global"),
            LeaderboardTeam(id: "6", name: "CricketLord", points: 14950, rank: 6, rankChange: 3, leagueName: "Global"),
            LeaderboardTeam(id: "7", name: "T20Expert", points: 14820, rank: 7, rankChange: -2, leagueName: "Global"),
            LeaderboardTeam(id: "8", name: "MatchWinner", points: 14700, rank: 8, rankChange: 1, leagueName: "Global"),
        ]
    }
}

struct LeaderboardTeam: Identifiable {
    let id: String
    let name: String
    let points: Int
    var rank: Int
    var rankChange: Int
    let leagueName: String
}

enum LeaderboardFilter: String, CaseIterable {
    case global = "Global"
    case friends = "Friends"
    case league = "My League"
    case thisWeek = "This Week"
}
