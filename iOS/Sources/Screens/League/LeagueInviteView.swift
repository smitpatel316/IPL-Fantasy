import SwiftUI

// MARK: - League Invite View
struct LeagueInviteView: View {
    let league: League
    @Environment(\.dismiss) var dismiss
    @State private var copied = false
    
    var body: some View {
        NavigationStack {
            ZStack {
                AppColors.background
                    .ignoresSafeArea()
                
                VStack(spacing: AppSpacing.xl) {
                    // League Icon
                    ZStack {
                        Circle()
                            .fill(AppColors.primary.opacity(0.2))
                            .frame(width: 80, height: 80)
                        
                        Text(String(league.name.prefix(1)))
                            .font(.system(size: 32, weight: .bold))
                            .foregroundColor(AppColors.primary)
                    }
                    .padding(.top, AppSpacing.xl)
                    
                    // Title
                    Text("Invite Players")
                        .font(AppFonts.title)
                        .fontWeight(.bold)
                        .foregroundColor(AppColors.textPrimary)
                    
                    Text("Share this code with your friends to join \(league.name)")
                        .font(AppFonts.body)
                        .foregroundColor(AppColors.textSecondary)
                        .multilineTextAlignment(.center)
                        .padding(.horizontal)
                    
                    // League Code Card
                    VStack(spacing: AppSpacing.md) {
                        Text("LEAGUE CODE")
                            .font(AppFonts.caption)
                            .foregroundColor(AppColors.textMuted)
                            .tracking(2)
                        
                        Text(league.code)
                            .font(.system(size: 40, weight: .bold, design: .monospaced))
                            .foregroundColor(AppColors.accent)
                            .tracking(4)
                        
                        // Copy Button
                        Button(action: copyCode) {
                            HStack {
                                Image(systemName: copied ? "checkmark" : "doc.on.doc")
                                Text(copied ? "Copied!" : "Copy Code")
                            }
                            .font(AppFonts.subheadline)
                            .fontWeight(.semibold)
                            .foregroundColor(copied ? AppColors.success : AppColors.primary)
                            .padding(.horizontal, AppSpacing.lg)
                            .padding(.vertical, AppSpacing.sm)
                            .background(
                                RoundedRectangle(cornerRadius: AppCornerRadius.medium)
                                    .stroke(copied ? AppColors.success : AppColors.primary, lineWidth: 2)
                            )
                        }
                    }
                    .padding(AppSpacing.xl)
                    .background(AppColors.card)
                    .cornerRadius(AppCornerRadius.large)
                    .padding(.horizontal)
                    
                    // Share Button
                    ShareLink(
                        item: shareText,
                        subject: Text("Join my IPL Fantasy League!"),
                        message: Text(shareText)
                    ) {
                        HStack {
                            Image(systemName: "square.and.arrow.up")
                            Text("Share Invite")
                        }
                        .font(AppFonts.subheadline)
                        .fontWeight(.semibold)
                        .foregroundColor(.white)
                        .frame(maxWidth: .infinity)
                        .padding(.vertical, AppSpacing.md)
                        .background(AppColors.primary)
                        .cornerRadius(AppCornerRadius.medium)
                    }
                    .padding(.horizontal)
                    
                    // QR Code Section
                    VStack(spacing: AppSpacing.md) {
                        Text("Or scan to join")
                            .font(AppFonts.caption)
                            .foregroundColor(AppColors.textMuted)
                        
                        // Mock QR Code placeholder
                        QRCodeView(code: league.code)
                            .frame(width: 150, height: 150)
                    }
                    .padding()
                    
                    Spacer()
                }
            }
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .navigationBarTrailing) {
                    Button("Done") {
                        dismiss()
                    }
                    .foregroundColor(AppColors.primary)
                }
            }
        }
    }
    
    private var shareText: String {
        "Join my IPL Fantasy League! 🎯\n\nLeague: \(league.name)\nCode: \(league.code)\n\nDownload IPL Fantasy Pro and enter this code to join my league!"
    }
    
    private func copyCode() {
        UIPasteboard.general.string = league.code
        copied = true
        
        // Reset after 2 seconds
        DispatchQueue.main.asyncAfter(deadline: .now() + 2) {
            copied = false
        }
    }
}

// MARK: - QR Code View
struct QRCodeView: View {
    let code: String
    
    var body: some View {
        ZStack {
            RoundedRectangle(cornerRadius: AppCornerRadius.medium)
                .fill(Color.white)
                .frame(width: 150, height: 150)
            
            // Generate QR pattern based on code
            QRCodePattern(code: code)
                .frame(width: 120, height: 120)
        }
        .shadow(color: AppColors.textMuted.opacity(0.2), radius: 8, x: 0, y: 4)
    }
}

// MARK: - QR Code Pattern Generator
struct QRCodePattern: View {
    let code: String
    
    var body: some View {
        Canvas { context, size in
            let gridSize = 21
            let cellSize = size.width / CGFloat(gridSize)
            
            // Generate pseudo-random pattern from code
            let codeHash = code.hashValue
            var random = SeededRandomGenerator(seed: UInt64(bitPattern: Int64(codeHash)))
            
            // Draw finder patterns (corners)
            drawFinderPattern(context: context, size: size, cellSize: cellSize, position: CGPoint(x: 0, y: 0))
            drawFinderPattern(context: context, size: size, cellSize: cellSize, position: CGPoint(x: size.width - 7 * cellSize, y: 0))
            drawFinderPattern(context: context, size: size, cellSize: cellSize, position: CGPoint(x: 0, y: size.height - 7 * cellSize))
            
            // Draw data pattern
            for row in 0..<gridSize {
                for col in 0..<gridSize {
                    // Skip finder pattern areas
                    if isFinderPatternArea(row: row, col: col) { continue }
                    
                    if random.nextBool() {
                        let rect = CGRect(
                            x: CGFloat(col) * cellSize,
                            y: CGFloat(row) * cellSize,
                            width: cellSize - 1,
                            height: cellSize - 1
                        )
                        context.fill(Path(rect), with: .color(.black))
                    }
                }
            }
        }
    }
    
    private func drawFinderPattern(context: GraphicsContext, size: CGSize, cellSize: CGFloat, position: CGPoint) {
        // Outer square
        let outerPath = Path { path in
            path.addRect(CGRect(x: position.x, y: position.y, width: 7 * cellSize, height: 7 * cellSize))
        }
        context.stroke(outerPath, with: .color(.black), lineWidth: cellSize)
        
        // Inner square
        let innerPath = Path { path in
            path.addRect(CGRect(x: position.x + cellSize * 2, y: position.y + cellSize * 2, width: 3 * cellSize, height: 3 * cellSize))
        }
        context.fill(innerPath, with: .color(.black))
    }
    
    private func isFinderPatternArea(row: Int, col: Int) -> Bool {
        // Top-left finder
        if row < 8 && col < 8 { return true }
        // Top-right finder
        if row < 8 && col > 12 { return true }
        // Bottom-left finder
        if row > 12 && col < 8 { return true }
        return false
    }
}

// MARK: - Seeded Random Generator
struct SeededRandomGenerator: RandomNumberGenerator {
    var state: UInt64
    
    init(seed: UInt64) {
        state = seed
    }
    
    mutating func next() -> UInt64 {
        state = state &* 6364136223846793005 &+ 1442695040888963407
        return state
    }
    
    func nextBool() -> Bool {
        return next() % 2 == 0
    }
}
