import SwiftUI

// MARK: - League Chat View
struct LeagueChatView: View {
    let leagueId: String
    @StateObject private var viewModel = ChatViewModel()
    @Environment(\.dismiss) var dismiss
    
    var body: some View {
        NavigationStack {
            ZStack {
                AppColors.background
                    .ignoresSafeArea()
                
                VStack(spacing: 0) {
                    // Messages List
                    ScrollViewReader { proxy in
                        ScrollView {
                            LazyVStack(spacing: AppSpacing.sm) {
                                ForEach(viewModel.messages) { message in
                                    ChatMessageRow(message: message, isOwn: message.userId == viewModel.currentUserId)
                                        .id(message.id)
                                }
                            }
                            .padding(AppSpacing.md)
                        }
                        .onChange(of: viewModel.messages.count) { _, _ in
                            if let last = viewModel.messages.last {
                                withAnimation {
                                    proxy.scrollTo(last.id, anchor: .bottom)
                                }
                            }
                        }
                    }
                    
                    // Input Area
                    messageInput
                }
            }
            .navigationTitle("League Chat")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .navigationBarLeading) {
                    Button(action: { dismiss() }) {
                        Image(systemName: "chevron.left")
                            .foregroundColor(AppColors.primary)
                    }
                }
                
                ToolbarItem(placement: .navigationBarTrailing) {
                    Menu {
                        Button(action: {}) {
                            Label("League Settings", systemImage: "gear")
                        }
                        Button(action: {}) {
                            Label("Members", systemImage: "person.2")
                        }
                    } label: {
                        Image(systemName: "ellipsis.circle")
                            .foregroundColor(AppColors.primary)
                    }
                }
            }
            .onAppear {
                viewModel.loadMessages(leagueId: leagueId)
            }
        }
    }
    
    private var messageInput: some View {
        VStack(spacing: 0) {
            Divider()
                .background(AppColors.textMuted)
            
            HStack(spacing: AppSpacing.md) {
                // Attachment button
                Button(action: {}) {
                    Image(systemName: "plus.circle.fill")
                        .font(.system(size: 24))
                        .foregroundColor(AppColors.textMuted)
                }
                
                // Text field
                HStack {
                    TextField("Type a message...", text: $viewModel.newMessage, axis: .vertical)
                        .lineLimit(1...5)
                        .foregroundColor(AppColors.textPrimary)
                }
                .padding(.horizontal, AppSpacing.md)
                .padding(.vertical, AppSpacing.sm)
                .background(AppColors.surface)
                .cornerRadius(20)
                
                // Send button
                Button(action: { viewModel.sendMessage(leagueId: leagueId) }) {
                    Image(systemName: "paperplane.fill")
                        .font(.system(size: 20))
                        .foregroundColor(viewModel.newMessage.isEmpty ? AppColors.textMuted : AppColors.primary)
                }
                .disabled(viewModel.newMessage.isEmpty)
            }
            .padding(AppSpacing.md)
            .background(AppColors.card)
        }
    }
}

// MARK: - Chat Message Row
struct ChatMessageRow: View {
    let message: ChatMessage
    let isOwn: Bool
    
    var body: some View {
        HStack(alignment: .bottom, spacing: AppSpacing.sm) {
            if isOwn { Spacer() }
            
            if !isOwn {
                // Avatar
                Circle()
                    .fill(AppColors.primary.opacity(0.3))
                    .frame(width: 32, height: 32)
                    .overlay(
                        Text(String(message.userName.prefix(1)))
                            .font(AppFonts.small)
                            .fontWeight(.bold)
                            .foregroundColor(AppColors.primary)
                    )
            }
            
            VStack(alignment: isOwn ? .trailing : .leading, spacing: AppSpacing.xs) {
                if !isOwn {
                    Text(message.userName)
                        .font(AppFonts.caption)
                        .fontWeight(.semibold)
                        .foregroundColor(AppColors.textSecondary)
                }
                
                VStack(alignment: isOwn ? .trailing : .leading, spacing: 2) {
                    Text(message.text)
                        .font(AppFonts.body)
                        .foregroundColor(isOwn ? .white : AppColors.textPrimary)
                        .padding(.horizontal, AppSpacing.md)
                        .padding(.vertical, AppSpacing.sm)
                        .background(isOwn ? AppColors.primary : AppColors.surface)
                        .cornerRadius(16)
                    
                    Text(formatTime(message.timestamp))
                        .font(AppFonts.small)
                        .foregroundColor(AppColors.textMuted)
                }
            }
            
            if !isOwn { Spacer() }
        }
    }
    
    private func formatTime(_ date: Date) -> String {
        let formatter = DateFormatter()
        formatter.timeStyle = .short
        return formatter.string(from: date)
    }
}

// MARK: - Chat View Model
@MainActor
class ChatViewModel: ObservableObject {
    @Published var messages: [ChatMessage] = []
    @Published var newMessage = ""
    @Published var isLoading = false
    
    let currentUserId = "user-123" // Would come from auth
    
    init() {
        loadMockMessages()
    }
    
    func loadMessages(leagueId: String) {
        isLoading = true
        // Simulate API call
        DispatchQueue.main.asyncAfter(deadline: .now() + 0.5) {
            self.loadMockMessages()
            self.isLoading = false
        }
    }
    
    func sendMessage(leagueId: String) {
        guard !newMessage.isEmpty else { return }
        
        let message = ChatMessage(
            id: UUID().uuidString,
            leagueId: leagueId,
            userId: currentUserId,
            userName: "You",
            text: newMessage,
            timestamp: Date()
        )
        
        messages.append(message)
        newMessage = ""
    }
    
    private func loadMockMessages() {
        messages = [
            ChatMessage(id: "1", leagueId: "1", userId: "user-1", userName: "Rohit", text: "Hey everyone! Ready for the auction?", timestamp: Date().addingTimeInterval(-3600)),
            ChatMessage(id: "2", leagueId: "1", userId: "user-2", userName: "Virat", text: "Yes! I've been preparing my strategy", timestamp: Date().addingTimeInterval(-3000)),
            ChatMessage(id: "3", leagueId: "1", userId: "user-3", userName: "Jasprit", text: "Good luck everyone! May the best team win 🏏", timestamp: Date().addingTimeInterval(-2400)),
            ChatMessage(id: "4", leagueId: "1", userId: "user-1", userName: "Rohit", text: "Who's going for Bumrah first?", timestamp: Date().addingTimeInterval(-1800)),
            ChatMessage(id: "5", leagueId: "1", userId: "user-4", userName: "Hardik", text: "I'll bid high for him!", timestamp: Date().addingTimeInterval(-1200)),
            ChatMessage(id: "6", leagueId: "1", userId: "user-2", userName: "Virat", text: "Draft starts at 7pm sharp", timestamp: Date().addingTimeInterval(-600)),
        ]
    }
}

// MARK: - Chat Message Model
struct ChatMessage: Identifiable {
    let id: String
    let leagueId: String
    let userId: String
    let userName: String
    let text: String
    let timestamp: Date
}
