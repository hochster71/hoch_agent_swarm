import Foundation
import AppIntents

struct ListOnlineAgentsIntent: AppIntent {
    static var title: LocalizedStringResource = "List Online Agents"
    static var description = IntentDescription("Lists all active workspace agents in the swarm.")
    
    func perform() async throws -> some IntentResult & ReturnsValue<String> {
        let client = HELMVoiceClient()
        let resultString = try await withCheckedThrowingContinuation { (continuation: CheckedContinuation<String, Error>) in
            client.sendVoiceRequest(intent: "helm.agents.online", utterance: "agents online") { result in
                switch result {
                case .success(let response):
                    continuation.resume(returning: response.speechResponse)
                case .failure(let err):
                    continuation.resume(throwing: err)
                }
            }
        }
        return .result(value: resultString)
    }
}
