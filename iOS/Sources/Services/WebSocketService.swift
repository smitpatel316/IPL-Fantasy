import Foundation
import Starscream

// MARK: - WebSocket Service
final class WebSocketService: WebSocketDelegate {
    static let shared = WebSocketService()
    
    private var socket: WebSocket?
    private var isConnected = false
    private var reconnectAttempts = 0
    private let maxReconnectAttempts = 5
    
    // Event handlers
    var onBidUpdate: ((BidUpdate) -> Void)?
    var onDraftSold: ((DraftSold) -> Void)?
    var onChatMessage: ((ChatMessage) -> Void)?
    var onTradeUpdate: ((TradeUpdate) -> Void)?
    var onMatchUpdate: ((MatchUpdate) -> Void)?
    var onConnectionStatus: ((Bool) -> Void)?
    
    private init() {}
    
    // MARK: - Connection Management
    
    func connect(token: String) {
        guard socket == nil || !isConnected else { return }
        
        var request = URLRequest(url: URL(string: "\(Config.wsURL)")!)
        request.timeoutInterval = 10
        request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        
        socket = WebSocket(request: request)
        socket?.delegate = self
        socket?.connect()
    }
    
    func disconnect() {
        socket?.disconnect()
        socket = nil
        isConnected = false
    }
    
    // MARK: - Join Rooms
    
    func joinLeagueRoom(leagueId: String) {
        send(event: "join:league", payload: ["leagueId": leagueId])
    }
    
    func leaveLeagueRoom(leagueId: String) {
        send(event: "leave:league", payload: ["leagueId": leagueId])
    }
    
    // MARK: - Send Events
    
    private func send(event: String, payload: [String: Any] = [:]) {
        let message: [String: Any] = [
            "event": event,
            "payload": payload
        ]
        
        if let data = try? JSONSerialization.data(withJSONObject: message),
           let string = String(data: data, encoding: .utf8) {
            socket?.write(string: string)
        }
    }
    
    // MARK: - WebSocketDelegate
    
    func didReceive(event: WebSocketEvent, client: any WebSocketClient) {
        switch event {
        case .connected(_):
            isConnected = true
            reconnectAttempts = 0
            onConnectionStatus?(true)
            print("WebSocket connected")
            
        case .disconnected(let reason, let code):
            isConnected = false
            onConnectionStatus?(false)
            print("WebSocket disconnected: \(reason) (\(code))")
            attemptReconnect()
            
        case .text(let string):
            handleMessage(string)
            
        case .binary(let data):
            if let string = String(data: data, encoding: .utf8) {
                handleMessage(string)
            }
            
        case .error(let error):
            print("WebSocket error: \(String(describing: error))")
            attemptReconnect()
            
        case .cancelled:
            isConnected = false
            onConnectionStatus?(false)
            
        default:
            break
        }
    }
    
    // MARK: - Message Handling
    
    private func handleMessage(_ string: String) {
        guard let data = string.data(using: .utf8),
              let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
              let event = json["event"] as? String,
              let payload = json["payload"] as? [String: Any] else {
            return
        }
        
        switch event {
        case "draft:bid":
            if let bidData = try? JSONSerialization.data(withJSONObject: payload),
               let bid = try? JSONDecoder().decode(BidUpdate.self, from: bidData) {
                onBidUpdate?(bid)
            }
            
        case "draft:sold":
            if let soldData = try? JSONSerialization.data(withJSONObject: payload),
               let sold = try? JSONDecoder().decode(DraftSold.self, from: soldData) {
                onDraftSold?(sold)
            }
            
        case "chat:message":
            if let chatData = try? JSONSerialization.data(withJSONObject: payload),
               let chat = try? JSONDecoder().decode(ChatMessage.self, from: chatData) {
                onChatMessage?(chat)
            }
            
        case "trade:update":
            if let tradeData = try? JSONSerialization.data(withJSONObject: payload),
               let trade = try? JSONDecoder().decode(TradeUpdate.self, from: tradeData) {
                onTradeUpdate?(trade)
            }
            
        case "match:update":
            if let matchData = try? JSONSerialization.data(withJSONObject: payload),
               let match = try? JSONDecoder().decode(MatchUpdate.self, from: matchData) {
                onMatchUpdate?(match)
            }
            
        default:
            break
        }
    }
    
    // MARK: - Reconnection
    
    private func attemptReconnect() {
        guard reconnectAttempts < maxReconnectAttempts else {
            print("Max reconnect attempts reached")
            return
        }
        
        reconnectAttempts += 1
        let delay = Double(reconnectAttempts) * 2.0 // Exponential backoff
        
        DispatchQueue.main.asyncAfter(deadline: .now() + delay) { [weak self] in
            self?.socket?.connect()
        }
    }
}

// MARK: - Event Models

struct BidUpdate: Codable {
    let amount: Double
    let bidder: BidderInfo
    
    struct BidderInfo: Codable {
        let id: String
        let teamName: String
    }
}

struct DraftSold: Codable {
    let playerId: String
    let soldTo: String
    let amount: Double
    let nextPlayer: PlayerInfo?
    let newBid: Double
    
    struct PlayerInfo: Codable {
        let id: String
        let name: String
        let role: String
        let team: String
        let basePrice: Double
    }
}

struct ChatMessage: Codable {
    let id: String
    let leagueId: String
    let userId: String
    let userName: String
    let text: String
    let timestamp: String
}

struct TradeUpdate: Codable {
    let tradeId: String
    let type: String // proposed, accepted, rejected
    let fromTeam: String
    let toTeam: String
}

struct MatchUpdate: Codable {
    let matchId: String
    let team1Score: String
    let team2Score: String
    let status: String
    let lastBall: String?
}

// MARK: - Config

enum Config {
    #if DEBUG
    static let apiURL = "http://localhost:3001"
    static let wsURL = "ws://localhost:3001"
    #else
    static let apiURL = "https://api.iplfantasy.com"
    static let wsURL = "wss://api.iplfantasy.com"
    #endif
}
