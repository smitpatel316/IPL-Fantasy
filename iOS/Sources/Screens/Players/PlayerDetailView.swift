import SwiftUI

// MARK: - Player Detail View
struct PlayerDetailView: View {
    let player: Player
    @Environment(\.dismiss) var dismiss
    
    var body: some View {
        NavigationStack {
            ZStack {
                AppColors.background
                    .ignoresSafeArea()
                
                ScrollView {
                    VStack(spacing: AppSpacing.lg) {
                        // Header
                        playerHeader
                        
                        // Stats
                        statsSection
                        
                        // Season History
                        seasonHistory
                        
                        // Matchups
                        matchupsSection
                        
                        // News
                        newsSection
                    }
                    .padding(AppSpacing.md)
                }
            }
            .navigationTitle("Player")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .navigationBarTrailing) {
                    Button(action: { dismiss() }) {
                        Image(systemName: "xmark.circle.fill")
                            .foregroundColor(AppColors.textMuted)
                    }
                }
            }
        }
    }
    
    private var playerHeader: some View {
        VStack(spacing: AppSpacing.lg) {
            // Avatar
            ZStack {
                Circle()
                    .fill(roleColor.opacity(0.2))
                    .frame(width: 120, height: 120)
                
                Text(initials)
                    .font(.system(size: 48, weight: .bold))
                    .foregroundColor(roleColor)
            }
            
            // Name & Role
            VStack(spacing: AppSpacing.sm) {
                Text(player.name)
                    .font(AppFonts.title)
                    .fontWeight(.bold)
                    .foregroundColor(AppColors.textPrimary)
                
                HStack(spacing: AppSpacing.md) {
                    Text(player.role.displayName)
                        .font(AppFonts.subheadline)
                        .foregroundColor(roleColor)
                    
                    Text("•")
                        .foregroundColor(AppColors.textMuted)
                    
                    Text(player.team)
                        .font(AppFonts.subheadline)
                        .foregroundColor(AppColors.textSecondary)
                    
                    if player.isOverseas {
                        Text("🌍")
                            .font(.system(size: 16))
                    }
                }
                
                // Price
                HStack(spacing: AppSpacing.sm) {
                    Text("Base Price:")
                        .font(AppFonts.caption)
                        .foregroundColor(AppColors.textMuted)
                    
                    Text("₹\(Int(player.basePrice))Cr")
                        .font(AppFonts.headline)
                        .fontWeight(.bold)
                        .foregroundColor(AppColors.accent)
                }
                .padding(.top, AppSpacing.xs)
            }
        }
        .padding(AppSpacing.lg)
        .frame(maxWidth: .infinity)
        .background(AppColors.card)
        .cornerRadius(AppCornerRadius.card)
    }
    
    private var statsSection: some View {
        VStack(alignment: .leading, spacing: AppSpacing.md) {
            Text("Season Stats")
                .font(AppFonts.headline)
                .foregroundColor(AppColors.textPrimary)
            
            LazyVGrid(columns: [GridItem(.flexible()), GridItem(.flexible())], spacing: AppSpacing.md) {
                StatBox(title: "Matches", value: "15")
                StatBox(title: "Points", value: "312")
                StatBox(title: "Runs", value: "456")
                StatBox(title: "Wickets", value: "0")
                StatBox(title: "Avg Points", value: "20.8")
                StatBox(title: "Form", value: "🔥🔥🔥", isEmoji: true)
            }
        }
        .padding(AppSpacing.md)
        .background(AppColors.card)
        .cornerRadius(AppCornerRadius.medium)
    }
    
    private var seasonHistory: some View {
        VStack(alignment: .leading, spacing: AppSpacing.md) {
            Text("Recent Form")
                .font(AppFonts.headline)
                .foregroundColor(AppColors.textPrimary)
            
            HStack(spacing: AppSpacing.sm) {
                ForEach(0..<5) { i in
                    VStack(spacing: 4) {
                        Text("\(Int.random(in: 15...45))")
                            .font(AppFonts.subheadline)
                            .fontWeight(.bold)
                            .foregroundColor(AppColors.textPrimary)
                        
                        Text("pts")
                            .font(AppFonts.small)
                            .foregroundColor(AppColors.textMuted)
                    }
                    .frame(maxWidth: .infinity)
                    .padding(AppSpacing.sm)
                    .background(i == 0 ? AppColors.success.opacity(0.2) : AppColors.surface)
                    .cornerRadius(AppCornerRadius.small)
                }
            }
        }
        .padding(AppSpacing.md)
        .background(AppColors.card)
        .cornerRadius(AppCornerRadius.medium)
    }
    
    private var matchupsSection: some View {
        VStack(alignment: .leading, spacing: AppSpacing.md) {
            Text("vs Opponent Teams")
                .font(AppFonts.headline)
                .foregroundColor(AppColors.textPrimary)
            
            VStack(spacing: AppSpacing.xs) {
                MatchupRow(opponent: "MI", performance: .good, points: 45)
                MatchupRow(opponent: "CSK", performance: .average, points: 32)
                MatchupRow(opponent: "RCB", performance: .good, points: 52)
                MatchupRow(opponent: "KKR", performance: .bad, points: 18)
            }
        }
        .padding(AppSpacing.md)
        .background(AppColors.card)
        .cornerRadius(AppCornerRadius.medium)
    }
    
    private var newsSection: some View {
        VStack(alignment: .leading, spacing: AppSpacing.md) {
            Text("News")
                .font(AppFonts.headline)
                .foregroundColor(AppColors.textPrimary)
            
            VStack(alignment: .leading, spacing: AppSpacing.sm) {
                Text("• Fit and ready for the new season")
                    .font(AppFonts.caption)
                    .foregroundColor(AppColors.textSecondary)
                Text("• Best performer in last 5 matches")
                    .font(AppFonts.caption)
                    .foregroundColor(AppColors.textSecondary)
            }
        }
        .padding(AppSpacing.md)
        .background(AppColors.card)
        .cornerRadius(AppCornerRadius.medium)
    }
    
    private var roleColor: Color {
        Color(hex: player.role.color)
    }
    
    private var initials: String {
        let parts = player.name.components(separatedBy: " ")
        let initials = parts.compactMap { $0.first }.prefix(2)
        return String(initials).uppercased()
    }
}

