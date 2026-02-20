import WidgetKit
import SwiftUI

// MARK: - Widget Entry
struct FantasyEntry: TimelineEntry {
    let date: Date
    let teamName: String
    let totalPoints: Int
    let rank: Int
    let liveMatch: String?
    let weeklyPoints: Int
}

// MARK: - Timeline Provider
struct FantasyProvider: TimelineProvider {
    func placeholder(in context: Context) -> FantasyEntry {
        FantasyEntry(
            date: Date(),
            teamName: "My Team",
            totalPoints: 1245,
            rank: 3,
            liveMatch: "MI vs CSK",
            weeklyPoints: 156
        )
    }
    
    func getSnapshot(in context: Context, completion: @escaping (FantasyEntry) -> Void) {
        let entry = FantasyEntry(
            date: Date(),
            teamName: "Team Fire",
            totalPoints: 1245,
            rank: 3,
            liveMatch: "MI vs CSK",
            weeklyPoints: 156
        )
        completion(entry)
    }
    
    func getTimeline(in context: Context, completion: @escaping (Timeline<FantasyEntry>) -> Void) {
        let entry = FantasyEntry(
            date: Date(),
            teamName: "Team Fire",
            totalPoints: 1245,
            rank: 3,
            liveMatch: "MI vs CSK",
            weeklyPoints: 156
        )
        
        // Refresh every 15 minutes
        let nextUpdate = Calendar.current.date(byAdding: .minute, value: 15, to: Date())!
        let timeline = Timeline(entries: [entry], policy: .after(nextUpdate))
        
        completion(timeline)
    }
}

// MARK: - Small Widget View
struct SmallWidgetView: View {
    let entry: FantasyEntry
    
    var body: some View {
        VStack(alignment: .leading, spacing: 4) {
            HStack {
                Image(systemName: "cricket.bat.ball")
                    .font(.system(size: 14))
                    .foregroundColor(.orange)
                Text("IPL Fantasy")
                    .font(.system(size: 12, weight: .semibold))
                    .foregroundColor(.white)
            }
            
            Spacer()
            
            Text(entry.teamName)
                .font(.system(size: 16, weight: .bold))
                .foregroundColor(.white)
                .lineLimit(1)
            
            HStack {
                Text("\(entry.totalPoints) pts")
                    .font(.system(size: 20, weight: .bold))
                    .foregroundColor(.green)
                
                Spacer()
                
                Text("#\(entry.rank)")
                    .font(.system(size: 14, weight: .medium))
                    .foregroundColor(.white.opacity(0.8))
            }
        }
        .padding(12)
        .containerBackground(for: .widget) {
            Color(red: 0.1, green: 0.1, blue: 0.15)
        }
    }
}

// MARK: - Medium Widget View
struct MediumWidgetView: View {
    let entry: FantasyEntry
    
    var body: some View {
        HStack(spacing: 16) {
            // Left side - Team info
            VStack(alignment: .leading, spacing: 4) {
                HStack {
                    Image(systemName: "cricket.bat.ball")
                        .font(.system(size: 12))
                        .foregroundColor(.orange)
                    Text("IPL Fantasy")
                        .font(.system(size: 11))
                        .foregroundColor(.white.opacity(0.7))
                }
                
                Spacer()
                
                Text(entry.teamName)
                    .font(.system(size: 16, weight: .bold))
                    .foregroundColor(.white)
                
                Text("\(entry.totalPoints) points")
                    .font(.system(size: 13))
                    .foregroundColor(.green)
                
                Text("Rank #\(entry.rank)")
                    .font(.system(size: 11))
                    .foregroundColor(.white.opacity(0.7))
            }
            
            Divider()
                .background(Color.white.opacity(0.3))
            
            // Right side - Live match
            VStack(alignment: .leading, spacing: 4) {
                if let match = entry.liveMatch {
                    HStack {
                        Circle()
                            .fill(Color.red)
                            .frame(width: 6, height: 6)
                        Text("LIVE")
                            .font(.system(size: 9, weight: .bold))
                            .foregroundColor(.red)
                    }
                    
                    Text(match)
                        .font(.system(size: 12, weight: .medium))
                        .foregroundColor(.white)
                        .lineLimit(1)
                }
                
                Spacer()
                
                Text("This week")
                    .font(.system(size: 10))
                    .foregroundColor(.white.opacity(0.6))
                
                Text("+\(entry.weeklyPoints) pts")
                    .font(.system(size: 18, weight: .bold))
                    .foregroundColor(.green)
            }
        }
        .padding(12)
        .containerBackground(for: .widget) {
            Color(red: 0.1, green: 0.1, blue: 0.15)
        }
    }
}

