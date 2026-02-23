import SwiftUI

@main
struct IPLFantasyProApp: App {
    @StateObject private var authViewModel = AuthViewModel()
    @State private var deepLinkCode: String?
    
    var body: some Scene {
        WindowGroup {
            ContentView()
                .environmentObject(authViewModel)
                .onOpenURL { url in
                    handleDeepLink(url: url)
                }
        }
    }
    
    private func handleDeepLink(url: URL) {
        // Handle iplfantasy://join/CODE
        guard url.scheme == "iplfantasy" else { return }
        
        if url.host == "join", let code = url.pathComponents.last, !code.isEmpty {
            deepLinkCode = code
            // Post notification to show join sheet
            NotificationCenter.default.post(
                name: .showJoinLeague,
                object: nil,
                userInfo: ["code": code]
            )
        }
    }
}

extension Notification.Name {
    static let showJoinLeague = Notification.Name("showJoinLeague")
}
