import SwiftUI
import WidgetKit

// MARK: - Live Scores View
struct LiveScoresView: View {
    @StateObject private var viewModel = LiveScoresViewModel()
    
    var body: some View {
        NavigationStack {
            ZStack {
                AppColors.background
                    .ignoresSafeArea()
                
                ScrollView {
                    VStack(spacing: AppSpacing.lg) {
                        // Live Now Section
                        if !viewModel.liveMatches.isEmpty {
                            liveMatchesSection
                        }
                        
                        // Upcoming Matches
                        upcomingSection
                        
                        // Completed
                        completedSection
                    }
                    .padding(AppSpacing.md)
                }
            }
            .navigationTitle("Live Scores")
            .navigationBarTitleDisplayMode(.large)
            .toolbar {
                ToolbarItem(placement: .navigationBarTrailing) {
                    Button(action: { viewModel.refresh() }) {
                        Image(systemName: "arrow.clockwise")
                            .foregroundColor(AppColors.primary)
                    }
                }
            }
            .onAppear {
                viewModel.startAutoRefresh()
            }
        }
    }
    
    private var liveMatchesSection: some View {
        VStack(alignment: .leading, spacing: AppSpacing.md) {
            HStack {
                HStack(spacing: AppSpacing.xs) {
                    Circle()
                        .fill(AppColors.error)
                        .frame(width: 8, height: 8)
                    Text("LIVE")
                        .font(AppFonts.caption)
                        .fontWeight(.bold)
                        .foregroundColor(AppColors.error)
                }
                
                Spacer()
                
                Text("\(viewModel.liveMatches.count) matches")
                    .font(AppFonts.caption)
                    .foregroundColor(AppColors.textMuted)
            }
            
            ForEach(viewModel.liveMatches) { match in
                LiveMatchCard(match: match)
            }
        }
    }
    
    private var upcomingSection: some View {
        VStack(alignment: .leading, spacing: AppSpacing.md) {
            Text("Upcoming")
                .font(AppFonts.headline)
                .foregroundColor(AppColors.textPrimary)
            
            ForEach(viewModel.upcomingMatches) { match in
                UpcomingMatchCard(match: match)
            }
        }
    }
    
    private var completedSection: some View {
        VStack(alignment: .leading, spacing: AppSpacing.md) {
            Text("Completed")
                .font(AppFonts.headline)
                .foregroundColor(AppColors.textPrimary)
            
            ForEach(viewModel.completedMatches) { match in
                CompletedMatchCard(match: match)
            }
        }
    }
}

// MARK: - Live Match Card
struct LiveMatchCard: View {
    let match: LiveMatch
    
