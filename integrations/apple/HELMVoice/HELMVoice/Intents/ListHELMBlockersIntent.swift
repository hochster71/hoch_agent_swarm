import Foundation
import AppIntents

struct ListHELMBlockersIntent: AppIntent {
    static var title: LocalizedStringResource = "List HELM Blockers"
    static var description = IntentDescription("Lists any open blockers blocking HELM milestone promotion.")
    
    func perform() async throws -> some IntentResult & ReturnsValue<String> {
        let client = HELMVoiceClient()
        let resultString = try await withCheckedThrowingContinuation { (continuation: CheckedContinuation<String, Error>) in
            client.sendVoiceRequest(intent: "helm.blockers.list", utterance: "blockers list") { result in
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
