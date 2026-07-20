import Foundation
import AppIntents

struct RunHAFConMonIntent: AppIntent {
    static var title: LocalizedStringResource = "Run HELM Continuous Monitoring"
    static var description = IntentDescription("Triggers a live continuous monitoring assessment run.")
    
    func perform() async throws -> some IntentResult & ReturnsValue<String> {
        let client = HELMVoiceClient()
        
        // 1. Local Authentication (FaceID/TouchID)
        let authSuccess = try await withCheckedThrowingContinuation { (continuation: CheckedContinuation<Bool, Error>) in
            DeviceAuthentication.authenticateOwner(reason: "Authorize triggering live continuous monitoring") { success, error in
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
        
        // 2. Perform Request (First Step: requires confirmation code)
        let resultString = try await withCheckedThrowingContinuation { (continuation: CheckedContinuation<String, Error>) in
            client.sendVoiceRequest(intent: "helm.conmon.run", utterance: "run conmon") { result in
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
