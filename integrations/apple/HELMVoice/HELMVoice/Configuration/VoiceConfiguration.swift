import Foundation

struct VoiceConfiguration {
    static let gatewayURL = URL(string: "https://127.0.0.1:8770/api/v1/helm/voice/request")!
    static let confirmationURL = URL(string: "https://127.0.0.1:8770/api/v1/helm/voice/confirm")!
    static let sessionURL = URL(string: "https://127.0.0.1:8770/api/v1/helm/voice/session")!
    static let connectionTimeout: TimeInterval = 10.0
    static let schemaVersion = "1.0.0"
}
