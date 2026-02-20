import SwiftUI

// MARK: - Draft Room View
struct DraftRoomView: View {
    @StateObject private var viewModel = DraftViewModel()
    @State private var showingBidSheet = false
    @State private var bidAmount: Double = 0
    
    var body: some View {
        NavigationStack {
            ZStack {
                AppColors.background
                    .ignoresSafeArea()
                
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
            .navigationTitle("Auction Draft")
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
        }
    }
    
    private var bidControls: some View {
        VStack(spacing: AppSpacing.md) {
            // Quick Bid Buttons
            HStack(spacing: AppSpacing.sm) {
                ForEach([0.5, 1.0, 2.0], id: \.self) { increment in
                    Button(action: {
                        viewModel.placeBid(amount: viewModel.currentBid + increment)
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
                    viewModel.placeBid(amount: bidAmount)
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
            
            Text("Start a draft from your league to begin bidding on players")
                .font(AppFonts.body)
                .foregroundColor(AppColors.textSecondary)
                .multilineTextAlignment(.center)
            
            Button(action: { viewModel.startDraft(members: []) }) {
                Text("Start Demo Draft")
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
