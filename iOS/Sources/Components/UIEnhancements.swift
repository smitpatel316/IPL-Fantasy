import SwiftUI

// MARK: - Error Alert Modifier
struct ErrorAlert: ViewModifier {
    @Binding var error: String?
    
    func body(content: Content) -> some View {
        content
            .alert("Error", isPresented: Binding(
                get: { error != nil },
                set: { if !$0 { error = nil } }
            )) {
                Button("OK") { error = nil }
            } message: {
                Text(error ?? "Something went wrong")
            }
        }
    }
}

extension View {
    func errorAlert(_ error: Binding<String?>) -> some View {
        modifier(ErrorAlert(error: error))
    }
}

// MARK: - Loading Overlay
struct LoadingOverlay: View {
    let message: String
    
    var body: some View {
        ZStack {
            Color.black.opacity(0.5)
                .ignoresSafeArea()
            
            VStack(spacing: AppSpacing.md) {
                ProgressView()
                    .progressViewStyle(CircularProgressViewStyle(tint: .white))
                    .scaleEffect(1.5)
                
                Text(message)
                    .font(AppFonts.body)
                    .foregroundColor(.white)
            }
            .padding(AppSpacing.xl)
            .background(AppColors.card)
            .cornerRadius(AppCornerRadius.card)
        }
    }
}

// MARK: - Toast View
struct ToastView: View {
    let message: String
    let type: ToastType
    
    enum ToastType {
        case success, error, info
        
        var color: Color {
            switch self {
            case .success: return AppColors.success
            case .error: return AppColors.error
            case .info: return AppColors.primary
            }
        }
        
        var icon: String {
            switch self {
            case .success: return "checkmark.circle.fill"
            case .error: return "xmark.circle.fill"
            case .info: return "info.circle.fill"
            }
        }
    }
    
    var body: some View {
        HStack(spacing: AppSpacing.md) {
            Image(systemName: type.icon)
                .foregroundColor(type.color)
            
            Text(message)
                .font(AppFonts.body)
                .foregroundColor(AppColors.textPrimary)
        }
        .padding(.horizontal, AppSpacing.lg)
        .padding(.vertical, AppSpacing.md)
        .background(AppColors.card)
        .cornerRadius(AppCornerRadius.medium)
        .shadow(color: .black.opacity(0.3), radius: 10, y: 5)
    }
}

// MARK: - Shimmer Effect
struct ShimmerModifier: ViewModifier {
    @State private var phase: CGFloat = 0
    
    func body(content: Content) -> some View {
        content
            .overlay(
                LinearGradient(
                    gradient: Gradient(colors: [
                        Color.clear,
                        Color.white.opacity(0.3),
                        Color.clear
                    ]),
                    startPoint: .leading,
                    endPoint: .trailing
                )
                .offset(x: phase)
                .onAppear {
                    withAnimation(.linear(duration: 1.5).repeatForever(autoreverses: false)) {
                        phase = 400
                    }
                }
            )
            .clipped()
    }
}

extension View {
    func shimmer() -> some View {
        modifier(ShimmerModifier())
    }
}

// MARK: - Skeleton Loader
struct SkeletonLoader: View {
    var body: some View {
        VStack(spacing: AppSpacing.md) {
            ForEach(0..<5, id: \.self) { _ in
                HStack(spacing: AppSpacing.md) {
                    Circle()
                        .fill(AppColors.surface)
                        .frame(width: 50, height: 50)
                        .shimmer()
                    
                    VStack(alignment: .leading, spacing: AppSpacing.xs) {
                        RoundedRectangle(cornerRadius: 4)
                            .fill(AppColors.surface)
                            .frame(width: 150, height: 16)
                            .shimmer()
                        
                        RoundedRectangle(cornerRadius: 4)
                            .fill(AppColors.surface)
                            .frame(width: 100, height: 12)
                            .shimmer()
                    }
                    
                    Spacer()
                }
                .padding(AppSpacing.md)
                .background(AppColors.card)
                .cornerRadius(AppCornerRadius.medium)
            }
        }
    }
}

// MARK: - Pull to Refresh
struct RefreshableScrollView<Content: View>: View {
    let onRefresh: () async -> Void
    @ViewBuilder let content: Content
    
    @State private var isRefreshing = false
    
    var body: some View {
        ScrollView {
            content
                .onAppear {
                    // Pull to refresh would be implemented with native SwiftUI .refreshable
                }
        }
    }
}

// MARK: - Animated Counter
struct AnimatedCounter: View {
    let value: Int
    let duration: Double = 0.5
    
    @State private var displayedValue = 0
    
    var body: some View {
        Text("\(displayedValue)")
            .onAppear {
                withAnimation(.easeOut(duration: duration)) {
                    displayedValue = value
                }
            }
            .onChange(of: value) { _, newValue in
                withAnimation(.easeOut(duration: duration)) {
                    displayedValue = newValue
                }
            }
    }
}

// MARK: - Shake Effect
struct ShakeEffect: GeometryEffect {
    var amount: CGFloat = 10
    var shakesPerUnit = 3
    var animatableData: CGFloat
    
    func effectValue(size: CGSize) -> ProjectionTransform {
        ProjectionTransform(CGAffineTransform(translationX:
            amount * sin(animatableData * .pi * CGFloat(shakesPerUnit)),
            y: 0))
    }
}

extension View {
    func shake(trigger: Bool) -> some View {
        modifier(ShakeEffect(animatableData: trigger ? 1 : 0))
    }
}
