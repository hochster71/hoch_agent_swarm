import Foundation

struct VoiceRequest: Codable {
    let requestId: String
    let provider: String
    let deviceIdHash: String
    let actorId: String
    let sessionId: String
    let timestamp: String
    let intent: String
    let parameters: [String: String]
    let utteranceRedacted: String
    let authenticationContext: AuthContext
    let confirmation: ConfirmationContext
    let nonce: String
    let signature: String
    let schemaVersion: String

    enum CodingKeys: String, CodingKey {
        case requestId = "request_id"
        case provider
        case deviceIdHash = "device_id_hash"
        case actorId = "actor_id"
        case sessionId = "session_id"
        case timestamp
        case intent
        case parameters
        case utteranceRedacted = "utterance_redacted"
        case authenticationContext = "authentication_context"
        case confirmation
        case nonce
        case signature
        case schemaVersion = "schema_version"
    }
}

struct AuthContext: Codable {
    let method: String
    let assuranceLevel: String

    enum CodingKeys: String, CodingKey {
        case method
        case assuranceLevel = "assurance_level"
    }
}

struct ConfirmationContext: Codable {
    let required: Bool
    let challengeId: String?
    let confirmed: Bool

    enum CodingKeys: String, CodingKey {
        case required
        case challengeId = "challenge_id"
        case confirmed
    }
}
