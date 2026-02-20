import Foundation
import UserNotifications

// MARK: - Notification Service
class NotificationService {
    static let shared = NotificationService()
    
    private init() {}
    
    // Request permission
    func requestPermission() async -> Bool {
        do {
            let center = UNUserNotificationCenter.current()
            let granted = try await center.requestAuthorization(options: [.alert, .badge, .sound])
            return granted
        } catch {
            print("Notification permission error: \(error)")
            return false
        }
    }
    
    // Register for remote notifications
    func registerForRemote() {
        #if !targetEnvironment(simulator)
        UIApplication.shared.registerForRemoteNotifications()
        #endif
    }
    
    // Schedule local notification
    func scheduleLocal(
        id: String,
        title: String,
        body: String,
        timeInterval: TimeInterval = 60
    ) {
        let content = UNMutableNotificationContent()
        content.title = title
        content.body = body
        content.sound = .default
        
        let trigger = UNTimeIntervalNotificationTrigger(timeInterval: timeInterval, repeats: false)
        let request = UNNotificationRequest(identifier: id, content: content, trigger: trigger)
        
        UNUserNotificationCenter.current().add(request)
    }
    
    // Cancel notification
    func cancel(id: String) {
        UNUserNotificationCenter.current().removePendingNotificationRequests(withIdentifiers: [id])
    }
    
    // Cancel all
    func cancelAll() {
        UNUserNotificationCenter.current().removeAllPendingNotificationRequests()
    }
    
    // Badge count
    func setBadge(_ count: Int) {
        #if !targetEnvironment(simulator)
        UIApplication.shared.applicationIconBadgeNumber = count
        #endif
    }
}

// MARK: - Notification Types
enum NotificationType: String {
    case draftTurn = "draft_turn"
    case draftSold = "draft_sold"
    case matchStarting = "match_starting"
    case matchResult = "match_result"
    case tradeReceived = "trade_received"
    case tradeAccepted = "trade_accepted"
    case weeklyResult = "weekly_result"
    case leagueInvite = "league_invite"
}

// MARK: - Notification Manager
class NotificationManager {
    static let shared = NotificationManager()
    
    private init() {}
    
    // Draft Notifications
    func scheduleDraftTurnNotification(playerName: String) {
        NotificationService.shared.scheduleLocal(
            id: NotificationType.draftTurn.rawValue,
            title: "Your Turn!",
            body: "\(playerName) is up for auction. Place your bid now!",
            timeInterval: 1
        )
    }
    
    func schedulePlayerSoldNotification(playerName: String, teamName: String) {
        NotificationService.shared.scheduleLocal(
            id: NotificationType.draftSold.rawValue,
            title: "Player Sold!",
            body: "\(playerName) sold to \(teamName)",
            timeInterval: 1
        )
    }
    
    // Match Notifications
    func scheduleMatchStartingNotification(team1: String, team2: String) {
        NotificationService.shared.scheduleLocal(
            id: NotificationType.matchStarting.rawValue,
            title: "Match Starting Soon!",
            body: "\(team1) vs \(team2) starts in 30 minutes. Check your lineup!",
            timeInterval: 1800 // 30 minutes
        )
    }
    
    func scheduleMatchResultNotification(winner: String, score: String) {
        NotificationService.shared.scheduleLocal(
            id: NotificationType.matchResult.rawValue,
            title: "Match Result",
            body: "\(winner) won! Final: \(score)",
            timeInterval: 1
        )
    }
    
    // Trade Notifications
    func scheduleTradeReceivedNotification(fromTeam: String) {
        NotificationService.shared.scheduleLocal(
            id: NotificationType.tradeReceived.rawValue,
            title: "New Trade Offer!",
            body: "\(fromTeam) wants to make a trade with you",
            timeInterval: 1
        )
    }
    
    func scheduleTradeAcceptedNotification().shared.scheduleLocal(
 {
        NotificationService            id: NotificationType.tradeAccepted.rawValue,
            title: "Trade Accepted!",
            body: "Your trade offer was accepted. Check your team!",
            timeInterval: 1
        )
    }
    
    // Weekly Result
    func scheduleWeeklyResultNotification(result: String, points: Int) {
        NotificationService.shared.scheduleLocal(
            id: NotificationType.weeklyResult.rawValue,
            title: result,
            body: "You scored \(points) points this week!",
            timeInterval: 1
        )
    }
    
    // League Invite
    func scheduleLeagueInviteNotification(leagueName: String, inviter: String) {
        NotificationService.shared.scheduleLocal(
            id: NotificationType.leagueInvite.rawValue,
            title: "League Invite!",
            body: "\(inviter) invited you to join \(leagueName)",
            timeInterval: 1
        )
    }
}
