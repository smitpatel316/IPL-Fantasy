import SwiftUI

// MARK: - Snake Draft View
struct SnakeDraftView: View {
    @ObservedObject var viewModel: DraftViewModel
    @State private var showingPlayerPicker = false
    @State private var selectedPlayer: Player?
    let leagueId: String
    
    private let columns = [
        GridItem(.flexible()),
        GridItem(.flexible()),
        GridItem(.flexible())
    ]
    
    var body: some View {
        NavigationStack {
            ZStack {
                AppColors.background
                    .ignoresSafeArea()
                
                VStack(spacing: 0) {
                    // Current Pick Banner
                    currentPickBanner
                    
                    // Draft Board
                    draftBoardSection
                    
                    // Available Players
                    availablePlayersSection
                }
            }
            .navigationTitle("Snake Draft")
            .navigationBarTitleDisplayMode(.large)
            .toolbar {
                ToolbarItem(placement: .navigationBarTrailing) {
                    if viewModel.isDraftActive {
                        Button("End Draft") {
                            viewModel.stopDraft()
                        }
                        .foregroundColor(AppColors.error)
                    }
                }
            }
            .sheet(isPresented: $showingPlayerPicker) {
                PlayerPickerSheet(
                    players: viewModel.availablePlayers,
                    onSelect: { player in
                        selectedPlayer = player
                        showingPlayerPicker = false
                        Task {
                            await viewModel.makePick(playerId: player.id, leagueId: leagueId)
                        }
                    }
                )
            }
            .task {
                await viewModel.loadDraftState(leagueId: leagueId)
            }
        }
    }
    
    // MARK: - Current Pick Banner
    
    private var currentPickBanner: some View {
        VStack(spacing: AppSpacing.sm) {
            HStack {
                VStack(alignment: .leading, spacing: AppSpacing.xs) {
                    Text("Pick #\(viewModel.currentPickNumber + 1)")
                        .font(AppFonts.headline)
                        .foregroundColor(AppColors.textPrimary)
                    
                    if let teamName = viewModel.currentPickTeamName {
                        Text(teamName)
                            .font(AppFonts.subheadline)
                            .foregroundColor(AppColors.textSecondary)
                    }
                }
                
                Spacer()
                
                if viewModel.isDraftActive {
                    Button(action: {
                        showingPlayerPicker = true
                    }) {
                        Text("Make Pick")
                            .font(AppFonts.subheadline)
                            .fontWeight(.semibold)
                            .foregroundColor(.white)
                            .padding(.horizontal, AppSpacing.lg)
                            .padding(.vertical, AppSpacing.md)
                            .background(AppColors.primary)
                            .cornerRadius(AppCornerRadius.medium)
                    }
                }
            }
            
            // Progress
            ProgressView(value: Double(viewModel.currentPickNumber), total: 150)
                .progressViewStyle(LinearProgressViewStyle(tint: AppColors.primary))
        }
        .padding(AppSpacing.md)
        .background(AppColors.card)
    }
    
    // MARK: - Draft Board Section
    
    private var draftBoardSection: some View {
        VStack(alignment: .leading, spacing: AppSpacing.md) {
            Text("Draft Board")
                .font(AppFonts.headline)
                .foregroundColor(AppColors.textPrimary)
                .padding(.horizontal, AppSpacing.md)
                .padding(.top, AppSpacing.md)
            
            ScrollView {
                LazyVStack(spacing: AppSpacing.sm) {
                    ForEach(Array(stride(from: 1, through: 15, by: 3)), id: \.self) { round in
                        roundRow(round: round)
                    }
                }
                .padding(.horizontal, AppSpacing.md)
            }
        }
        .frame(height: 200)
        .background(AppColors.surface)
    }
    
    private func roundRow(round: Int) -> some View {
        HStack(spacing: AppSpacing.xs) {
            Text("R\(round)")
                .font(AppFonts.caption)
                .foregroundColor(AppColors.textMuted)
                .frame(width: 25)
            
            ForEach(0..<3, id: \.self) { offset in
                let pickNum = round + offset
                pickCell(pickNumber: pickNum)
            }
        }
    }
    
