import SwiftUI

// MARK: - Content View
struct ContentView: View {
    @EnvironmentObject var authViewModel: AuthViewModel

    var body: some View {
        Group {
            if authViewModel.isAuthenticated {
                MainTabView()
            } else {
                LoginView()
            }
        }
        .animation(.easeInOut(duration: 0.3), value: authViewModel.isAuthenticated)
    }
}

// MARK: - Main Tab View
struct MainTabView: View {
    @State private var selectedTab = 0
    @State private var showingJoinSheet = false
    @State private var joinCode = ""
    @StateObject private var leagueViewModel = LeagueViewModel()

    var body: some View {
        TabView(selection: $selectedTab) {
            DashboardView()
                .tabItem {
                    Image(systemName: "house.fill")
                    Text("Home")
                }
                .tag(0)

            LeagueListView()
                .tabItem {
                    Image(systemName: "person.3.fill")
                    Text("Leagues")
                }
                .tag(1)

            DraftRoomView(leagueId: "")
                .tabItem {
                    Image(systemName: "hammer.fill")
                    Text("Draft")
                }
                .tag(2)

            MyTeamView()
                .tabItem {
                    Image(systemName: "sportscourt.fill")
                    Text("My Team")
                }
                .tag(3)
            
            StandingsView()
                .tabItem {
                    Image(systemName: "chart.bar.fill")
                    Text("Standings")
                }
                .tag(4)
        }
        .tint(AppColors.primary)
        .onAppear {
            configureTabBarAppearance()
        }
        .onReceive(NotificationCenter.default.publisher(for: .showJoinLeague)) { notification in
            if let code = notification.userInfo?["code"] as? String {
                joinCode = code
                showingJoinSheet = true
            }
        }
        .sheet(isPresented: $showingJoinSheet) {
            Text("Join League: \(joinCode)")
                .padding()
        }
    }

    private func configureTabBarAppearance() {
        let tabBarAppearance = UITabBarAppearance()
        tabBarAppearance.configureWithOpaqueBackground()
        tabBarAppearance.backgroundColor = UIColor(AppColors.surface)

        // Normal state
        tabBarAppearance.stackedLayoutAppearance.normal.iconColor = UIColor(AppColors.textMuted)
        tabBarAppearance.stackedLayoutAppearance.normal.titleTextAttributes = [
            .foregroundColor: UIColor(AppColors.textMuted)
        ]

        // Selected state
        tabBarAppearance.stackedLayoutAppearance.selected.iconColor = UIColor(AppColors.primary)
        tabBarAppearance.stackedLayoutAppearance.selected.titleTextAttributes = [
            .foregroundColor: UIColor(AppColors.primary)
        ]

        UITabBar.appearance().standardAppearance = tabBarAppearance
        UITabBar.appearance().scrollEdgeAppearance = tabBarAppearance

        // Configure navigation bar appearance
        let navAppearance = UINavigationBarAppearance()
        navAppearance.configureWithOpaqueBackground()
        navAppearance.backgroundColor = UIColor(AppColors.background)
        navAppearance.titleTextAttributes = [.foregroundColor: UIColor.white]
        navAppearance.largeTitleTextAttributes = [.foregroundColor: UIColor.white]

        UINavigationBar.appearance().standardAppearance = navAppearance
        UINavigationBar.appearance().compactAppearance = navAppearance
        UINavigationBar.appearance().scrollEdgeAppearance = navAppearance
    }
}
