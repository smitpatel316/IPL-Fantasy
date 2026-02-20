import SwiftUI

// MARK: - League Detail View
struct LeagueDetailView: View {
    let league: League
    @State private var selectedTab = 0
    
    var body: some View {
        NavigationStack {
            ZStack {
                AppColors.background
                    .ignoresSafeArea()
                
                VStack(spacing: 0) {
                    // Header
                    leagueHeader
                    
                    // Tab Bar
                    tabBar
                    
                    // Content
                    TabView(selection: $selectedTab) {
                        overviewTab
                            .tag(0)
                        
                        teamsTab
                            .tag(1)
                        
                        scheduleTab
                            .tag(2)
                        
                        settingsTab
                            .tag(3)
                    }
                    .tabViewStyle(.page(indexDisplayMode: .never))
                }
            }
            .navigationTitle(league.name)
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .navigationBarTrailing) {
                    Menu {
                        Button(action: {}) {
                            Label("Invite", systemImage: "person.badge.plus")
                        }
                        Button(action: {}) {
                            Label("Leave League", systemImage: "arrow.right.square")
                        }
                    } label: {
                        Image(systemName: "ellipsis.circle")
                            .foregroundColor(AppColors.primary)
                    }
                }
            }
        }
    }
    
    private var leagueHeader: some View {
        VStack(spacing: AppSpacing.md) {
            // League Icon
            ZStack {
                Circle()
                    .fill(AppColors.primary.opacity(0.2))
                    .frame(width: 80, height: 80)
                
                Text(String(league.name.prefix(1)))
                    .font(.system(size: 32, weight: .bold))
                    .foregroundColor(AppColors.primary)
            }
            
            // Stats
            HStack(spacing: AppSpacing.xl) {
                VStack(spacing: 2) {
                    Text("\(league.members.count)")
                        .font(AppFonts.headline)
                        .fontWeight(.bold)
                        .foregroundColor(AppColors.textPrimary)
                    Text("Teams")
                        .font(AppFonts.caption)
                        .foregroundColor(AppColors.textMuted)
                }
                
                VStack(spacing: 2) {
                    Text("₹\(Int(league.auctionBudget))Cr")
                        .font(AppFonts.headline)
                        .fontWeight(.bold)
                        .foregroundColor(AppColors.textPrimary)
                    Text("Budget")
                        .font(AppFonts.caption)
                        .foregroundColor(AppColors.textMuted)
                }
                
                VStack(spacing: 2) {
                    Text(league.status.rawValue.capitalized)
                        .font(AppFonts.headline)
                        .fontWeight(.bold)
                        .foregroundColor(statusColor)
                    Text("Status")
                        .font(AppFonts.caption)
                        .foregroundColor(AppColors.textMuted)
                }
            }
            
            // Action Button
            if league.status == .open {
                Button(action: {}) {
                    Text("Start Auction")
                        .font(AppFonts.subheadline)
                        .fontWeight(.semibold)
                        .foregroundColor(.white)
                        .frame(maxWidth: .infinity)
                        .padding(.vertical, AppSpacing.md)
                        .background(AppColors.primary)
                        .cornerRadius(AppCornerRadius.medium)
                }
                .padding(.horizontal, AppSpacing.lg)
            }
        }
        .padding(AppSpacing.lg)
        .background(AppColors.card)
    }
    
    private var tabBar: some View {
        HStack(spacing: 0) {
            ForEach(["Overview", "Teams", "Schedule", "Settings"], id: \.self) { tab in
                Button(action: { withAnimation { selectedTab = tabIndex(tab) } }) {
                    VStack(spacing: AppSpacing.xs) {
                        Text(tab)
                            .font(selectedTab == tabIndex(tab) ? AppFonts.headline : AppFonts.body)
                            .fontWeight(selectedTab == tabIndex(tab) ? .bold : .regular)
                            .foregroundColor(selectedTab == tabIndex(tab) ? AppColors.primary : AppColors.textMuted)
                        
                        Rectangle()
                            .fill(selectedTab == tabIndex(tab) ? AppColors.primary : Color.clear)
                            .frame(height: 2)
                    }
                }
                .frame(maxWidth: .infinity)
            }
        }
        .padding(.horizontal, AppSpacing.md)
        .background(AppColors.card)
    }
    
    private func tabIndex(_ tab: String) -> Int {
        ["Overview", "Teams", "Schedule", "Settings"].firstIndex(of: tab) ?? 0
    }
    
    private var statusColor: Color {
        switch league.status {
        case .open: return AppColors.success
        case .drafting: return AppColors.warning
        case .active: return AppColors.primary
        case .completed: return AppColors.textMuted
        }
    }
    
    private var overviewTab: some View {
        ScrollView {
            VStack(spacing: AppSpacing.md) {
                // League Code
                HStack {
                    Text("League Code:")
                        .font(AppFonts.subheadline)
                        .foregroundColor(AppColors.textSecondary)
                    
                    Spacer()
                    
                    Text(league.code)
                        .font(AppFonts.headline)
                        .fontWeight(.bold)
                        .foregroundColor(AppColors.accent)
                    
                    Button(action: {}) {
                        Image(systemName: "doc.on.doc")
                            .foregroundColor(AppColors.primary)
                    }
                }
                .padding(AppSpacing.md)
                .background(AppColors.card)
                .cornerRadius(AppCornerRadius.medium)
                
                // Commissioner
                HStack {
                    Text("Commissioner:")
                        .font(AppFonts.subheadline)
                        .foregroundColor(AppColors.textSecondary)
                    
                    Spacer()
                    
                    Text("You")
                        .font(AppFonts.subheadline)
                        .fontWeight(.semibold)
                        .foregroundColor(AppColors.textPrimary)
                }
                .padding(AppSpacing.md)
                .background(AppColors.card)
                .cornerRadius(AppCornerRadius.medium)
                
                // Recent Activity
                VStack(alignment: .leading, spacing: AppSpacing.sm) {
                    Text("Recent Activity")
                        .font(AppFonts.headline)
                        .foregroundColor(AppColors.textPrimary)
                    
                    ActivityRow(icon: "person.badge.plus", text: "Sanju joined the league", time: "2 hours ago")
                    ActivityRow(icon: "arrow.left.arrow.right", text: "Trade completed: Rohit → Bumrah", time: "1 day ago")
                    ActivityRow(icon: "hammer", text: "Auction draft completed", time: "3 days ago")
                }
                .padding(AppSpacing.md)
                .background(AppColors.card)
                .cornerRadius(AppCornerRadius.medium)
            }
            .padding(AppSpacing.md)
        }
    }
    
    private var teamsTab: some View {
        ScrollView {
            LazyVStack(spacing: AppSpacing.sm) {
                ForEach(league.members) { member in
                    TeamListRow(member: member)
                }
            }
            .padding(AppSpacing.md)
        }
    }
    
    private var scheduleTab: some View {
        ScrollView {
            VStack(spacing: AppSpacing.sm) {
                ForEach(1...14, id: \.self) { week in
                    ScheduleRow(week: week, status: week < 8 ? .completed : (week == 8 ? .current : .upcoming))
                }
            }
            .padding(AppSpacing.md)
        }
    }
    
    private var settingsTab: some View {
        List {
            Button(action: {}) {
                Label("Edit League Settings", systemImage: "pencil")
            }
            
            Button(action: {}) {
                Label("Transfer Commissioner", systemImage: "arrow.triangle.swap")
            }
            
            Button(action: {}) {
                Label("Delete League", systemImage: "trash")
                    .foregroundColor(AppColors.error)
            }
        }
        .scrollContentBackground(.hidden)
    }
}