    private func pickCell(pickNumber: Int) -> some View {
        let pick = viewModel.snakePicks.first { $0.pickNumber == pickNumber }
        
        return ZStack {
            RoundedRectangle(cornerRadius: 4)
                .fill(pick?.isMade == true ? AppColors.success.opacity(0.2) : AppColors.card)
                .frame(height: 36)
            
            if let pick = pick, let playerName = pick.playerName {
                Text(String(playerName.prefix(8)))
                    .font(AppFonts.caption)
                    .foregroundColor(AppColors.textPrimary)
            } else {
                Text("\(pickNumber)")
                    .font(AppFonts.caption)
                    .foregroundColor(AppColors.textMuted)
            }
        }
    }
    
    // MARK: - Available Players Section
    
    private var availablePlayersSection: some View {
        VStack(alignment: .leading, spacing: AppSpacing.md) {
            HStack {
                Text("Available Players")
                    .font(AppFonts.headline)
                    .foregroundColor(AppColors.textPrimary)
                
                Spacer()
                
                Text("\(viewModel.availablePlayers.count) left")
                    .font(AppFonts.caption)
                    .foregroundColor(AppColors.textMuted)
            }
            .padding(.horizontal, AppSpacing.md)
            .padding(.top, AppSpacing.md)
            
            ScrollView {
                LazyVStack(spacing: AppSpacing.sm) {
                    ForEach(viewModel.availablePlayers) { player in
                        AvailablePlayerRow(player: player) {
                            Task {
                                await viewModel.makePick(playerId: player.id, leagueId: leagueId)
                            }
                        }
                    }
                }
                .padding(.horizontal, AppSpacing.md)
            }
        }
        .background(AppColors.surface)
    }
}

// MARK: - Available Player Row

struct AvailablePlayerRow: View {
    let player: Player
    let onPick: () -> Void
    
    var body: some View {
        HStack {
            VStack(alignment: .leading, spacing: AppSpacing.xs) {
                Text(player.name)
                    .font(AppFonts.subheadline)
                    .fontWeight(.semibold)
                    .foregroundColor(AppColors.textPrimary)
                
                HStack(spacing: AppSpacing.sm) {
                    Text(player.team)
                        .font(AppFonts.caption)
                        .foregroundColor(AppColors.textSecondary)
                    
                    Text(player.role.displayName)
                        .font(AppFonts.caption)
                        .foregroundColor(roleColor(for: player.role))
                }
            }
            
            Spacer()
            
            Text("₹\(Int(player.basePrice))Cr")
                .font(AppFonts.subheadline)
                .fontWeight(.bold)
                .foregroundColor(AppColors.success)
            
            Button(action: onPick) {
                Image(systemName: "plus.circle.fill")
                    .font(.title2)
                    .foregroundColor(AppColors.primary)
            }
        }
        .padding(AppSpacing.md)
        .background(AppColors.card)
        .cornerRadius(AppCornerRadius.small)
    }
    
    private func roleColor(for role: Player.PlayerRole) -> Color {
        switch role {
        case .batsman: return AppColors.success
        case .bowler: return AppColors.error
        case .allRounder: return Color.purple
        case .wicketKeeper: return AppColors.primary
        }
    }
}

// MARK: - Player Picker Sheet

struct PlayerPickerSheet: View {
    let players: [Player]
    let onSelect: (Player) -> Void
    
    @Environment(\.dismiss) private var dismiss
    
    var body: some View {
        NavigationStack {
            ZStack {
                AppColors.background
                    .ignoresSafeArea()
                
                ScrollView {
                    LazyVStack(spacing: AppSpacing.sm) {
                        ForEach(players) { player in
                            Button(action: { onSelect(player) }) {
                                HStack {
                                    VStack(alignment: .leading) {
                                        Text(player.name)
                                            .font(AppFonts.subheadline)
                                            .fontWeight(.semibold)
                                            .foregroundColor(AppColors.textPrimary)
                                        
                                        Text("\(player.team) • \(player.role.displayName)")
                                            .font(AppFonts.caption)
                                            .foregroundColor(AppColors.textSecondary)
                                    }
                                    
                                    Spacer()
                                    
                                    Text("₹\(Int(player.basePrice))Cr")
                                        .font(AppFonts.subheadline)
                                        .fontWeight(.bold)
                                        .foregroundColor(AppColors.success)
                                }
                                .padding(AppSpacing.md)
                                .background(AppColors.card)
                                .cornerRadius(AppCornerRadius.small)
                            }
                        }
                    }
                    .padding(AppSpacing.md)
                }
            }
            .navigationTitle("Select Player")
            .navigationBarTitleDisplayMode(.large)
            .toolbar {
                ToolbarItem(placement: .navigationBarTrailing) {
                    Button("Cancel") {
                        dismiss()
                    }
                }
            }
        }
    }
}
