import SwiftUI

// MARK: - Player Card
struct PlayerCard: View {
    let player: Player
    var showPrice: Bool = true
    var isSelectable: Bool = false
    var isSelected: Bool = false
    var onTap: (() -> Void)?
    
    var body: some View {
        Button(action: { onTap?() }) {
            HStack(spacing: AppSpacing.md) {
                // Player Avatar
                ZStack {
                    Circle()
                        .fill(roleColor.opacity(0.2))
                        .frame(width: 50, height: 50)
                    
                    Text(initials)
                        .font(AppFonts.subheadline)
                        .fontWeight(.bold)
                        .foregroundColor(roleColor)
                }
                
                // Player Info
                VStack(alignment: .leading, spacing: AppSpacing.xs) {
                    Text(player.name)
                        .font(AppFonts.subheadline)
                        .fontWeight(.semibold)
                        .foregroundColor(AppColors.textPrimary)
                        .lineLimit(1)
                    
                    HStack(spacing: AppSpacing.sm) {
                        Text(player.role.displayName)
                            .font(AppFonts.caption)
                            .foregroundColor(roleColor)
                        
                        Text("•")
                            .foregroundColor(AppColors.textMuted)
                        
                        Text(player.team)
                            .font(AppFonts.caption)
                            .foregroundColor(AppColors.textSecondary)
                    }
                }
                
                Spacer()
                
                // Price/Status
                if showPrice {
                    VStack(alignment: .trailing, spacing: AppSpacing.xs) {
                        Text("₹\(player.basePrice, specifier: "%.1f")Cr")
                            .font(AppFonts.subheadline)
                            .fontWeight(.bold)
                            .foregroundColor(AppColors.accent)
                        
                        if player.isSold {
                            Text("SOLD")
                                .font(AppFonts.small)
                                .fontWeight(.bold)
                                .foregroundColor(AppColors.success)
                        } else {
                            Text("Available")
                                .font(AppFonts.small)
                                .foregroundColor(AppColors.textMuted)
                        }
                    }
                }
            }
            .padding(AppSpacing.md)
            .background(
                RoundedRectangle(cornerRadius: AppCornerRadius.medium)
                    .fill(isSelected ? AppColors.primary.opacity(0.15) : AppColors.card)
            )
            .overlay(
                RoundedRectangle(cornerRadius: AppCornerRadius.medium)
                    .stroke(isSelected ? AppColors.primary : Color.clear, lineWidth: 2)
            )
        }
        .buttonStyle(PlainButtonStyle())
        .disabled(!isSelectable)
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

// MARK: - Auction Player Card (larger)
struct AuctionPlayerCard: View {
    let player: Player
    let currentBid: Double
    let currentBidder: String?
    let timer: Int
    
    var body: some View {
        VStack(spacing: AppSpacing.md) {
            // Timer
            HStack {
                Image(systemName: "timer")
                    .foregroundColor(timer < 10 ? AppColors.error : AppColors.accent)
                
                Text("\(timer)s")
                    .font(AppFonts.headline)
                    .fontWeight(.bold)
                    .foregroundColor(timer < 10 ? AppColors.error : AppColors.textPrimary)
            }
            
            // Player Large Avatar
            ZStack {
                Circle()
                    .fill(roleColor.opacity(0.2))
                    .frame(width: 100, height: 100)
                
                Text(initials)
                    .font(.system(size: 36, weight: .bold))
                    .foregroundColor(roleColor)
            }
            
            // Player Details
            Text(player.name)
                .font(AppFonts.title)
                .fontWeight(.bold)
                .foregroundColor(AppColors.textPrimary)
            
            HStack(spacing: AppSpacing.md) {
                Text(player.role.displayName)
                    .font(AppFonts.body)
                    .foregroundColor(roleColor)
                
                Text("|")
                    .foregroundColor(AppColors.textMuted)
                
                Text(player.team)
                    .font(AppFonts.body)
                    .foregroundColor(AppColors.textSecondary)
            }
            
            // Base Price
            Text("Base Price: ₹\(player.basePrice, specifier: "%.1f")Cr")
                .font(AppFonts.caption)
                .foregroundColor(AppColors.textMuted)
            
            Divider()
                .background(AppColors.textMuted)
            
            // Current Bid
            VStack(spacing: AppSpacing.sm) {
                Text("Current Bid")
                    .font(AppFonts.caption)
                    .foregroundColor(AppColors.textSecondary)
                
                Text("₹\(currentBid, specifier: "%.1f")Cr")
                    .font(.system(size: 40, weight: .bold))
                    .foregroundColor(AppColors.accent)
                
                if let bidder = currentBidder {
                    Text("by \(bidder)")
                        .font(AppFonts.subheadline)
                        .foregroundColor(AppColors.success)
                }
            }
        }
        .padding(AppSpacing.lg)
        .background(AppColors.card)
        .cornerRadius(AppCornerRadius.card)
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

// MARK: - Preview
struct PlayerCard_Previews: PreviewProvider {
    static var previews: some View {
        VStack {
            PlayerCard(player: Player(name: "Virat Kohli", role: .batsman, team: "RCB", basePrice: 18))
            PlayerCard(player: Player(name: "Jasprit Bumrah", role: .bowler, team: "MI", basePrice: 18, isSold: true))
        }
        .padding()
        .background(AppColors.background)
    }
}
