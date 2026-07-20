import Foundation

struct VoiceTruthState: Codable {
    let sharedKernel: String
    let siriImplementation: String
    let siriOperational: String
    let alexaImplementation: String
    let alexaOperational: String
    let webVoiceImplementation: String
    let endToEndAssurance: String
    let lastLiveSiriEvent: String?
    let lastLiveAlexaEvent: String?

    enum CodingKeys: String, CodingKey {
        case sharedKernel = "shared_kernel"
        case siriImplementation = "siri_implementation"
        case siriOperational = "siri_operational"
        case alexaImplementation = "alexa_implementation"
        case alexaOperational = "alexa_operational"
        case webVoiceImplementation = "web_voice_implementation"
        case endToEndAssurance = "end_to_end_assurance"
        case lastLiveSiriEvent = "last_live_siri_event"
        case lastLiveAlexaEvent = "last_live_alexa_event"
    }
}
