import Foundation
import AppIntents

struct EnableOperatorHoldIntent: AppIntent {
    static var title: LocalizedStringResource = "Enable HELM Operator Hold"
    static var description = IntentDescription("Places the HELM system on operator hold, blocking write operations.")
    
    func perform() async throws -> some IntentResult & ReturnsValue<String> {
        let client = HELMVoiceClient()
        
        let authSuccess = try await withCheckedThrowingContinuation { (continuation: CheckedContinuation<Bool, Error>) in
            DeviceAuthentication.authenticateOwner(reason: "Authorize placing HELM on operator hold") { success, error in
                if let error = error {
                    continuation.resume(throwing: error)
                } else {
                    continuation.resume(returning: success)
                }
            }
        }
        
        guard authSuccess else {
            return .result(value: "Biometric authentication failed. Request denied.")
        }
        
        let resultString = try await withCheckedThrowingContinuation { (continuation: CheckedContinuation<String, Error>) in
            client.sendVoiceRequest(intent: "helm.operator_hold.enable", utterance: "enable operator hold") { result in
                switch result {
                case .success(let response):
                    if response.confirmationRequired {
                        continuation.resume(returning: "Biometrics accepted. Confirmation required. Please speak the 3 digit code sent to your session. Challenge code is \(response.challengeId ?? "")")
                    } else {
                        continuation.resume(returning: response.speechResponse)
                    }
                case .failure(let err):
                    continuation.resume(throwing: err)
                }
            }
        }
        return .result(value: resultString)
    }
}
