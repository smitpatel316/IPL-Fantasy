import SwiftUI

// MARK: - Player Search View
struct PlayerSearchView: View {
    @StateObject private var viewModel = PlayerSearchViewModel()
    @Environment(\.dismiss) var dismiss
    
    var body: some View {
        NavigationStack {
            ZStack {
                AppColors.background
                    .ignoresSafeArea()
                
                VStack(spacing: 0) {
                    // Search Bar
                    searchBar
                    
                    // Filters
                    filterSection
                    
                    // Results
                    if viewModel.isLoading {
                        Spacer()
                        ProgressView()
                            .progressViewStyle(CircularProgressViewStyle(tint: AppColors.primary))
                        Spacer()
                    } else if viewModel.players.isEmpty {
                        emptyState
                    } else {
                        playerList
                    }
                }
            }
            .navigationTitle("Players")
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
                viewModel.loadPlayers()
            }
        }
    }
    
    private var searchBar: some View {
        HStack(spacing: AppSpacing.md) {
            Image(systemName: "magnifyingglass")
                .foregroundColor(AppColors.textMuted)
            
            TextField("Search players...", text: $viewModel.searchText)
                .foregroundColor(AppColors.textPrimary)
                .autocorrectionDisabled()
                .onChange(of: viewModel.searchText) { _, _ in
                    viewModel.search()
                }
            
            if !viewModel.searchText.isEmpty {
                Button(action: { viewModel.searchText = "" }) {
                    Image(systemName: "xmark.circle.fill")
                        .foregroundColor(AppColors.textMuted)
                }
            }
        }
        .padding(AppSpacing.md)
        .background(AppColors.surface)
        .cornerRadius(AppCornerRadius.medium)
        .padding(AppSpacing.md)
    }
    
    private var filterSection: some View {
        ScrollView(.horizontal, showsIndicators: false) {
            HStack(spacing: AppSpacing.sm) {
                // Team Filter
                Menu {
                    Button("All Teams") { viewModel.selectedTeam = nil }
                    ForEach(viewModel.teams, id: \.self) { team in
                        Button(team) { viewModel.selectedTeam = team }
                    }
                } label: {
                    FilterChip(
                        text: viewModel.selectedTeam ?? "Team",
                        isSelected: viewModel.selectedTeam != nil
                    )
                }
                
                // Role Filter
                Menu {
                    Button("All Roles") { viewModel.selectedRole = nil }
                    ForEach(viewModel.roles, id: \.self) { role in
                        Button(role.capitalized) { viewModel.selectedRole = role }
                    }
                } label: {
                    FilterChip(
                        text: viewModel.selectedRole?.capitalized ?? "Role",
                        isSelected: viewModel.selectedRole != nil
                    )
                }
                
                // Sort
                Menu {
                    Button("Price: High to Low") { viewModel.sortBy = .priceDesc }
                    Button("Price: Low to High") { viewModel.sortBy = .priceAsc }
                    Button("Name: A-Z") { viewModel.sortBy = .nameAsc }
                    Button("Name: Z-A") { viewModel.sortBy = .nameDesc }
                } label: {
                    FilterChip(text: "Sort", isSelected: false, icon: "arrow.up.arrow.down")
                }
            }
            .padding(.horizontal, AppSpacing.md)
            .padding(.bottom, AppSpacing.sm)
        }
        .padding(.bottom, AppSpacing.sm)
        .background(AppColors.card)
    }
    
    private var playerList: some View {
        ScrollView {
            LazyVStack(spacing: AppSpacing.sm) {
                ForEach(viewModel.players) { player in
                    PlayerSearchRow(player: player) {
                        // Player selected callback
                        dismiss()
                    }
                }
            }
            .padding(AppSpacing.md)
        }
    }
    
    private var emptyState: some View {
        VStack(spacing: AppSpacing.md) {
            Image(systemName: "magnifyingglass")
                .font(.system(size: 48))
                .foregroundColor(AppColors.textMuted)
            
            Text("No players found")
                .font(AppFonts.headline)
                .foregroundColor(AppColors.textPrimary)
            
            Text("Try adjusting your filters")
                .font(AppFonts.body)
                .foregroundColor(AppColors.textSecondary)
        }
        .frame(maxHeight: .infinity)
    }
}

