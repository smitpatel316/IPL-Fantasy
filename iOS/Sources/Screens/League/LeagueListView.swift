import SwiftUI

// MARK: - League List View
struct LeagueListView: View {
    @StateObject private var viewModel = LeagueViewModel()
    @State private var showingCreateSheet = false
    @State private var showingJoinSheet = false
    
    var body: some View {
        NavigationStack {
            ZStack {
                AppColors.background
                    .ignoresSafeArea()
                
                VStack(spacing: 0) {
                    // Action Buttons
                    actionButtons
                    
                    // League List
                    if viewModel.leagues.isEmpty {
                        EmptyStateView(
                            icon: "person.3",
                            title: "No Leagues",
                            message: "Create your own league or join one with a code",
                            buttonTitle: "Create League"
                        ) {
                            showingCreateSheet = true
                        }
                        .frame(maxHeight: .infinity)
                    } else {
                        ScrollView {
                            LazyVStack(spacing: AppSpacing.md) {
                                ForEach(viewModel.leagues) { league in
                                    LeagueRowView(league: league) {
                                        viewModel.selectLeague(league)
                                    }
                                }
                            }
                            .padding(AppSpacing.md)
                        }
                    }
                }
            }
            .navigationTitle("Leagues")
            .navigationBarTitleDisplayMode(.large)
            .sheet(isPresented: $showingCreateSheet) {
                CreateLeagueSheet(viewModel: viewModel)
            }
            .sheet(isPresented: $showingJoinSheet) {
                JoinLeagueSheet(viewModel: viewModel)
            }
            .onAppear {
                viewModel.loadLeagues()
            }
        }
    }
    
    private var actionButtons: some View {
        HStack(spacing: AppSpacing.md) {
            Button(action: { showingCreateSheet = true }) {
                HStack {
                    Image(systemName: "plus")
                    Text("Create")
                }
                .font(AppFonts.subheadline)
                .fontWeight(.semibold)
                .foregroundColor(AppColors.textPrimary)
                .frame(maxWidth: .infinity)
                .padding(.vertical, AppSpacing.md)
                .background(AppColors.primary)
                .cornerRadius(AppCornerRadius.medium)
            }
            
            Button(action: { showingJoinSheet = true }) {
                HStack {
                    Image(systemName: "qrcode")
                    Text("Join")
                }
                .font(AppFonts.subheadline)
                .fontWeight(.semibold)
                .foregroundColor(AppColors.textPrimary)
                .frame(maxWidth: .infinity)
                .padding(.vertical, AppSpacing.md)
                .background(AppColors.surface)
                .overlay(
                    RoundedRectangle(cornerRadius: AppCornerRadius.medium)
                        .stroke(AppColors.primary, lineWidth: 2)
                )
                .cornerRadius(AppCornerRadius.medium)
            }
        }
        .padding(AppSpacing.md)
        .background(AppColors.card)
    }
}

// MARK: - League Row
struct LeagueRowView: View {
    let league: League
    var action: () -> Void
    
    var body: some View {
        Button(action: action) {
            CardView {
                VStack(alignment: .leading, spacing: AppSpacing.md) {
                    HStack {
                        Text(league.name)
                            .font(AppFonts.subheadline)
                            .fontWeight(.bold)
                            .foregroundColor(AppColors.textPrimary)

                        Spacer()
                        
                        BadgeView(text: league.status.rawValue.uppercased(), color: statusColor)
                    }
                    
                    Divider().background(AppColors.textMuted)
                    
                    HStack(spacing: AppSpacing.md) {
                        LeagueStat(label: "Teams", value: "\(league.members.count)/\(league.maxTeams)")
                        LeagueStat(label: "Budget", value: "₹\(Int(league.auctionBudget))Cr")
                        
                        Spacer()
                        
                        if league.status == .open {
                            Text("Code: \(league.code)")
                                .font(AppFonts.caption)
                                .fontWeight(.medium)
                                .foregroundColor(AppColors.accent)
                        }
                    }
                    
                    if league.status == .open && !league.members.isEmpty {
                        HStack {
                            Text("Members:")
                                .font(AppFonts.caption)
                                .foregroundColor(AppColors.textSecondary)
                            
                            ForEach(league.members.prefix(3)) { member in
                                Circle()
                                    .fill(AppColors.primary.opacity(0.3))
                                    .frame(width: 24, height: 24)
                                    .overlay(
                                        Text(String(member.teamName.prefix(1)))
                                            .font(AppFonts.small)
                                            .foregroundColor(AppColors.textPrimary)
                                    )
                            }
                            
                            if league.members.count > 3 {
                                Text("+\(league.members.count - 3)")
                                    .font(AppFonts.caption)
                                    .foregroundColor(AppColors.textSecondary)
                            }
                        }
                    }
                }
            }
        }
        .buttonStyle(ScaleButtonStyle())
    }
    
    private var statusColor: Color {
        switch league.status {
        case .open: return AppColors.success
        case .drafting: return AppColors.warning
        case .active: return AppColors.primary
        case .completed: return AppColors.textMuted
        }
    }
}

struct LeagueStat: View {
    let label: String
    let value: String
    
    var body: some View {
        VStack(alignment: .leading, spacing: AppSpacing.xs) {
            Text(label)
                .font(AppFonts.caption)
                .foregroundColor(AppColors.textSecondary)
            Text(value)
                .font(AppFonts.body)
                .fontWeight(.semibold)
                .foregroundColor(AppColors.textPrimary)
        }
    }
}

// MARK: - Scale Button Style
struct ScaleButtonStyle: ButtonStyle {
    func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .scaleEffect(configuration.isPressed ? 0.98 : 1)
            .animation(.easeInOut(duration: 0.1), value: configuration.isPressed)
    }
}
