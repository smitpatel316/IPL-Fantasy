import SwiftUI

// MARK: - Notifications View
struct NotificationsView: View {
    @StateObject private var viewModel = NotificationsViewModel()
    
    var body: some View {
        NavigationStack {
            ZStack {
                AppColors.background
                    .ignoresSafeArea()
                
                if viewModel.notifications.isEmpty {
                    emptyState
                } else {
                    notificationsList
                }
            }
            .navigationTitle("Notifications")
            .navigationBarTitleDisplayMode(.large)
            .toolbar {
                ToolbarItem(placement: .navigationBarTrailing) {
                    if !viewModel.notifications.isEmpty {
                        Button("Mark All Read") {
                            viewModel.markAllRead()
                        }
                        .foregroundColor(AppColors.primary)
                    }
                }
            }
        }
    }
    
    private var notificationsList: some View {
        ScrollView {
            LazyVStack(spacing: AppSpacing.sm) {
                ForEach(viewModel.notifications) { notification in
                    NotificationRow(notification: notification) {
                        viewModel.markRead(id: notification.id)
                    }
                }
            }
            .padding(AppSpacing.md)
        }
    }
    
    private var emptyState: some View {
        VStack(spacing: AppSpacing.md) {
            Image(systemName: "bell.slash")
                .font(.system(size: 48))
                .foregroundColor(AppColors.textMuted)
            
            Text("No Notifications")
                .font(AppFonts.headline)
                .foregroundColor(AppColors.textPrimary)
            
            Text("You're all caught up!")
                .font(AppFonts.body)
                .foregroundColor(AppColors.textSecondary)
        }
    }
}

struct NotificationRow: View {
    let notification: AppNotification
    let onTap: () -> Void
    
    var body: some View {
        Button(action: onTap) {
            HStack(spacing: AppSpacing.md) {
                // Icon
                ZStack {
                    Circle()
                        .fill(notification.color.opacity(0.2))
                        .frame(width: 44, height: 44)
                    
                    Image(systemName: notification.icon)
                        .font(.system(size: 18))
                        .foregroundColor(notification.color)
                }
                
                // Content
                VStack(alignment: .leading, spacing: AppSpacing.xs) {
                    Text(notification.title)
                        .font(AppFonts.subheadline)
                        .fontWeight(.semibold)
                        .foregroundColor(notification.isRead ? AppColors.textSecondary : AppColors.textPrimary)
                        .lineLimit(2)
                    
                    Text(notification.message)
                        .font(AppFonts.caption)
                        .foregroundColor(AppColors.textSecondary)
                        .lineLimit(2)
                    
                    Text(notification.timeAgo)
                        .font(AppFonts.small)
                        .foregroundColor(AppColors.textMuted)
                }
                
                Spacer()
                
                // Unread indicator
                if !notification.isRead {
                    Circle()
                        .fill(AppColors.primary)
                        .frame(width: 8, height: 8)
                }
            }
            .padding(AppSpacing.md)
            .background(notification.isRead ? AppColors.card : AppColors.card.opacity(0.8))
            .cornerRadius(AppCornerRadius.medium)
        }
        .buttonStyle(PlainButtonStyle())
    }
}

// MARK: - Notifications View Model
@MainActor
class NotificationsViewModel: ObservableObject {
    @Published var notifications: [AppNotification] = []
    
    init() {
        loadMockNotifications()
    }
    
    func markRead(id: String) {
        if let index = notifications.firstIndex(where: { $0.id == id }) {
            notifications[index].isRead = true
        }
    }
    
    func markAllRead() {
        for index in notifications.indices {
            notifications[index].isRead = true
        }
    }
    
    private func loadMockNotifications() {
        notifications = [
            AppNotification(id: "1", type: .trade, title: "Trade Offer Received", message: "Team Bolt offered you a trade for Jasprit Bumrah", timeAgo: "2 hours ago", isRead: false),
            AppNotification(id: "2", type: .match, title: "Match Starting Soon", message: "MI vs CSK starts in 30 minutes. Check your lineup!", timeAgo: "25 min ago", isRead: false),
            AppNotification(id: "3", type: .league, title: "You Won Week 8!", message: "Congratulations! Team Fire beat Team Bolt 5-4", timeAgo: "3 hours ago", isRead: true),
            AppNotification(id: "4", type: .draft, title: "Draft Reminder", message: "Auction draft starts tomorrow at 7pm", timeAgo: "1 day ago", isRead: true),
            AppNotification(id: "5", type: .system, title: "Welcome to IPL Fantasy!", message: "Complete your profile to start playing", timeAgo: "2 days ago", isRead: true),
            AppNotification(id: "6", type: .league, title: "New League Member", message: "Sanju joined Sunday League", timeAgo: "2 days ago", isRead: true),
        ]
    }
}

// MARK: - Notification Model
struct AppNotification: Identifiable {
    let id: String
    let type: NotificationType
    let title: String
    let message: String
    let timeAgo: String
    var isRead: Bool
    
    enum NotificationType {
        case trade
        case match
        case league
        case draft
        case system
        
        var icon: String {
            switch self {
            case .trade: return "arrow.left.arrow.right"
            case .match: return "sportscourt"
            case .league: return "person.3"
            case .draft: return "hammer"
            case .system: return "gear"
            }
        }
        
        var color: Color {
            switch self {
            case .trade: return AppColors.accent
            case .match: return AppColors.success
            case .league: return AppColors.primary
            case .draft: return AppColors.warning
            case .system: return AppColors.textMuted
            }
        }
    }
}