// MARK: - Activity Row
struct ActivityRow: View {
    let icon: String
    let text: String
    let time: String
    
    var body: some View {
        HStack(spacing: AppSpacing.md) {
            Image(systemName: icon)
                .foregroundColor(AppColors.primary)
                .frame(width: 24)
            
            Text(text)
                .font(AppFonts.caption)
                .foregroundColor(AppColors.textPrimary)
            
            Spacer()
            
            Text(time)
                .font(AppFonts.small)
                .foregroundColor(AppColors.textMuted)
        }
    }
}

// MARK: - Team List Row
struct TeamListRow: View {
    let member: LeagueMember
    
    var body: some View {
        HStack(spacing: AppSpacing.md) {
            Circle()
                .fill(AppColors.primary.opacity(0.2))
                .frame(width: 40, height: 40)
                .overlay(
                    Text(String(member.teamName.prefix(1)))
                        .font(AppFonts.subheadline)
                        .fontWeight(.bold)
                        .foregroundColor(AppColors.primary)
                )
            
            VStack(alignment: .leading, spacing: 2) {
                Text(member.teamName)
                    .font(AppFonts.subheadline)
                    .fontWeight(.semibold)
                    .foregroundColor(AppColors.textPrimary)
                
                if member.isCommissioner {
                    Text("Commissioner")
                        .font(AppFonts.small)
                        .foregroundColor(AppColors.accent)
                }
            }
            
            Spacer()
            
            VStack(alignment: .trailing, spacing: 2) {
                Text("₹\(Int(member.budgetRemaining))Cr")
                    .font(AppFonts.caption)
                    .foregroundColor(AppColors.textSecondary)
            }
        }
        .padding(AppSpacing.md)
        .background(AppColors.card)
        .cornerRadius(AppCornerRadius.medium)
    }
}

// MARK: - Schedule Row
struct ScheduleRow: View {
    let week: Int
    let status: ScheduleStatus
    
    enum ScheduleStatus {
        case completed, current, upcoming
        
        var color: Color {
            switch self {
            case .completed: return AppColors.success
            case .current: return AppColors.primary
            case .upcoming: return AppColors.textMuted
            }
        }
    }
    
    var body: some View {
        HStack {
            Circle()
                .fill(status.color)
                .frame(width: 8, height: 8)
            
            Text("Week \(week)")
                .font(AppFonts.subheadline)
                .foregroundColor(AppColors.textPrimary)
            
            Spacer()
            
            Text(statusText)
                .font(AppFonts.caption)
                .foregroundColor(status.color)
        }
        .padding(AppSpacing.md)
        .background(AppColors.card)
        .cornerRadius(AppCornerRadius.small)
    }
    
    private var statusText: String {
        switch status {
        case .completed: return "Completed"
        case .current: return "In Progress"
        case .upcoming: return "Upcoming"
        }
    }
}