// MARK: - Filter Chip
struct FilterChip: View {
    let text: String
    var isSelected: Bool = true
    var icon: String? = nil
    
    var body: some View {
        HStack(spacing: AppSpacing.xs) {
            if let icon = icon {
                Image(systemName: icon)
                    .font(AppFonts.caption)
            }
            Text(text)
                .font(AppFonts.caption)
        }
        .padding(.horizontal, AppSpacing.md)
        .padding(.vertical, AppSpacing.sm)
        .background(isSelected ? AppColors.primary.opacity(0.2) : AppColors.surface)
        .foregroundColor(isSelected ? AppColors.primary : AppColors.textSecondary)
        .cornerRadius(AppCornerRadius.large)
        .overlay(
            RoundedRectangle(cornerRadius: AppCornerRadius.large)
                .stroke(isSelected ? AppColors.primary : AppColors.textMuted.opacity(0.3), lineWidth: 1)
        )
    }
}

// MARK: - Player Search Row
struct PlayerSearchRow: View {
    let player: Player
    let onTap: () -> Void
    
    var body: some View {
        Button(action: onTap) {
            HStack(spacing: AppSpacing.md) {
                // Avatar
                ZStack {
                    Circle()
                        .fill(roleColor.opacity(0.2))
                        .frame(width: 50, height: 50)
                    Text(initials)
                        .font(AppFonts.subheadline)
                        .fontWeight(.bold)
                        .foregroundColor(roleColor)
                }
                
                // Info
                VStack(alignment: .leading, spacing: AppSpacing.xs) {
                    Text(player.name)
                        .font(AppFonts.subheadline)
                        .fontWeight(.semibold)
                        .foregroundColor(AppColors.textPrimary)
                    
                    HStack(spacing: AppSpacing.sm) {
                        Text(player.team)
                            .font(AppFonts.caption)
                            .foregroundColor(AppColors.textSecondary)
                        
                        Text("•")
                            .foregroundColor(AppColors.textMuted)
                        
                        Text(player.role.displayName)
                            .font(AppFonts.caption)
                            .foregroundColor(roleColor)
                        
                        if player.isOverseas {
                            Text("🌍")
                                .font(AppFonts.caption)
                        }
                    }
                }
                
                Spacer()
                
                // Price
                VStack(alignment: .trailing, spacing: AppSpacing.xs) {
                    Text("₹\(Int(player.basePrice))Cr")
                        .font(AppFonts.subheadline)
                        .fontWeight(.bold)
                        .foregroundColor(AppColors.accent)
                }
            }
            .padding(AppSpacing.md)
            .background(AppColors.card)
            .cornerRadius(AppCornerRadius.medium)
        }
        .buttonStyle(PlainButtonStyle())
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

// MARK: - Player Search View Model
@MainActor
class PlayerSearchViewModel: ObservableObject {
    @Published var players: [Player] = []
    @Published var searchText = ""
    @Published var selectedTeam: String? = nil
    @Published var selectedRole: String? = nil
    @Published var sortBy: SortOption = .priceDesc
    @Published var isLoading = false
    
    let teams = ["MI", "CSK", "RCB", "KKR", "DC", "LSG", "GT", "RR", "SRH"]
    let roles = ["batsman", "bowler", "allrounder", "wicketkeeper"]
    
    enum SortOption {
        case priceDesc, priceAsc, nameAsc, nameDesc
    }
    
    init() {
        loadMockPlayers()
    }
    
    func loadPlayers() {
        isLoading = true
        // Simulate API call
        DispatchQueue.main.asyncAfter(deadline: .now() + 0.5) {
            self.loadMockPlayers()
            self.isLoading = false
        }
    }
    
    func search() {
        var filtered = allPlayers
        
        // Search
        if !searchText.isEmpty {
            filtered = filtered.filter { $0.name.localizedCaseInsensitiveContains(searchText) }
        }
        
        // Team filter
        if let team = selectedTeam {
            filtered = filtered.filter { $0.team == team }
        }
        
        // Role filter
        if let role = selectedRole {
            filtered = filtered.filter { $0.role.rawValue == role }
        }
        
        // Sort
        switch sortBy {
        case .priceDesc:
            filtered.sort { $0.basePrice > $1.basePrice }
        case .priceAsc:
            filtered.sort { $0.basePrice < $1.basePrice }
        case .nameAsc:
            filtered.sort { $0.name < $1.name }
        case .nameDesc:
            filtered.sort { $0.name > $1.name }
        }
        
        players = filtered
    }
    
    private var allPlayers: [Player] = []
    
    private func loadMockPlayers() {
        allPlayers = [
            // Mumbai Indians
            Player(name: "Rohit Sharma", role: .batsman, team: "MI", basePrice: 18),
            Player(name: "Jasprit Bumrah", role: .bowler, team: "MI", basePrice: 18),
            Player(name: "Hardik Pandya", role: .allRounder, team: "MI", basePrice: 16),
            Player(name: "Suryakumar Yadav", role: .batsman, team: "MI", basePrice: 14),
            Player(name: "Ishan Kishan", role: .wicketKeeper, team: "MI", basePrice: 12),
            Player(name: "Tilak Varma", role: .batsman, team: "MI", basePrice: 8),
            
            // Chennai Super Kings
            Player(name: "MS Dhoni", role: .wicketKeeper, team: "CSK", basePrice: 12),
            Player(name: "Ruturaj Gaikwad", role: .batsman, team: "CSK", basePrice: 12),
            Player(name: "Ravindra Jadeja", role: .allRounder, team: "CSK", basePrice: 14),
            Player(name: "Deepak Chahar", role: .bowler, team: "CSK", basePrice: 8),
            
            // RCB
            Player(name: "Virat Kohli", role: .batsman, team: "RCB", basePrice: 18),
            Player(name: "Faf du Plessis", role: .batsman, team: "RCB", basePrice: 12, isOverseas: true),
            Player(name: "Mohammed Siraj", role: .bowler, team: "RCB", basePrice: 10),
            Player(name: "Glenn Maxwell", role: .allRounder, team: "RCB", basePrice: 12, isOverseas: true),
            
            // KKR
            Player(name: "Shreyas Iyer", role: .batsman, team: "KKR", basePrice: 12),
            Player(name: "Andre Russell", role: .allRounder, team: "KKR", basePrice: 12, isOverseas: true),
            Player(name: "Sunil Narine", role: .allRounder, team: "KKR", basePrice: 10, isOverseas: true),
            
            // DC
            Player(name: "Rishabh Pant", role: .wicketKeeper, team: "DC", basePrice: 14),
            Player(name: "David Warner", role: .batsman, team: "DC", basePrice: 12, isOverseas: true),
            Player(name: "Axar Patel", role: .allRounder, team: "DC", basePrice: 10),
            Player(name: "Kuldeep Yadav", role: .bowler, team: "DC", basePrice: 10),
            
            // LSG
            Player(name: "KL Rahul", role: .wicketKeeper, team: "LSG", basePrice: 14),
            Player(name: "Mohammed Shami", role: .bowler, team: "LSG", basePrice: 14),
            Player(name: "Nicholas Pooran", role: .batsman, team: "LSG", basePrice: 10, isOverseas: true),
            
            // GT
            Player(name: "Shubman Gill", role: .batsman, team: "GT", basePrice: 16),
            Player(name: "Rashid Khan", role: .bowler, team: "GT", basePrice: 14, isOverseas: true),
            Player(name: "Hardik Pandya", role: .allRounder, team: "GT", basePrice: 16),
            
            // RR
            Player(name: "Sanju Samson", role: .wicketKeeper, team: "RR", basePrice: 10),
            Player(name: "Yashasvi Jaiswal", role: .batsman, team: "RR", basePrice: 10),
            Player(name: "Ravichandran Ashwin", role: .allRounder, team: "RR", basePrice: 12),
            Player(name: "Yuzvendra Chahal", role: .bowler, team: "RR", basePrice: 10),
            
            // SRH
            Player(name: "Aiden Markram", role: .batsman, team: "SRH", basePrice: 10, isOverseas: true),
            Player(name: "Bhuvneshwar Kumar", role: .bowler, team: "SRH", basePrice: 12),
            Player(name: "T Natarajan", role: .bowler, team: "SRH", basePrice: 8),
        ]
        
        search()
    }
}
