import SwiftUI

// MARK: - Draft Room View
struct DraftRoomView: View {
    @StateObject private var viewModel = DraftViewModel()
    @State private var showingBidSheet = false
    @State private var bidAmount: Double = 0
    @State private var selectedDraftType: DraftType = .auction
    @State private var showingDraftTypePicker = false
    let leagueId: String

    init(leagueId: String = "") {
        self.leagueId = leagueId
    }

    init() {
        self.leagueId = ""
    }
    
    var body: some View {
        NavigationStack {
            ZStack {
                AppColors.background
                    .ignoresSafeArea()
                
                VStack(spacing: 0) {
                    // Draft Type Selector
                    draftTypeSelector
                    
                    // Show appropriate draft view based on type
                    if viewModel.isSnakeDraft() {
                        SnakeDraftContent(viewModel: viewModel, leagueId: leagueId, bidAmount: $bidAmount, showingBidSheet: $showingBidSheet)
                    } else {
                        AuctionDraftContent(viewModel: viewModel, bidAmount: $bidAmount, showingBidSheet: $showingBidSheet)
                    }
                }
            }
            .navigationTitle("Draft Room")
            .navigationBarTitleDisplayMode(.large)
            .toolbar {
                ToolbarItem(placement: .navigationBarTrailing) {
                    Menu {
                        Button("Auction Draft") {
                            viewModel.startDraft(members: [], type: .auction, leagueId: leagueId)
                        }
                        Button("Snake Draft") {
                            viewModel.startDraft(members: [], type: .snake, leagueId: leagueId)
                        }
                        Divider()
                        if viewModel.isDraftActive {
                            Button("End Draft", role: .destructive) {
                                viewModel.stopDraft()
                            }
                        }
                    } label: {
                        Image(systemName: "ellipsis.circle")
                    }
                }
            }
            .sheet(isPresented: $showingBidSheet) {
                BidSheet(amount: $bidAmount) {
                    // Place bid logic
                }
            }
        }
    }
    
    // MARK: - Draft Type Selector
    
    private var draftTypeSelector: some View {
        HStack(spacing: 0) {
            draftTypeButton(type: .auction, title: "Auction")
            draftTypeButton(type: .snake, title: "Snake")
        }
        .padding(AppSpacing.xs)
        .background(AppColors.surface)
    }
    
    private func draftTypeButton(type: DraftType, title: String) -> some View {
        Button(action: {
            showingDraftTypePicker = true
        }) {
            Text(title)
                .font(AppFonts.subheadline)
                .fontWeight(viewModel.draftType == type ? .semibold : .regular)
                .foregroundColor(viewModel.draftType == type ? AppColors.primary : AppColors.textMuted)
                .frame(maxWidth: .infinity)
                .padding(.vertical, AppSpacing.sm)
                .background(viewModel.draftType == type ? AppColors.primary.opacity(0.1) : Color.clear)
                .cornerRadius(AppCornerRadius.small)
        }
    }
}

// MARK: - Auction Draft Content

struct AuctionDraftContent: View {
    @ObservedObject var viewModel: DraftViewModel
    @Binding var bidAmount: Double
    @Binding var showingBidSheet: Bool
    
    var body: some View {
        VStack(spacing: 0) {
            // Current Player Auction
            if let player = viewModel.currentPlayer {
                AuctionPlayerCard(
                    player: player,
                    currentBid: viewModel.currentBid,
                    currentBidder: viewModel.currentBidder?.teamName,
                    timer: viewModel.draftTimer
                )
                .padding(AppSpacing.md)
                
                // Bid Controls
                bidControls
            } else {
                // No Active Draft
                noActiveDraft
            }
            
            // Bid History
            bidHistorySection
        }
    }
    
    private var bidControls: some View {
        VStack(spacing: AppSpacing.md) {
            // Quick Bid Buttons
            HStack(spacing: AppSpacing.sm) {
                ForEach([0.5, 1.0, 2.0], id: \.self) { increment in
                    Button(action: {
                        // Place bid logic
                    }) {
                        Text("+₹\(Int(increment))Cr")
                            .font(AppFonts.caption)
                            .fontWeight(.semibold)
                            .foregroundColor(AppColors.textPrimary)
                            .padding(.horizontal, AppSpacing.md)
                            .padding(.vertical, AppSpacing.sm)
                            .background(AppColors.surface)
                            .cornerRadius(AppCornerRadius.small)
                    }
                }
            }
            
            // Custom Bid
            HStack {
                TextField("Custom Bid", value: $bidAmount, format: .number)
                    .keyboardType(.decimalPad)
                    .textFieldStyle(RoundedBorderTextFieldStyle())
                    .frame(width: 100)
                
                Button("Place Bid") {
                    showingBidSheet = true
                }
                .buttonStyle(PrimaryButtonStyle())
            }
            
            // Admin Controls (Sold/Unsold)
            HStack(spacing: AppSpacing.md) {
                Button(action: { viewModel.markUnsold() }) {
                    Text("Unsold")
                        .font(AppFonts.subheadline)
                        .fontWeight(.semibold)
                        .foregroundColor(AppColors.error)
                        .frame(maxWidth: .infinity)
                        .padding(.vertical, AppSpacing.md)
                        .background(AppColors.error.opacity(0.1))
                        .cornerRadius(AppCornerRadius.medium)
                }
                
                Button(action: { viewModel.confirmSale() }) {
                    Text("Sold!")
                        .font(AppFonts.subheadline)
                        .fontWeight(.semibold)
                        .foregroundColor(.white)
                        .frame(maxWidth: .infinity)
                        .padding(.vertical, AppSpacing.md)
                        .background(AppColors.success)
                        .cornerRadius(AppCornerRadius.medium)
                }
                .disabled(viewModel.currentBidder == nil)
            }
        }
        .padding(AppSpacing.md)
        .background(AppColors.card)
    }
    