// MARK: - Stat Box
struct StatBox: View {
    let title: String
    let value: String
    var isEmoji: Bool = false
    
    var body: some View {
        VStack(spacing: AppSpacing.xs) {
            if isEmoji {
                Text(value)
                    .font(.system(size: 24))
            } else {
                Text(value)
                    .font(AppFonts.headline)
                    .fontWeight(.bold)
                    .foregroundColor(AppColors.textPrimary)
            }
            
            Text(title)
                .font(AppFonts.caption)
                .foregroundColor(AppColors.textMuted)
        }
        .frame(maxWidth: .infinity)
        .padding(AppSpacing.md)
        .background(AppColors.surface)
        .cornerRadius(AppCornerRadius.small)
    }
}

// MARK: - Matchup Row
struct MatchupRow: View {
    let opponent: String
    let performance: Performance
    let points: Int
    
    enum Performance {
        case good, average, bad
        
        var color: Color {
            switch self {
            case .good: return AppColors.success
            case .average: return AppColors.warning
            case .bad: return AppColors.error
            }
        }
        
        var icon: String {
            switch self {
            case .good: return "arrow.up.circle.fill"
            case .average: return "minus.circle.fill"
            case .bad: return "arrow.down.circle.fill"
            }
        }
    }
    
    var body: some View {
        HStack {
            Text(opponent)
                .font(AppFonts.subheadline)
                .foregroundColor(AppColors.textPrimary)
            
            Spacer()
            
            Image(systemName: performance.icon)
                .foregroundColor(performance.color)
            
            Text("\(points) pts")
                .font(AppFonts.subheadline)
                .fontWeight(.bold)
                .foregroundColor(performance.color)
        }
        .padding(AppSpacing.sm)
    }
}
