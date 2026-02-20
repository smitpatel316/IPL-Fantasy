import SwiftUI

// MARK: - My Team View
struct MyTeamView: View {
    @StateObject private var viewModel = TeamViewModel()
    @State private var selectedTab = 0
    
    var body: some View {
        NavigationStack {
            ZStack {
                AppColors.background
                    .ignoresSafeArea()
                
                VStack(spacing: 0) {
                    // Team Summary Header
                    teamHeader
                    
                    // Captain Selection
                    captainSection
                    
                    // Player List
                    playerList
                }
            }
            .navigationTitle("My Team")
            .navigationBarTitleDisplayMode(.large)
            .toolbar {
                ToolbarItem(placement: .navigationBarTrailing) {
                    Button("Save") {
                        viewModel.saveTeam()
                    }
                    .foregroundColor(AppColors.primary)
                }
            }
        }
    }
    
    private var teamHeader: some View {
        VStack(spacing: AppSpacing.md) {
            HStack {
                VStack(alignment: .leading, spacing: AppSpacing.xs) {
                    Text("Team Fire")
                        .font(AppFonts.title)
                        .fontWeight(.bold)
                        .foregroundColor(AppColors.textPrimary)
                    
                    Text("15 Players • ₹42.5Cr spent")
                        .font(AppFonts.caption)
                        .foregroundColor(AppColors.textSecondary)
                }
                
                Spacer()
                
                VStack(alignment: .trailing, spacing: AppSpacing.xs) {
                    Text("Budget")
                        .font(AppFonts.caption)
                        .foregroundColor(AppColors.textSecondary)
                    Text("₹7.5Cr")
                        .font(AppFonts.headline)
                        .fontWeight(.bold)
                        .foregroundColor(AppColors.accent)
                }
            }
            .padding(AppSpacing.md)
            .background(AppColors.card)
            .cornerRadius(AppCornerRadius.medium)
        }
        .padding(AppSpacing.md)
    }
    
    private var captainSection: some View {
        VStack(alignment: .leading, spacing: AppSpacing.sm) {
            Text("Select Captain & Vice-Captain")
                .font(AppFonts.headline)
                .foregroundColor(AppColors.textPrimary)
            
            HStack(spacing: AppSpacing.md) {
                // Captain
                VStack(spacing: AppSpacing.sm) {
                    Text("C")
                        .font(AppFonts.caption)
                        .fontWeight(.bold)
                        .foregroundColor(.white)
                        .frame(width: 24, height: 24)
                        .background(AppColors.primary)
                        .clipShape(Circle())
                    
                    if let captain = viewModel.captain {
                        Text(captain.name.components(separatedBy: " ").first ?? "")
                            .font(AppFonts.caption)
                            .foregroundColor(AppColors.textPrimary)
                            .lineLimit(1)
                    } else {
                        Text("Select")
                            .font(AppFonts.caption)
                            .foregroundColor(AppColors.textMuted)
                    }
                }
                .frame(maxWidth: .infinity)
                
                // Vice-Captain
                VStack(spacing: AppSpacing.sm) {
                    Text("VC")
                        .font(AppFonts.caption)
                        .fontWeight(.bold)
                        .foregroundColor(.white)
                        .frame(width: 24, height: 24)
                        .background(AppColors.accent)
                        .clipShape(Circle())
                    
                    if let vice = viewModel.viceCaptain {
                        Text(vice.name.components(separatedBy: " ").first ?? "")
                            .font(AppFonts.caption)
                            .foregroundColor(AppColors.textPrimary)
                            .lineLimit(1)
                    } else {
                        Text("Select")
                            .font(AppFonts.caption)
                            .foregroundColor(AppColors.textMuted)
                    }
                }
                .frame(maxWidth: .infinity)
            }
            .padding(AppSpacing.md)
            .background(AppColors.card)
            .cornerRadius(AppCornerRadius.medium)
        }
        .padding(.horizontal, AppSpacing.md)
    }
    
