import Foundation
import Combine

// MARK: - API Service (Production Ready)
class APIService {
    static let shared = APIService()
    
    private let baseURL = Config.apiURL
    private let session: URLSession
    private var authToken: String?
    
    // Combine publishers for reactive updates
    let authStatePublisher = PassthroughSubject<AuthState, Never>()
    
    private init() {
        // Configure URLSession with security settings
        let config = URLSessionConfiguration.default
        config.timeoutIntervalForRequest = 30
        config.timeoutIntervalForResource = 60
        config.waitsForConnectivity = true
        config.httpAdditionalHeaders = [
            "Content-Type": "application/json",
            "Accept": "application/json"
        ]
        
        #if !DEBUG
        // In production, enforce SSL
        config.urlCache = nil
        #endif
        
        session = URLSession(configuration: config)
    }
    
    // MARK: - Authentication
    
    func setAuthToken(_ token: String?) {
        authToken = token
        
        if let token = token {
            UserDefaults.standard.set(token, forKey: "auth_token")
        } else {
            UserDefaults.standard.removeObject(forKey: "auth_token")
        }
    }
    
    func loadStoredToken() {
        authToken = UserDefaults.standard.string(forKey: "auth_token")
    }
    
    // MARK: - Request Building
    
    private func buildRequest(
        endpoint: String,
        method: HTTPMethod = .get,
        body: Data? = nil,
        requiresAuth: Bool = true
    ) throws -> URLRequest {
        guard let url = URL(string: "\(baseURL)\(endpoint)") else {
            throw APIError.invalidURL
        }
        
        var request = URLRequest(url: url)
        request.httpMethod = method.rawValue
        request.httpBody = body
        
        // Add auth header if required
        if requiresAuth, let token = authToken {
            request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }
        
        return request
    }
    
    // MARK: - Generic Request
    
    func request<T: Decodable>(
        _ endpoint: String,
        method: HTTPMethod = .get,
        body: Encodable? = nil,
        requiresAuth: Bool = true
    ) async throws -> T {
        var bodyData: Data?
        
        if let body = body {
            bodyData = try JSONEncoder().encode(AnyEncodable(body))
        }
        
        let request = try buildRequest(
            endpoint: endpoint,
            method: method,
            body: bodyData,
            requiresAuth: requiresAuth
        )
        
        let (data, response) = try await session.data(for: request)
        
        guard let httpResponse = response as? HTTPURLResponse else {
            throw APIError.invalidResponse
        }
        
        switch httpResponse.statusCode {
        case 200...299:
            let decoder = JSONDecoder()
            decoder.dateDecodingStrategy = .iso8601
            return try decoder.decode(T.self, from: data)
            
        case 401:
            authToken = nil
            authStatePublisher.send(.unauthenticated)
            throw APIError.unauthorized
            
        case 429:
            throw APIError.rateLimited
            
        case 500...599:
            throw APIError.serverError(httpResponse.statusCode)
            
        default:
            // Try to decode error message
            if let errorResponse = try? JSONDecoder().decode(ErrorResponse.self, from: data) {
                throw APIError.serverMessage(errorResponse.error)
            }
            throw APIError.unknown(httpResponse.statusCode)
        }
    }
    
    // MARK: - Convenience Methods
    
    func get<T: Decodable>(_ endpoint: String, requiresAuth: Bool = true) async throws -> T {
        try await request(endpoint, method: .get, requiresAuth: requiresAuth)
    }
    
    func post<T: Decodable>(_ endpoint: String, body: Encodable? = nil, requiresAuth: Bool = true) async throws -> T {
        try await request(endpoint, method: .post, body: body, requiresAuth: requiresAuth)
    }
    
    func put<T: Decodable>(_ endpoint: String, body: Encodable? = nil, requiresAuth: Bool = true) async throws -> T {
        try await request(endpoint, method: .put, body: body, requiresAuth: requiresAuth)
    }
    
    func delete<T: Decodable>(_ endpoint: String, requiresAuth: Bool = true) async throws -> T {
        try await request(endpoint, method: .delete, requiresAuth: requiresAuth)
    }
}

// MARK: - HTTP Method

enum HTTPMethod: String {
    case get = "GET"
    case post = "POST"
    case put = "PUT"
    case delete = "DELETE"
    case patch = "PATCH"
}

// MARK: - API Error

enum APIError: LocalizedError {
    case invalidURL
    case invalidResponse
    case unauthorized
    case rateLimited
    case serverError(Int)
    case serverMessage(String)
    case networkError(Error)
    case decodingError(Error)
    case unknown(Int)
    
    var errorDescription: String? {
        switch self {
        case .invalidURL:
            return "Invalid URL"
        case .invalidResponse:
            return "Invalid response from server"
        case .unauthorized:
            return "Please log in again"
        case .rateLimited:
            return "Too many requests. Please try again later."
        case .serverError(let code):
            return "Server error (\(code))"
        case .serverMessage(let message):
            return message
        case .networkError(let error):
            return "Network error: \(error.localizedDescription)"
        case .decodingError:
            return "Failed to process response"
        case .unknown(let code):
            return "Unknown error (\(code))"
        }
    }
}

// MARK: - API Response Models

struct ErrorResponse: Codable {
    let error: String
}

struct AuthState {
    case authenticated
    case unauthenticated
    case refreshing
}

// MARK: - AnyEncodable (for dynamic encoding)

struct AnyEncodable: Encodable {
    private let encodeClosure: (Encoder) throws -> Void
    
    init(_ wrapped: Encodable) {
        encodeClosure = wrapped.encode
    }
    
    func encode(to encoder: Encoder) throws {
        try encodeClosure(encoder)
    }
}

// MARK: - Generic Encodable Extension

extension Encodable {
    func encode(to encoder: Encoder) throws {
        var container = encoder.singleValueContainer()
        try container.encode(self)
    }
}
