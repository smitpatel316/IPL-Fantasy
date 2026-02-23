import SwiftUI

// MARK: - Conditional View Modifier
extension View {
    @ViewBuilder
    func `if`<Content: View>(_ condition: Bool, transform: (Self) -> Content) -> some View {
        if condition {
            transform(self)
        } else {
            self
        }
    }
}

// MARK: - Primary Button
struct PrimaryButton: View {
    let title: String
    let action: () -> Void
    var isLoading: Bool = false
    var isDisabled: Bool = false
    
    var body: some View {
        Button(action: action) {
            HStack(spacing: AppSpacing.sm) {
                if isLoading {
                    ProgressView()
                        .progressViewStyle(CircularProgressViewStyle(tint: .white))
                        .scaleEffect(0.8)
                }
                Text(title)
                    .font(AppFonts.subheadline)
                    .fontWeight(.semibold)
            }
            .frame(maxWidth: .infinity)
            .padding(.vertical, AppSpacing.md)
            .background(isDisabled ? AppColors.textMuted : AppColors.primary)
            .foregroundColor(.white)
            .cornerRadius(AppCornerRadius.medium)
        }
        .disabled(isDisabled || isLoading)
    }
}

// MARK: - Secondary Button
struct SecondaryButton: View {
    let title: String
    let action: () -> Void
    
    var body: some View {
        Button(action: action) {
            Text(title)
                .font(AppFonts.subheadline)
                .fontWeight(.medium)
                .frame(maxWidth: .infinity)
                .padding(.vertical, AppSpacing.md)
                .background(AppColors.surface)
                .foregroundColor(AppColors.textPrimary)
                .cornerRadius(AppCornerRadius.medium)
                .overlay(
                    RoundedRectangle(cornerRadius: AppCornerRadius.medium)
                        .stroke(AppColors.textMuted, lineWidth: 1)
                )
        }
    }
}

// MARK: - Text Input Field
struct AppTextField: View {
    let placeholder: String
    @Binding var text: String
    var isSecure: Bool = false
    var keyboardType: UIKeyboardType = .default
    
    @FocusState private var isFocused: Bool
    
    var body: some View {
        VStack(alignment: .leading, spacing: AppSpacing.xs) {
            if !placeholder.isEmpty {
                Text(placeholder)
                    .font(AppFonts.caption)
                    .foregroundColor(AppColors.textSecondary)
            }
            
            Group {
                if isSecure {
                    SecureField("", text: $text)
                } else {
                    TextField("", text: $text)
                        .keyboardType(keyboardType)
                }
            }
            .focused($isFocused)
            .padding(AppSpacing.md)
            .background(AppColors.surface)
            .cornerRadius(AppCornerRadius.small)
            .foregroundColor(AppColors.textPrimary)
            .overlay(
                RoundedRectangle(cornerRadius: AppCornerRadius.small)
                    .stroke(isFocused ? AppColors.primary : AppColors.textMuted.opacity(0.3), lineWidth: 1)
            )
        }
    }
}

// MARK: - Card View
struct CardView<Content: View>: View {
    var backgroundColor: Color = AppColors.card
    var padding: CGFloat = AppSpacing.md
    @ViewBuilder let content: () -> Content

    init(@ViewBuilder content: @escaping () -> Content) {
        self.content = content
    }

    var body: some View {
        VStack(alignment: .leading, spacing: AppSpacing.sm) {
            content()
        }
        .padding(padding)
        .background(backgroundColor)
        .cornerRadius(AppCornerRadius.card)
    }
}

// MARK: - Loading View
struct LoadingView: View {
    var message: String = "Loading..."
    
    var body: some View {
        VStack(spacing: AppSpacing.md) {
            ProgressView()
                .progressViewStyle(CircularProgressViewStyle(tint: AppColors.primary))
                .scaleEffect(1.5)
            
            Text(message)
                .font(AppFonts.caption)
                .foregroundColor(AppColors.textSecondary)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .background(AppColors.background)
    }
}

// MARK: - Empty State View
struct EmptyStateView: View {
    let icon: String
    let title: String
    let message: String
    var buttonTitle: String?
    var buttonAction: (() -> Void)?
    
    var body: some View {
        VStack(spacing: AppSpacing.md) {
            Image(systemName: icon)
                .font(.system(size: 48))
                .foregroundColor(AppColors.textMuted)
            
            Text(title)
                .font(AppFonts.headline)
                .foregroundColor(AppColors.textPrimary)
            
            Text(message)
                .font(AppFonts.body)
                .foregroundColor(AppColors.textSecondary)
                .multilineTextAlignment(.center)
            
            if let buttonTitle = buttonTitle, let action = buttonAction {
                PrimaryButton(title: buttonTitle, action: action)
                    .frame(width: 200)
                    .padding(.top, AppSpacing.sm)
            }
        }
        .padding(AppSpacing.xl)
    }
}

// MARK: - Badge View
struct BadgeView: View {
    let text: String
    var color: Color = AppColors.primary
    var isPulsing: Bool = false

    var body: some View {
        Text(text)
            .font(AppFonts.small)
            .fontWeight(.semibold)
            .padding(.horizontal, AppSpacing.sm)
            .padding(.vertical, AppSpacing.xs)
            .background(color)
            .cornerRadius(AppCornerRadius.small)
            .if(isPulsing) { view in
                view.pulsing()
            }
    }
}

// MARK: - Animated Progress Bar
struct AnimatedProgressBar: View {
    let progress: Double
    var color: Color = AppColors.primary
    var height: CGFloat = 8

    @State private var animatedProgress: Double = 0

    var body: some View {
        GeometryReader { geometry in
            ZStack(alignment: .leading) {
                RoundedRectangle(cornerRadius: height / 2)
                    .fill(AppColors.surface)
                    .frame(height: height)

                RoundedRectangle(cornerRadius: height / 2)
                    .fill(color)
                    .frame(width: geometry.size.width * animatedProgress, height: height)
                    .shadow(color: color.opacity(0.5), radius: 4, y: 2)
            }
        }
        .frame(height: height)
        .onAppear {
            withAnimation(.easeOut(duration: 0.8)) {
                animatedProgress = progress
            }
        }
        .onChange(of: progress) { _, newValue in
            withAnimation(.easeOut(duration: 0.5)) {
                animatedProgress = newValue
            }
        }
    }
}

// MARK: - Team Logo View
struct TeamLogoView: View {
    let teamCode: String
    var size: CGFloat = 50

    var body: some View {
        ZStack {
            Circle()
                .fill(teamColor.opacity(0.2))
                .frame(width: size, height: size)

            Text(teamCode.prefix(2))
                .font(.system(size: size * 0.35, weight: .bold))
                .foregroundColor(teamColor)
        }
    }

    private var teamColor: Color {
        switch teamCode.uppercased() {
        case "MI": return Color(hex: "00A8E1")
        case "CSK": return Color(hex: "FDB913")
        case "RCB": return Color(hex: "D1C265")
        case "DC": return Color(hex: "0078BC")
        case "KKR": return Color(hex: "3A225D")
        case "RR": return Color(hex: "E5386B")
        case "PBKS": return Color(hex: "DA291C")
        case "SRH": return Color(hex: "FF662F")
        case "GT": return Color(hex: "1C1C1C")
        case "LSG": return Color(hex: "0D5D2E")
        default: return AppColors.primary
        }
    }
}