    private var playerList: some View {
        VStack(alignment: .leading, spacing: AppSpacing.sm) {
            HStack {
                Text("Squad")
                    .font(AppFonts.headline)
                    .foregroundColor(AppColors.textPrimary)
                
                Spacer()
                
                Picker("Filter", selection: $selectedTab) {
                    Text("All").tag(0)
                    Text("Batsmen").tag(1)
                    Text("Bowlers").tag(2)
                    Text("All-Rounders").tag(3)
                    Text("WK").tag(4)
                }
                .pickerStyle(SegmentedPickerStyle())
                .frame(width: 200)
            }
            .padding(.horizontal, AppSpacing.md)
            
            ScrollView {
                LazyVStack(spacing: AppSpacing.sm) {
                    ForEach(filteredPlayers) { player in
                        TeamPlayerRow(
                            player: player,
                            isCaptain: viewModel.captain?.id == player.id,
                            isViceCaptain: viewModel.viceCaptain?.id == player.id,
                            onSelectCaptain: { viewModel.selectCaptain(player) },
                            onSelectVice: { viewModel.selectViceCaptain(player) }
                        )
                    }
                }
                .padding(AppSpacing.md)
            }
        }
    }
    
    private var filteredPlayers: [Player] {
        switch selectedTab {
        case 0: return viewModel.squad
        case 1: return viewModel.squad.filter { $0.role == .batsman }
        case 2: return viewModel.squad.filter { $0.role == .bowler }
        case 3: return viewModel.squad.filter { $0.role == .allRounder }
        case 4: return viewModel.squad.filter { $0.role == .wicketKeeper }
        default: return viewModel.squad
        }
    }
}

// MARK: - Team Player Row
struct TeamPlayerRow: View {
    let player: Player
    let isCaptain: Bool
    let isViceCaptain: Bool
    let onSelectCaptain: () -> Void
    let onSelectVice: () -> Void
    
    var body: some View {
        HStack(spacing: AppSpacing.md) {
            // Role indicator
            Circle()
                .fill(Color(hex: player.role.color).opacity(0.2))
                .frame(width: 40, height: 40)
                .overlay(
                    Text(player.role.displayName.prefix(1))
                        .font(AppFonts.caption)
                        .fontWeight(.bold)
                        .foregroundColor(Color(hex: player.role.color))
                )
            
            // Player info
            VStack(alignment: .leading, spacing: AppSpacing.xs) {
                HStack {
                    Text(player.name)
                        .font(AppFonts.subheadline)
                        .fontWeight(.semibold)
                        .foregroundColor(AppColors.textPrimary)
                    
                    if isCaptain {
                        BadgeView(text: "C", color: AppColors.primary)
                    } else if isViceCaptain {
                        BadgeView(text: "VC", color: AppColors.accent)
                    }
                }
                
                Text("\(player.team) • \(player.role.displayName)")
                    .font(AppFonts.caption)
                    .foregroundColor(AppColors.textSecondary)
            }
            
            Spacer()
            
            // Points
            VStack(alignment: .trailing, spacing: AppSpacing.xs) {
                Text("\(player.totalPoints) pts")
                    .font(AppFonts.subheadline)
                    .fontWeight(.bold)
                    .foregroundColor(AppColors.textPrimary)
                
                Text("₹\(Int(player.basePrice))Cr")
                    .font(AppFonts.caption)
                    .foregroundColor(AppColors.accent)
            }
            
            // Quick actions
            Menu {
                Button(action: onSelectCaptain) {
                    Label("Make Captain (2x)", systemImage: "star.fill")
                }
                Button(action: onSelectVice) {
                    Label("Make Vice (1.5x)", systemImage: "star")
                }
            } label: {
                Image(systemName: "ellipsis")
                    .foregroundColor(AppColors.textMuted)
                    .padding(AppSpacing.sm)
            }
        }
        .padding(AppSpacing.md)
        .background(AppColors.card)
        .cornerRadius(AppCornerRadius.medium)
    }
}