    var body: some View {
        VStack(spacing: AppSpacing.md) {
            // Match Info
            HStack {
                Text(match.league)
                    .font(AppFonts.caption)
                    .foregroundColor(AppColors.textMuted)
                
                Spacer()
                
                Text(match.status)
                    .font(AppFonts.caption)
                    .fontWeight(.bold)
                    .foregroundColor(AppColors.error)
            }
            
            // Teams
            HStack {
                // Team 1
                VStack(spacing: AppSpacing.sm) {
                    TeamLogo(team: match.team1Abbr)
                    Text(match.team1Abbr)
                        .font(AppFonts.caption)
                        .fontWeight(.bold)
                        .foregroundColor(AppColors.textPrimary)
                    Text("\(match.team1Score)/\(match.team1Wickets)")
                        .font(AppFonts.headline)
                        .foregroundColor(AppColors.textPrimary)
                    Text("\(match.team1Overs) ov")
                        .font(AppFonts.caption)
                        .foregroundColor(AppColors.textMuted)
                }
                .frame(maxWidth: .infinity)
                
                // VS
                Text("vs")
                    .font(AppFonts.caption)
                    .foregroundColor(AppColors.textMuted)
                
                // Team 2
                VStack(spacing: AppSpacing.sm) {
                    TeamLogo(team: match.team2Abbr)
                    Text(match.team2Abbr)
                        .font(AppFonts.caption)
                        .fontWeight(.bold)
                        .foregroundColor(AppColors.textPrimary)
                    Text("\(match.team2Score)/\(match.team2Wickets)")
                        .font(AppFonts.headline)
                        .foregroundColor(AppColors.textPrimary)
                    Text("\(match.team2Overs) ov")
                        .font(AppFonts.caption)
                        .foregroundColor(AppColors.textMuted)
                }
                .frame(maxWidth: .infinity)
            }
            
            // Required Run Rate
            if match.requiredRunRate > 0 {
                HStack {
                    Text("Required RR:")
                        .font(AppFonts.caption)
                        .foregroundColor(AppColors.textMuted)
                    Text("\(String(format: "%.2f", match.requiredRunRate))")
                        .font(AppFonts.caption)
                        .fontWeight(.bold)
                        .foregroundColor(AppColors.warning                    Spacer()
)
                    
                    
                    Text("CRR:")
                        .font(AppFonts.caption)
                        .foregroundColor(AppColors.textMuted)
                    Text("\(String(format: "%.2f", match.currentRunRate))")
                        .font(AppFonts.caption)
                        .fontWeight(.bold)
                        .foregroundColor(AppColors.success)
                }
            }
            
            // Last Ball Commentary
            if !match.lastCommentary.isEmpty {
                Text(match.lastCommentary)
                    .font(AppFonts.caption)
                    .foregroundColor(AppColors.textSecondary)
                    .italic()
            }
        }
        .padding(AppSpacing.lg)
        .background(AppColors.card)
        .cornerRadius(AppCornerRadius.card)
    }
}

struct TeamLogo: View {
    let team: String
    
    var body: some View {
        ZStack {
            Circle()
                .fill(teamColor.opacity(0.2))
                .frame(width: 50, height: 50)
            
            Text(team.prefix(1))
                .font(AppFonts.title)
                .fontWeight(.bold)
                .foregroundColor(teamColor)
        }
    }
    
    private var teamColor: Color {
        switch team {
        case "MI": return .blue
        case "CSK": return .yellow
        case "RCB": return .red
        case "KKR": return .purple
        case "DC": return .blue
        case "GT": return .orange
        case "LSG": return .cyan
        case "RR": return .pink
        case "SRH": return .orange
        default: return .gray
        }
    }
}

struct UpcomingMatchCard: View {
    let match: LiveMatch
    
    var body: some View {
        HStack(spacing: AppSpacing.md) {
            TeamLogo(team: match.team1Abbr)
            TeamLogo(team: match.team2Abbr)
            
            VStack(alignment: .leading, spacing: AppSpacing.xs) {
                Text("\(match.team1Abbr) vs \(match.team2Abbr)")
                    .font(AppFonts.subheadline)
                    .fontWeight(.semibold)
                    .foregroundColor(AppColors.textPrimary)
                
                Text(match.startTime)
                    .font(AppFonts.caption)
                    .foregroundColor(AppColors.textMuted)
            }
            
            Spacer()
            
            Text(match.league)
                .font(AppFonts.caption)
                .foregroundColor(AppColors.primary)
        }
        .padding(AppSpacing.md)
        .background(AppColors.card)
        .cornerRadius(AppCornerRadius.medium)
    }
}

struct CompletedMatchCard: View {
    let match: LiveMatch
    
