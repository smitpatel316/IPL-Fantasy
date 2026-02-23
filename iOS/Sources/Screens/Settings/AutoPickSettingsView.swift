import SwiftUI

// MARK: - Auto-Pick Settings View
struct AutoPickSettingsView: View {
    @StateObject private var viewModel = AutoPickSettingsViewModel()
    @Environment(\.dismiss) private var dismiss
    
    let leagueId: String
    let leagueName: String
    
    var body: some View {
        NavigationStack {
            ZStack {
                AppColors.background
                    .ignoresSafeArea()
                
                ScrollView {
                    VStack(spacing: AppSpacing.lg) {
                        // Enable Auto-Pick Toggle
                        enableSection
                        
                        // Favorite Players
                        if viewModel.settings.isEnabled {
                            favoritePlayersSection
                            
                            // Preferred Roles
                            preferredRolesSection
                            
                            // Budget Settings
                            budgetSection
                            
                            // Auto-Bid Settings
                            autoBidSection
                        }
                    }
                    .padding(AppSpacing.md)
                }
            }
            .navigationTitle("Auto-Pick Settings")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .navigationBarLeading) {
                    Button("Cancel") {
                        dismiss()
                    }
                }
                
                ToolbarItem(placement: .navigationBarTrailing) {
                    Button("Save") {
                        Task {
                            await viewModel.saveSettings()
                            dismiss()
                        }
                    }
                    .fontWeight(.semibold)
                    .disabled(!viewModel.hasChanges)
                }
            }
            .alert("Error", isPresented: $viewModel.showError) {
                Button("OK", role: .cancel) {}
            } message: {
                Text(viewModel.errorMessage)
            }
            .task {
                await viewModel.loadSettings(leagueId: leagueId)
            }
            .overlay {
                if viewModel.isLoading {
                    ProgressView()
                        .scaleEffect(1.5)
                        .frame(maxWidth: .infinity, maxHeight: .infinity)
                        .background(AppColors.background.opacity(0.8))
                }
            }
        }
    }
    
    // MARK: - Enable Section
    
    private var enableSection: some View {
        VStack(alignment: .leading, spacing: AppSpacing.md) {
            HStack {
                Image(systemName: "bolt.fill")
                    .font(.system(size: 24))
                    .foregroundColor(AppColors.primary)
                
                VStack(alignment: .leading, spacing: 2) {
                    Text("Enable Auto-Pick")
                        .font(AppFonts.headline)
                        .foregroundColor(AppColors.textPrimary)
                    
                    Text("Automatically pick/bid on players when timer expires")
                        .font(AppFonts.caption)
                        .foregroundColor(AppColors.textSecondary)
                }
                
                Spacer()
                
                Toggle("", isOn: $viewModel.settings.isEnabled)
                    .tint(AppColors.primary)
            }
            
            if viewModel.settings.isEnabled {
                Text("Auto-pick will activate during the draft when it's your turn and the timer is about to expire.")
                    .font(AppFonts.caption)
                    .foregroundColor(AppColors.textMuted)
                    .padding(AppSpacing.sm)
                    .background(AppColors.primary.opacity(0.1))
                    .cornerRadius(AppCornerRadius.small)
            }
        }
        .padding(AppSpacing.md)
        .background(AppColors.card)
        .cornerRadius(AppCornerRadius.medium)
    }
    
    // MARK: - Favorite Players Section
    
    private var favoritePlayersSection: some View {
        VStack(alignment: .leading, spacing: AppSpacing.md) {
            Text("Favorite Players")
                .font(AppFonts.headline)
                .foregroundColor(AppColors.textPrimary)
            
            Text("These players will always be picked automatically")
                .font(AppFonts.caption)
                .foregroundColor(AppColors.textSecondary)
            
            if viewModel.availablePlayers.isEmpty {
                ProgressView()
                    .frame(maxWidth: .infinity)
                    .padding(AppSpacing.lg)
            } else {
                // Selected favorites
                if !viewModel.settings.favoritePlayers.isEmpty {
                    ScrollView(.horizontal, showsIndicators: false) {
                        HStack(spacing: AppSpacing.sm) {
                            ForEach(viewModel.settings.favoritePlayers, id: \.self) { playerId in
                                if let player = viewModel.availablePlayers.first(where: { $0.id == playerId }) {
                                    FavoritePlayerChip(
                                        player: player,
                                        onRemove: {
                                            viewModel.toggleFavoritePlayer(player.id)
                                        }
                                    )
                                }
                            }
                        }
                    }
                }
                
                // Add more button
                Menu {
                    ForEach(viewModel.availablePlayers.filter { !viewModel.settings.favoritePlayers.contains($0.id) }) { player in
                        Button(action: {
                            viewModel.toggleFavoritePlayer(player.id)
                        }) {
                            Label(player.name, systemImage: "plus")
                        }
                    }
                } label: {
                    HStack {
                        Image(systemName: "plus.circle.fill")
                        Text("Add Favorite")
                    }
                    .font(AppFonts.subheadline)
                    .fontWeight(.semibold)
                    .foregroundColor(AppColors.primary)
                    .padding(AppSpacing.md)
                    .frame(maxWidth: .infinity)
                    .background(AppColors.primary.opacity(0.1))
                    .cornerRadius(AppCornerRadius.medium)
                }
            }
        }
        .padding(AppSpacing.md)
        .background(AppColors.card)
        .cornerRadius(AppCornerRadius.medium)
    }
    
    // MARK: - Preferred Roles Section
    
    private var preferredRolesSection: some View {
        VStack(alignment: .leading, spacing: AppSpacing.md) {
            Text("Preferred Roles")
                .font(AppFonts.headline)
                .foregroundColor(AppColors.textPrimary)
            
            Text("Pick players from these roles automatically")
                .font(AppFonts.caption)
                .foregroundColor(AppColors.textSecondary)
            
            HStack(spacing: AppSpacing.sm) {
                ForEach(Player.PlayerRole.allCases, id: \.self) { role in
                    RoleChip(
                        role: role,
                        isSelected: viewModel.settings.preferredRoles.contains(role),
                        onTap: {
                            viewModel.togglePreferredRole(role)
                        }
                    )
                }
            }
            
            Text("Leave empty to pick players from any role")
                .font(AppFonts.caption)
                .foregroundColor(AppColors.textMuted)
        }
        .padding(AppSpacing.md)
        .background(AppColors.card)
        .cornerRadius(AppCornerRadius.medium)
    }
    
    // MARK: - Budget Section
    
    private var budgetSection: some View {
        VStack(alignment: .leading, spacing: AppSpacing.md) {
            Text("Maximum Price")
                .font(AppFonts.headline)
                .foregroundColor(AppColors.textPrimary)
            
            Text("Only pick players within your budget")
                .font(AppFonts.caption)
                .foregroundColor(AppColors.textSecondary)
            
            VStack(spacing: AppSpacing.sm) {
                Slider(
                    value: $viewModel.settings.maxPrice,
                    in: 1...100,
                    step: 1
                )
                .tint(AppColors.primary)
                
                HStack {
                    Text("₹1Cr")
                        .font(AppFonts.caption)
                        .foregroundColor(AppColors.textMuted)
                    
                    Spacer()
                    
                    Text("₹\(Int(viewModel.settings.maxPrice))Cr")
                        .font(AppFonts.headline)
                        .foregroundColor(AppColors.primary)
                    
                    Spacer()
                    
                    Text("₹100Cr")
                        .font(AppFonts.caption)
                        .foregroundColor(AppColors.textMuted)
                }
            }
        }
        .padding(AppSpacing.md)
        .background(AppColors.card)
        .cornerRadius(AppCornerRadius.medium)
    }
    
    // MARK: - Auto-Bid Section
    
    private var autoBidSection: some View {
        VStack(alignment: .leading, spacing: AppSpacing.md) {
            Toggle(isOn: $viewModel.settings.autoBidEnabled) {
                VStack(alignment: .leading, spacing: 2) {
                    Text("Auto-Bid")
                        .font(AppFonts.headline)
                        .foregroundColor(AppColors.textPrimary)
                    
                    Text("Automatically increase bids when competing")
                        .font(AppFonts.caption)
                        .foregroundColor(AppColors.textSecondary)
                }
            }
            .tint(AppColors.primary)
            
            if viewModel.settings.autoBidEnabled {
                VStack(spacing: AppSpacing.sm) {
                    Text("Bid Increment")
                        .font(AppFonts.subheadline)
                        .foregroundColor(AppColors.textPrimary)
                    
                    HStack(spacing: AppSpacing.sm) {
                        ForEach([0.5, 1.0, 2.0, 5.0], id: \.self) { increment in
                            Button(action: {
                                viewModel.settings.autoBidIncrement = increment
                            }) {
                                Text("+₹\(increment)")
                                    .font(AppFonts.caption)
                                    .fontWeight(.semibold)
                                    .foregroundColor(
                                        viewModel.settings.autoBidIncrement == increment 
                                        ? .white 
                                        : AppColors.textPrimary
                                    )
                                    .padding(.horizontal, AppSpacing.md)
                                    .padding(.vertical, AppSpacing.sm)
                                    .background(
                                        viewModel.settings.autoBidIncrement == increment 
                                        ? AppColors.primary 
                                        : AppColors.surface
                                    )
                                    .cornerRadius(AppCornerRadius.small)
                            }
                        }
                    }
                }
                .padding(AppSpacing.sm)
                .background(AppColors.primary.opacity(0.1))
                .cornerRadius(AppCornerRadius.small)
            }
        }
        .padding(AppSpacing.md)
        .background(AppColors.card)
        .cornerRadius(AppCornerRadius.medium)
    }
}

