import Foundation

// MARK: - Result Type
/// A type that represents either a success or a failure
enum Result<Success, Failure: Error> {
    case success(Success)
    case failure(Failure)
    
    var isSuccess: Bool {
        if case .success = self { return true }
        return false
    }
    
    var isFailure: Bool {
        !isSuccess
    }
    
    func get() throws -> Success {
        switch self {
        case .success(let value):
            return value
        case .failure(let error):
            throw error
        }
    }
    
    func map<T>(_ transform: (Success) -> T) -> Result<T, Failure> {
        switch self {
        case .success(let value):
            return .success(transform(value))
        case .failure(let error):
            return .failure(error)
        }
    }
}

// MARK: - App Errors
enum AppError: LocalizedError {
    case networkError(underlying: Error)
    case serverError(code: Int, message: String)
    case validationError(field: String, message: String)
    case unauthorized
    case notFound
    case decodingError
    case unknown(message: String)
    
    var errorDescription: String? {
        switch self {
        case .networkError(let error):
            return "Network error: \(error.localizedDescription)"
        case .serverError(let code, let message):
            return "Server error (\(code)): \(message)"
        case .validationError(let field, let message):
            return "\(field): \(message)"
        case .unauthorized:
            return "Please log in again"
        case .notFound:
            return "Resource not found"
        case .decodingError:
            return "Failed to process data"
        case .unknown(let message):
            return message
        }
    }
    
    var isRecoverable: Bool {
        switch self {
        case .networkError, .serverError:
            return true
        case .unauthorized, .validationError, .notFound, .decodingError, .unknown:
            return false
        }
    }
}

// MARK: - Optional Extension
extension Optional where Wrapped: Collection {
    var isNilOrEmpty: Bool {
        self?.isEmpty ?? true
    }
}

extension Optional {
    func orThrow(_ error: Error) throws -> Wrapped {
        guard let value = self else {
            throw error
        }
        return value
    }
}

// MARK: - String Validation
extension String {
    var isValidEmail: Bool {
        let emailRegex = "[A-Z0-9a-z._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,64}"
        return NSPredicate(format: "SELF MATCHES %@", emailRegex).evaluate(with: self)
    }
    
    var isValidPassword: Bool {
        // At least 8 characters
        return count >= 8
    }
    
    var trimmed: String {
        trimmingCharacters(in: .whitespacesAndNewlines)
    }
    
    // Limit string length
    func truncated(to length: Int, trailing: String = "...") -> String {
        if count > length {
            return String(prefix(length)) + trailing
        }
        return self
    }
}

// MARK: - Array Safety
extension Array {
    subscript(safe index: Index) -> Element? {
        indices.contains(index) ? self[index] : nil
    }
}

// MARK: - Date Extensions
extension Date {
    var isToday: Bool {
        Calendar.current.isDateInToday(self)
    }
    
    var isYesterday: Bool {
        Calendar.current.isDateInYesterday(self)
    }
    
    func timeAgo() -> String {
        let formatter = RelativeDateTimeFormatter()
        formatter.unitsStyle = .abbreviated
        return formatter.localizedString(for: self, relativeTo: Date())
    }
}

// MARK: - Number Formatting
extension Int {
    var formatted: String {
        let formatter = NumberFormatter()
        formatter.numberStyle = .decimal
        return formatter.string(from: NSNumber(value: self)) ?? "\(self)"
    }
    
    var abbreviated: String {
        if self >= 1_000_000 {
            return "\(self / 1_000_000)M"
        } else if self >= 1_000 {
            return "\(self / 1_000)K"
        }
        return "\(self)"
    }
}

extension Double {
    var currencyFormatted: String {
        let formatter = NumberFormatter()
        formatter.numberStyle = .currency
        formatter.currencySymbol = "₹"
        formatter.maximumFractionDigits = 1
        return formatter.string(from: NSNumber(value: self)) ?? "₹\(self)"
    }
}

// MARK: - UserDefaults Keys
enum UserDefaultsKey: String {
    case authToken = "auth_token"
    case userId = "user_id"
    case userEmail = "user_email"
    case userName = "user_name"
    case darkMode = "dark_mode"
    case notificationsEnabled = "notifications_enabled"
    case lastSyncTime = "last_sync_time"
}

// MARK: - UserDefaults Helper
extension UserDefaults {
    func set<T: Encodable>(_ value: T, forKey key: UserDefaultsKey) {
        if let encoded = try? JSONEncoder().encode(value) {
            set(encoded, forKey: key.rawValue)
        }
    }
    
    func get<T: Decodable>(_ type: T.Type, forKey key: UserDefaultsKey) -> T? {
        guard let data = data(forKey: key.rawValue) else { return nil }
        return try? JSONDecoder().decode(type, from: data)
    }
    
    func remove(forKey key: UserDefaultsKey) {
        removeObject(forKey: key.rawValue)
    }
}

// MARK: - Debouncer
class Debouncer {
    private let delay: TimeInterval
    private var workItem: DispatchWorkItem?
    
    init(delay: TimeInterval) {
        self.delay = delay
    }
    
    func debounce(action: @escaping () -> Void) {
        workItem?.cancel()
        workItem = DispatchWorkItem(block: action)
        DispatchQueue.main.asyncAfter(deadline: .now() + delay, execute: workItem!)
    }
}

// MARK: - Throttler
class Throttler {
    private let interval: TimeInterval
    private var lastExecution: Date?
    
    init(interval: TimeInterval) {
        self.interval = interval
    }
    
    func throttle(action: @escaping () -> Void) {
        let now = Date()
        
        if let last = lastExecution, now.timeIntervalSince(last) < interval {
            return
        }
        
        lastExecution = now
        action()
    }
}

// MARK: - Retry Handler
actor RetryHandler {
    private let maxRetries: Int
    private let delay: TimeInterval
    
    init(maxRetries: Int = 3, delay: TimeInterval = 1.0) {
        self.maxRetries = maxRetries
        self.delay = delay
    }
    
    func retry<T>(
        maxAttempts: Int = 3,
        delay: TimeInterval = 1.0,
        operation: @escaping () async throws -> T
    ) async throws -> T {
        var lastError: Error?
        
        for attempt in 1...maxAttempts {
            do {
                return try await operation()
            } catch {
                lastError = error
                
                if attempt < maxAttempts {
                    try await Task.sleep(nanoseconds: UInt64(delay * 1_000_000_000))
                }
            }
        }
        
        throw lastError ?? RetryError.exhausted
    }
}

enum RetryError: Error {
    case exhausted
}

// MARK: - Weak Reference
class WeakRef<T: AnyObject> {
    weak var value: T?
    
    init(_ value: T) {
        self.value = value
    }
}