    var body: some View {
        HStack(spacing: AppSpacing.md) {
            VStack(alignment: .leading, spacing: AppSpacing.xs) {
                Text("\(match.team1Abbr) \(match.team1Score)/\(match.team1Wickets)")
                    .font(AppFonts.subheadline)
                    .foregroundColor(AppColors.textPrimary)
                
                Text("\(match.team2Abbr) \(match.team2Score)/\(match.team2Wickets)")
                    .font(AppFonts.subheadline)
                    .foregroundColor(AppColors.textPrimary)
            }
            
            Spacer()
            
            VStack(alignment: .trailing, spacing: AppSpacing.xs) {
                Text(match.winner.isEmpty ? "Tie" : match.winner)
                    .font(AppFonts.caption)
                    .fontWeight(.bold)
                    .foregroundColor(AppColors.success)
                
                Text(match.result)
                    .font(AppFonts.caption)
                    .foregroundColor(AppColors.textMuted)
            }
        }
        .padding(AppSpacing.md)
        .background(AppColors.card)
        .cornerRadius(AppCornerRadius.medium)
    }
}

// MARK: - Live Scores View Model
@MainActor
class LiveScoresViewModel: ObservableObject {
    @Published var liveMatches: [LiveMatch] = []
    @Published var upcomingMatches: [LiveMatch] = []
    @Published var completedMatches: [LiveMatch] = []
    
    private var timer: Timer?
    
    init() {
        loadMockData()
    }
    
    func startAutoRefresh() {
        timer?.invalidate()
        timer = Timer.scheduledTimer(withTimeInterval: 30, repeats: true) { [weak self] _ in
            Task { @MainActor in
                self?.refresh()
            }
        }
    }
    
    func stopAutoRefresh() {
        timer?.invalidate()
        timer = nil
    }
    
    func refresh() {
        // In production, would fetch from API
        loadMockData()
    }
    
    private func loadMockData() {
        liveMatches = [
            LiveMatch(
                id: "1",
                league: "IPL 2026",
                team1: "Mumbai Indians",
                team1Abbr: "MI",
                team1Score: 145,
                team1Wickets: 3,
                team1Overs: 14.2,
                team2: "Chennai Super Kings",
                team2Abbr: "CSK",
                team2Score: 0,
                team2Wickets: 0,
                team2Overs: 0,
                status: "In Progress",
                startTime: "",
                requiredRunRate: 8.5,
                currentRunRate: 10.1,
                lastCommentary: "Rohit hits a six! MI looking strong",
                winner: "",
                result: ""
            )
        ]
        
        upcomingMatches = [
            LiveMatch(
                id: "2",
                league: "IPL 2026",
                team1: "Royal Challengers Bangalore",
                team1Abbr: "RCB",
                team2: "Kolkata Knight Riders",
                team2Abbr: "KKR",
                status: "Today 7:30 PM",
                startTime: "Today, 7:30 PM",
                winner: "",
                result: ""
            ),
            LiveMatch(
                id: "3",
                league: "IPL 2026",
                team1: "Delhi Capitals",
                team1Abbr: "DC",
                team2: "Sunrisers Hyderabad",
                team2Abbr: "SRH",
                status: "Tomorrow 3:30 PM",
                startTime: "Tomorrow, 3:30 PM",
                winner: "",
                result: ""
            )
        ]
        
        completedMatches = [
            LiveMatch(
                id: "4",
                league: "IPL 2026",
                team1: "Gujarat Titans",
                team1Abbr: "GT",
                team1Score: 180,
                team1Wickets: 6,
                team1Overs: 20,
                team2: "Rajasthan Royals",
                team2Abbr: "RR",
                team2Score: 175,
                team2Wickets: 8,
                team2Overs: 19.5,
                status: "Completed",
                startTime: "",
                winner: "GT",
                result: "GT won by 5 runs"
            )
        ]
    }
}

struct LiveMatch: Identifiable {
    let id: String
    let league: String
    let team1: String
    let team1Abbr: String
    var team1Score: Int
    var team1Wickets: Int
    var team1Overs: Double
    let team2: String
    let team2Abbr: String
    var team2Score: Int
    var team2Wickets: Int
    var team2Overs: Double
    let status: String
    let startTime: String
    var requiredRunRate: Double = 0
    var currentRunRate: Double = 0
    let lastCommentary: String
    let winner: String
    let result: String
}