    private var noActiveDraft: some View {
        VStack(spacing: AppSpacing.lg) {
            Image(systemName: "hammer")
                .font(.system(size: 60))
                .foregroundColor(AppColors.textMuted)
            
            Text("No Active Draft")
                .font(AppFonts.title)
                .fontWeight(.bold)
                .foregroundColor(AppColors.textPrimary)
            
            Text("Start an auction draft from your league to begin bidding on players")
                .font(AppFonts.body)
                .foregroundColor(AppColors.textSecondary)
                .multilineTextAlignment(.center)
            
            Button(action: { viewModel.startDraft(members: [], type: .auction, leagueId: "") }) {
                Text("Start Auction Draft")
                    .font(AppFonts.subheadline)
                    .fontWeight(.semibold)
                    .foregroundColor(.white)
                    .padding(.horizontal, AppSpacing.xl)
                    .padding(.vertical, AppSpacing.md)
                    .background(AppColors.primary)
                    .cornerRadius(AppCornerRadius.medium)
            }
        }
        .padding(AppSpacing.xl)
    }
    
    private var bidHistorySection: some View {
        VStack(alignment: .leading, spacing: AppSpacing.md) {
            Text("Bid History")
                .font(AppFonts.headline)
                .foregroundColor(AppColors.textPrimary)
                .padding(.horizontal, AppSpacing.md)
            
            if viewModel.bidHistory.isEmpty {
                Text("No bids yet")
                    .font(AppFonts.body)
                    .foregroundColor(AppColors.textMuted)
                    .frame(maxWidth: .infinity)
                    .padding(AppSpacing.xl)
            } else {
                ScrollView {
                    LazyVStack(spacing: AppSpacing.sm) {
                        ForEach(viewModel.bidHistory) { entry in
                            BidHistoryRow(entry: entry)
                        }
                    }
                    .padding(.horizontal, AppSpacing.md)
                }
            }
        }
        .frame(maxHeight: .infinity)
        .background(AppColors.surface)
    }
}

// MARK: - Snake Draft Content

struct SnakeDraftContent: View {
    @ObservedObject var viewModel: DraftViewModel
    let leagueId: String
    @Binding var bidAmount: Double
    @Binding var showingBidSheet: Bool

    var body: some View {
        VStack {
            Text("Snake Draft")
                .font(AppFonts.headline)
            Text("Draft in progress...")
                .font(AppFonts.body)
        }
    }
}

// MARK: - Bid Sheet

struct BidSheet: View {
    @Binding var amount: Double
    let onSubmit: () -> Void
    
    @Environment(\.dismiss) private var dismiss
    
    var body: some View {
        NavigationStack {
            VStack(spacing: AppSpacing.lg) {
                TextField("Enter bid amount", value: $amount, format: .number)
                    .keyboardType(.decimalPad)
                    .textFieldStyle(RoundedBorderTextFieldStyle())
                    .padding(AppSpacing.md)
                
                Button("Place Bid") {
                    onSubmit()
                    dismiss()
                }
                .buttonStyle(PrimaryButtonStyle())
                
                Spacer()
            }
            .navigationTitle("Place Bid")
            .navigationBarTitleDisplayMode(.large)
            .toolbar {
                ToolbarItem(placement: .navigationBarLeading) {
                    Button("Cancel") {
                        dismiss()
                    }
                }
            }
        }
    }
}

// MARK: - Bid History Row

struct BidHistoryRow: View {
    let entry: BidHistoryEntry
    
    var body: some View {
        HStack {
            VStack(alignment: .leading, spacing: AppSpacing.xs) {
                Text(entry.playerName)
                    .font(AppFonts.subheadline)
                    .fontWeight(.semibold)
                    .foregroundColor(AppColors.textPrimary)
                
                Text(entry.soldTo)
                    .font(AppFonts.caption)
                    .foregroundColor(AppColors.textSecondary)
            }
            
            Spacer()
            
            Text("₹\(Int(entry.amount))Cr")
                .font(AppFonts.subheadline)
                .fontWeight(.bold)
                .foregroundColor(entry.amount > 0 ? AppColors.success : AppColors.error)
        }
        .padding(AppSpacing.md)
        .background(AppColors.card)
        .cornerRadius(AppCornerRadius.small)
    }
}

// MARK: - Primary Button Style

struct PrimaryButtonStyle: ButtonStyle {
    func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .font(AppFonts.subheadline)
            .fontWeight(.semibold)
            .foregroundColor(.white)
            .padding(.horizontal, AppSpacing.lg)
            .padding(.vertical, AppSpacing.md)
            .background(configuration.isPressed ? AppColors.primary.opacity(0.8) : AppColors.primary)
            .cornerRadius(AppCornerRadius.medium)
    }
}
