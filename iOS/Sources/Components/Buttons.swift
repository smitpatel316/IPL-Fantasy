import SwiftUI

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
struct CardView: View {
    var backgroundColor: Color = AppColors.card
    var padding: CGFloat = AppSpacing.md
    
    var body: some View {
        VStack(alignment: .leading, spacing: AppSpacing.sm) {
            content
        }
        .padding(padding)
        .background(backgroundColor)
        .cornerRadius(AppCornerRadius.card)
    }
    
    @ViewBuilder
    var content: some View {
        EmptyView()
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
    
    var body: some View {
        Text(text)
            .font(AppFonts.small)
            .fontWeight(.semibold)
            .padding(.horizontal, AppSpacing.sm)
            .padding(.vertical, AppSpacing.xs)
            .background(color)
            .cornerRadius(AppCornerRadius.small)
    }
}
