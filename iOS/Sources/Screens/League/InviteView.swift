import SwiftUI

// MARK: - Invite View
struct InviteView: View {
    let league: League
    @State private var copied = false
    @Environment(\.dismiss) var dismiss
    
    var body: some View {
        NavigationStack {
            ZStack {
                AppColors.background
                    .ignoresSafeArea()
                
                ScrollView {
                    VStack(spacing: AppSpacing.xl) {
                        // League Icon
                        ZStack {
                            Circle()
                                .fill(AppColors.primary.opacity(0.2))
                                .frame(width: 100, height: 100)
                            
                            Text(String(league.name.prefix(1)))
                                .font(.system(size: 40, weight: .bold))
                                .foregroundColor(AppColors.primary)
                        }
                        .padding(.top, AppSpacing.xl)
                        
                        // Title
                        Text("Invite Friends")
                            .font(AppFonts.title)
                            .fontWeight(.bold)
                            .foregroundColor(AppColors.textPrimary)
                        
                        Text("Share this code with your friends to join \(league.name)")
                            .font(AppFonts.body)
                            .foregroundColor(AppColors.textSecondary)
                            .multilineTextAlignment(.center)
                            .padding(.horizontal, AppSpacing.lg)
                        
                        // Code Card
                        codeCard
                        
                        // Share Options
                        shareOptions
                        
                        // Pending Invites
                        pendingInvites
                        
                        Spacer()
                    }
                }
            }
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .navigationBarTrailing) {
                    Button("Done") { dismiss() }
                        .foregroundColor(AppColors.primary)
                }
            }
        }
    }
    
    private var codeCard: some View {
        VStack(spacing: AppSpacing.md) {
            Text("League Code")
                .font(AppFonts.caption)
                .foregroundColor(AppColors.textSecondary)
            
            HStack(spacing: AppSpacing.sm) {
                Text(league.code)
                    .font(.system(size: 36, weight: .bold, design: .monospaced))
                    .foregroundColor(AppColors.accent)
                    .tracking(8)
                
                Button(action: copyCode) {
                    Image(systemName: copied ? "checkmark" : "doc.on.doc")
                        .font(.system(size: 20))
                        .foregroundColor(copied ? AppColors.success : AppColors.primary)
                }
            }
            
            Text(copied ? "Copied to clipboard!" : "Tap to copy")
                .font(AppFonts.caption)
                .foregroundColor(copied ? AppColors.success : AppColors.textMuted)
        }
        .padding(AppSpacing.xl)
        .background(AppColors.card)
        .cornerRadius(AppCornerRadius.card)
        .padding(.horizontal, AppSpacing.lg)
    }
    
    private var shareOptions: some View {
        VStack(spacing: AppSpacing.md) {
            Text("Share via")
                .font(AppFonts.headline)
                .foregroundColor(AppColors.textPrimary)
                .frame(maxWidth: .infinity, alignment: .leading)
            
            HStack(spacing: AppSpacing.md) {
                ShareButton(icon: "message.fill", name: "Message", color: .green) {
                    // Share via message
                }
                
                ShareButton(icon: "whatsapp", name: "WhatsApp", color: .green) {
                    // Share via WhatsApp
                }
                
                ShareButton(icon: "link", name: "Copy Link", color: AppColors.primary) {
                    copyCode()
                }
                
                ShareButton(icon: "square.and.arrow.up", name: "More", color: AppColors.textSecondary) {
                    // System share sheet
                }
            }
        }
        .padding(.horizontal, AppSpacing.lg)
    }
    
    private var pendingInvites: some View {
        VStack(spacing: AppSpacing.md) {
            Text("Pending Invites")
                .font(AppFonts.headline)
                .foregroundColor(AppColors.textPrimary)
                .frame(maxWidth: .infinity, alignment: .leading)
            
            // Mock pending invites
            VStack(spacing: AppSpacing.sm) {
                InviteRow(email: "friend1@email.com", status: .pending)
                InviteRow(email: "friend2@email.com", status: .pending)
            }
        }
        .padding(.horizontal, AppSpacing.lg)
    }
    
    private func copyCode() {
        UIPasteboard.general.string = league.code
        copied = true
        
        DispatchQueue.main.asyncAfter(deadline: .now() + 2) {
            copied = false
        }
    }
}

// MARK: - Share Button
struct ShareButton: View {
    let icon: String
    let name: String
    let color: Color
    let action: () -> Void
    
    var body: some View {
        Button(action: action) {
            VStack(spacing: AppSpacing.sm) {
                Image(systemName: icon)
                    .font(.system(size: 24))
                    .foregroundColor(color)
                    .frame(width: 50, height: 50)
                    .background(color.opacity(0.1))
                    .cornerRadius(12)
                
                Text(name)
                    .font(AppFonts.caption)
                    .foregroundColor(AppColors.textSecondary)
            }
        }
    }
}

// MARK: - Invite Row
struct InviteRow: View {
    let email: String
    let status: InviteStatus
    
    enum InviteStatus {
        case pending, accepted
    }
    
    var body: some View {
        HStack {
            Image(systemName: "envelope")
                .foregroundColor(AppColors.textMuted)
            
            Text(email)
                .font(AppFonts.body)
                .foregroundColor(AppColors.textPrimary)
            
            Spacer()
            
            Text(status == .pending ? "Pending" : "Accepted")
                .font(AppFonts.caption)
                .foregroundColor(status == .pending ? AppColors.warning : AppColors.success)
        }
        .padding(AppSpacing.md)
        .background(AppColors.card)
        .cornerRadius(AppCornerRadius.medium)
    }
}
