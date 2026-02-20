import SwiftUI

// MARK: - Theme Colors
struct AppColors {
    // Primary Colors - IPL inspired
    static let primary = Color(hex: "E31E24")  // IPL Red
    static let secondary = Color(hex: "1E3A5F")  // Deep Blue
    static let accent = Color(hex: "FFB81C")  // Gold/Yellow
    
    // Backgrounds
    static let background = Color(hex: "121212")
    static let surface = Color(hex: "1E1E1E")
    static let card = Color(hex: "2C2C2C")
    
    // Text
    static let textPrimary = Color.white
    static let textSecondary = Color.gray
    static let textMuted = Color(hex: "888888")
    
    // Status
    static let success = Color.green
    static let warning = Color.orange
    static let error = Color.red
    
    // Player Roles
    static let batsman = Color(hex: "4CAF50")
    static let bowler = Color(hex: "F44336")
    static let allRounder = Color(hex: "9C27B0")
    static let wicketKeeper = Color(hex: "2196F3")
}

// MARK: - Theme Spacing
struct AppSpacing {
    static let xs: CGFloat = 4
    static let sm: CGFloat = 8
    static let md: CGFloat = 16
    static let lg: CGFloat = 24
    static let xl: CGFloat = 32
    static let xxl: CGFloat = 48
}

// MARK: - Theme Corner Radius
struct AppCornerRadius {
    static let small: CGFloat = 8
    static let medium: CGFloat = 12
    static let large: CGFloat = 16
    static let card: CGFloat = 20
}

// MARK: - Font Styles
struct AppFonts {
    static let title = Font.system(size: 28, weight: .bold, design: .default)
    static let headline = Font.system(size: 22, weight: .semibold)
    static let subheadline = Font.system(size: 18, weight: .medium)
    static let body = Font.system(size: 16, weight: .regular)
    static let caption = Font.system(size: 14, weight: .regular)
    static let small = Font.system(size: 12, weight: .light)
}

// MARK: - Color Extension
extension Color {
    init(hex: String) {
        let hex = hex.trimmingCharacters(in: CharacterSet.alphanumerics.inverted)
        var int: UInt64 = 0
        Scanner(string: hex).scanHexInt64(&int)
        let a, r, g, b: UInt64
        switch hex.count {
        case 3: // RGB (12-bit)
            (a, r, g, b) = (255, (int >> 8) * 17, (int >> 4 & 0xF) * 17, (int & 0xF) * 17)
        case 6: // RGB (24-bit)
            (a, r, g, b) = (255, int >> 16, int >> 8 & 0xFF, int & 0xFF)
        case 8: // ARGB (32-bit)
            (a, r, g, b) = (int >> 24, int >> 16 & 0xFF, int >> 8 & 0xFF, int & 0xFF)
        default:
            (a, r, g, b) = (1, 1, 1, 0)
        }
        
        self.init(
            .sRGB,
            red: Double(r) / 255,
            green: Double(g) / 255,
            blue:  Double(b) / 255,
            opacity: Double(a) / 255
        )
    }
}
