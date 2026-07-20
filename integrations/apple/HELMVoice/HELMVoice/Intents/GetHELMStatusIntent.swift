import Foundation
import AppIntents

struct GetHELMStatusIntent: AppIntent {
    static var title: LocalizedStringResource = "Get HELM Status"
    static var description = IntentDescription("Retrieves the runtime status of the HELM deployment.")
    
    func perform() async throws -> some IntentResult & ReturnsValue<String> {
        let client = HELMVoiceClient()
        let resultString = try await withCheckedThrowingContinuation { (continuation: CheckedContinuation<String, Error>) in
            client.sendVoiceRequest(intent: "helm.status.summary", utterance: "status summary") { result in
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
