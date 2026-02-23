import SwiftUI

// MARK: - Join League From Link View
struct JoinLeagueFromLinkView: View {
    let inviteCode: String
    @Environment(\.dismiss) var dismiss
    @StateObject private var viewModel = LeagueViewModel()
    @State private var teamName = ""
    @State private var isLoading = true
    @State private var errorMessage: String?
    @State private var leagueInfo: InviteLeagueInfo?
    @State private var joined = false
    
    var body: some View {
        NavigationStack {
            ZStack {
                AppColors.background
                    .ignoresSafeArea()
                
                if isLoading {
                    ProgressView()
                        .progressViewStyle(CircularProgressViewStyle(tint: AppColors.primary))
                } else if joined {
                    joinedView
                } else if let league = leagueInfo {
                    joinContent(league: league)
                } else if let error = errorMessage {
                    errorView(message: error)
                }
            }
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .navigationBarLeading) {
                    Button("Cancel") {
                        dismiss()
                    }
                    .foregroundColor(AppColors.primary)
                }
            }
            .onAppear {
                validateInviteCode()
            }
        }
    }
    
    private func joinContent(league: InviteLeagueInfo) -> some View {
        VStack(spacing: AppSpacing.xl) {
            // League Info Header
            VStack(spacing: AppSpacing.md) {
                ZStack {
                    Circle()
                        .fill(AppColors.primary.opacity(0.2))
                        .frame(width: 80, height: 80)
                    
                    Text(String(league.name.prefix(1)))
                        .font(.system(size: 32, weight: .bold))
                        .foregroundColor(AppColors.primary)
                }
                
                Text("Join \(league.name)")
                    .font(AppFonts.title)
                    .fontWeight(.bold)
                    .foregroundColor(AppColors.textPrimary)
                
                HStack(spacing: AppSpacing.lg) {
                    Label("\(league.currentTeams)/\(league.maxTeams) Teams", systemImage: "person.3")
                    Label(league.status.capitalized, systemImage: "circle.fill")
                        .foregroundColor(statusColor(for: league.status))
                }
                .font(AppFonts.caption)
                .foregroundColor(AppColors.textSecondary)
            }
            .padding(.top, AppSpacing.xl)
            
            // Team Name Input
            VStack(alignment: .leading, spacing: AppSpacing.sm) {
                Text("Your Team Name")
                    .font(AppFonts.caption)
                    .foregroundColor(AppColors.textSecondary)
                
                TextField("Enter your team name", text: $teamName)
                    .textFieldStyle(CustomTextFieldStyle())
            }
            .padding(.horizontal)
            
            // Error message
            if let error = errorMessage {
                Text(error)
                    .font(AppFonts.caption)
                    .foregroundColor(AppColors.error)
            }
            
            // Join Button
            Button(action: joinLeague) {
                Text("Join League")
                    .font(AppFonts.subheadline)
                    .fontWeight(.semibold)
                    .foregroundColor(.white)
                    .frame(maxWidth: .infinity)
                    .padding(.vertical, AppSpacing.md)
                    .background(teamName.isEmpty ? AppColors.textMuted : AppColors.primary)
                    .cornerRadius(AppCornerRadius.medium)
            }
            .disabled(teamName.isEmpty || league.isFull)
            .padding(.horizontal)
            
            if league.isFull {
                Text("This league is full and cannot accept new members")
                    .font(AppFonts.caption)
                    .foregroundColor(AppColors.error)
                    .multilineTextAlignment(.center)
                    .padding(.horizontal)
            }
            
            Spacer()
        }
    }
    
    private var joinedView: some View {
        VStack(spacing: AppSpacing.xl) {
            Image(systemName: "checkmark.circle.fill")
                .font(.system(size: 80))
                .foregroundColor(AppColors.success)
                .padding(.top, AppSpacing.xxl)
            
            Text("Welcome to the League!")
                .font(AppFonts.title)
                .fontWeight(.bold)
                .foregroundColor(AppColors.textPrimary)
            
            Text("You've successfully joined \(leagueInfo?.name ?? "the league")")
                .font(AppFonts.body)
                .foregroundColor(AppColors.textSecondary)
                .multilineTextAlignment(.center)
            
            Button(action: { dismiss() }) {
                Text("Continue")
                    .font(AppFonts.subheadline)
                    .fontWeight(.semibold)
                    .foregroundColor(.white)
                    .frame(maxWidth: .infinity)
                    .padding(.vertical, AppSpacing.md)
                    .background(AppColors.primary)
                    .cornerRadius(AppCornerRadius.medium)
            }
            .padding(.horizontal, AppSpacing.lg)
            
            Spacer()
        }
        .padding()
    }
    
    private func errorView(message: String) -> some View {
        VStack(spacing: AppSpacing.xl) {
            Image(systemName: "xmark.circle.fill")
                .font(.system(size: 80))
                .foregroundColor(AppColors.error)
                .padding(.top, AppSpacing.xxl)
            
            Text("Invalid Invite")
                .font(AppFonts.title)
                .fontWeight(.bold)
                .foregroundColor(AppColors.textPrimary)
            
            Text(message)
                .font(AppFonts.body)
                .foregroundColor(AppColors.textSecondary)
                .multilineTextAlignment(.center)
            
            Button(action: { dismiss() }) {
                Text("Go Back")
                    .font(AppFonts.subheadline)
                    .fontWeight(.semibold)
                    .foregroundColor(.white)
                    .frame(maxWidth: .infinity)
                    .padding(.vertical, AppSpacing.md)
                    .background(AppColors.primary)
                    .cornerRadius(AppCornerRadius.medium)
            }
            .padding(.horizontal, AppSpacing.lg)
            
            Spacer()
        }
        .padding()
    }
    
    private func statusColor(for status: String) -> Color {
        switch status.lowercased() {
        case "open": return AppColors.success
        case "drafting": return AppColors.warning
        case "active": return AppColors.primary
        default: return AppColors.textMuted
        }
    }
    
    private func validateInviteCode() {
        Task {
            do {
                let result = try await LeagueService.shared.validateInviteCode(inviteCode)
                
                await MainActor.run {
                    if result.valid, let league = result.league {
                        leagueInfo = league
                    } else {
                        errorMessage = "Invalid invite code"
                    }
                    isLoading = false
                }
            } catch {
                await MainActor.run {
                    errorMessage = error.localizedDescription
                    isLoading = false
                }
            }
        }
    }
    
    private func joinLeague() {
        Task {
            do {
                let _ = try await LeagueService.shared.joinLeague(code: inviteCode, teamName: teamName)
                
                await MainActor.run {
                    joined = true
                }
            } catch {
                await MainActor.run {
                    errorMessage = error.localizedDescription
                }
            }
        }
    }
}

// MARK: - Invite League Info
struct InviteLeagueInfo: Identifiable {
    let id: String
    let name: String
    let code: String
    let maxTeams: Int
    let currentTeams: Int
    let isFull: Bool
    let status: String
}