// MARK: - Supporting Views

struct FavoritePlayerChip: View {
    let player: Player
    let onRemove: () -> Void
    
    var body: some View {
        HStack(spacing: AppSpacing.xs) {
            Text(player.name)
                .font(AppFonts.caption)
                .fontWeight(.semibold)
                .foregroundColor(AppColors.textPrimary)
            
            Button(action: onRemove) {
                Image(systemName: "xmark.circle.fill")
                    .font(.system(size: 14))
                    .foregroundColor(AppColors.textMuted)
            }
        }
        .padding(.horizontal, AppSpacing.sm)
        .padding(.vertical, AppSpacing.xs)
        .background(AppColors.surface)
        .cornerRadius(AppCornerRadius.small)
    }
}

struct RoleChip: View {
    let role: Player.PlayerRole
    let isSelected: Bool
    let onTap: () -> Void
    
    var body: some View {
        Button(action: onTap) {
            Text(role.displayName)
                .font(AppFonts.caption)
                .fontWeight(.semibold)
                .foregroundColor(isSelected ? .white : AppColors.textPrimary)
                .padding(.horizontal, AppSpacing.md)
                .padding(.vertical, AppSpacing.sm)
                .background(isSelected ? AppColors.primary : AppColors.surface)
                .cornerRadius(AppCornerRadius.small)
        }
    }
}

// MARK: - Preview

#Preview {
    AutoPickSettingsView(leagueId: "test", leagueName: "Test League")
}
