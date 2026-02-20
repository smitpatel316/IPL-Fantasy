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
            
            DraftRoomView()
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
    }
}
