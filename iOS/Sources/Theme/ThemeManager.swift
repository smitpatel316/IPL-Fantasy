import SwiftUI

// MARK: - Theme Manager
class ThemeManager: ObservableObject {
    static let shared = ThemeManager()
    
    @AppStorage("isDarkMode") var isDarkMode: Bool = true {
        didSet {
            applyTheme()
        }
    }
    
    private init() {}
    
    func applyTheme() {
        if isDarkMode {
            // Dark mode colors are already set as default
        } else {
            // Light mode would be applied here
        }
    }
    
    func toggle() {
        isDarkMode.toggle()
    }
}

// MARK: - Color Extensions for Theme
extension Color {
    static let theme = ThemeColors()
}

struct ThemeColors {
    let primary = Color("Primary", bundle: nil)
    let secondary = Color("Secondary", bundle: nil)
    let accent = Color("Accent", bundle: nil)
}

// MARK: - App Colors with Light/Dark Support
extension AppColors {
    // Dynamic colors that adapt to light/dark mode
    static var adaptiveBackground: Color {
        Color("Background", bundle: nil)
    }
    
    static var adaptiveCard: Color {
        Color("Card", bundle: nil)
    }
}

// MARK: - Theme Preview
struct ThemePreview: View {
    @StateObject private var themeManager = ThemeManager.shared
    
    var body: some View {
        VStack(spacing: 20) {
            Text("Current Theme: \(themeManager.isDarkMode ? "Dark" : "Light")")
                .font(.headline)
            
            Toggle("Dark Mode", isOn: $themeManager.isDarkMode)
                .padding()
            
            // Preview Colors
            HStack {
                ColorBox(color: AppColors.primary, name: "Primary")
                ColorBox(color: AppColors.accent, name: "Accent")
                ColorBox(color: AppColors.success, name: "Success")
            }
        }
        .padding()
    }
}

struct ColorBox: View {
    let color: Color
    let name: String
    
    var body: some View {
        VStack {
            color
                .frame(width: 60, height: 60)
                .cornerRadius(8)
            Text(name)
                .font(.caption)
        }
    }
}

#Preview {
    ThemePreview()
}