// MARK: - Large Widget View
struct LargeWidgetView: View {
    let entry: FantasyEntry
    
    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            // Header
            HStack {
                Image(systemName: "cricket.bat.ball")
                    .font(.system(size: 16))
                    .foregroundColor(.orange)
                Text("IPL Fantasy Pro")
                    .font(.system(size: 14, weight: .semibold))
                    .foregroundColor(.white)
                
                Spacer()
                
                Text("Updated just now")
                    .font(.system(size: 10))
                    .foregroundColor(.white.opacity(0.5))
            }
            
            // Team Card
            HStack {
                VStack(alignment: .leading, spacing: 4) {
                    Text(entry.teamName)
                        .font(.system(size: 18, weight: .bold))
                        .foregroundColor(.white)
                    
                    Text("Total Points")
                        .font(.system(size: 11))
                        .foregroundColor(.white.opacity(0.6))
                }
                
                Spacer()
                
                VStack(alignment: .trailing, spacing: 4) {
                    Text("\(entry.totalPoints)")
                        .font(.system(size: 24, weight: .bold))
                        .foregroundColor(.green)
                    
                    HStack(spacing: 4) {
                        Image(systemName: "chart.bar.fill")
                            .font(.system(size: 10))
                        Text("Rank #\(entry.rank)")
                    }
                    .font(.system(size: 11))
                    .foregroundColor(.white.opacity(0.8))
                }
            }
            .padding(12)
            .background(Color.white.opacity(0.1))
            .cornerRadius(12)
            
            // Weekly Progress
            VStack(alignment: .leading, spacing: 6) {
                Text("This Week")
                    .font(.system(size: 12, weight: .medium))
                    .foregroundColor(.white.opacity(0.8))
                
                HStack {
                    Text("+\(entry.weeklyPoints)")
                        .font(.system(size: 28, weight: .bold))
                        .foregroundColor(.green)
                    
                    Text("points")
                        .font(.system(size: 14))
                        .foregroundColor(.white.opacity(0.6))
                    
                    Spacer()
                }
            }
            
            // Live Match
            if let match = entry.liveMatch {
                HStack {
                    HStack(spacing: 6) {
                        Circle()
                            .fill(Color.red)
                            .frame(width: 8, height: 8)
                        Text("LIVE")
                            .font(.system(size: 10, weight: .bold))
                            .foregroundColor(.red)
                    }
                    
                    Spacer()
                    
                    Text(match)
                        .font(.system(size: 12, weight: .medium))
                        .foregroundColor(.white)
                }
                .padding(10)
                .background(Color.red.opacity(0.2))
                .cornerRadius(8)
            }
            
            Spacer()
        }
        .padding(12)
        .containerBackground(for: .widget) {
            Color(red: 0.1, green: 0.1, blue: 0.15)
        }
    }
}

// MARK: - Widget Configuration
@main
struct IPLFantasyWidget: Widget {
    let kind: String = "IPLFantasyWidget"
    
    var body: some WidgetConfiguration {
        StaticConfiguration(kind: kind, provider: FantasyProvider()) { entry in
            IPLFantasyWidgetEntryView(entry: entry)
        }
        .configurationDisplayName("Fantasy Team")
        .description("Track your fantasy team points and live matches.")
        .supportedFamilies([.systemSmall, .systemMedium, .systemLarge])
    }
}

struct IPLFantasyWidgetEntryView: View {
    @Environment(\.widgetFamily) var family
    let entry: FantasyProvider.Entry
    
    var body: some View {
        switch family {
        case .systemSmall:
            SmallWidgetView(entry: entry)
        case .systemMedium:
            MediumWidgetView(entry: entry)
        case .systemLarge:
            LargeWidgetView(entry: entry)
        default:
            SmallWidgetView(entry: entry)
        }
    }
}

// MARK: - Preview
#Preview(as: .systemSmall) {
    IPLFantasyWidget()
} timeline: {
    FantasyEntry(
        date: Date(),
        teamName: "Team Fire",
        totalPoints: 1245,
        rank: 3,
        liveMatch: "MI vs CSK",
        weeklyPoints: 156
    )
}
