import Foundation

struct VoiceResponse: Codable {
    let requestId: String
    let correlationId: String
    let status: String
    let executionId: String?
    let speechResponse: String
    let confirmationRequired: Bool
    let challengeId: String?
    let timestamp: String
    let error: String?

    enum CodingKeys: String, CodingKey {
        case requestId = "request_id"
        case correlationId = "correlation_id"
        case status
        case executionId = "execution_id"
        case speechResponse = "speech_response"
        case confirmationRequired = "confirmation_required"
        case challengeId = "challenge_id"
        case timestamp
        case error
    }
}
