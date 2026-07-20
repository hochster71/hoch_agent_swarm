import Foundation
import Combine

class HELMVoiceClient: ObservableObject {
    @Published var isConnected = false
    @Published var lastResponse: String = ""
    @Published var truthState: VoiceTruthState?
    
    private var cancellables = Set<AnyCancellable>()
    
    func sendVoiceRequest(
        intent: String,
        parameters: [String: String] = [:],
        utterance: String,
        confirmed: Bool = false,
        challengeId: String? = nil,
        completion: @escaping (Result<VoiceResponse, Error>) -> Void
    ) {
        let requestId = "REQ-" + UUID().uuidString.prefix(8)
        let sessionId = "SESS-IOS"
        let nonce = String(format: "%08d", arc4random_uniform(100000000))
        
        let actorId = KeychainStore.getActorId() ?? "founder"
        let privateKey = KeychainStore.getPrivateKey() ?? "dummy_key"
        
        let authContext = AuthContext(
            method: "app_attestation",
            assuranceLevel: "HIGH"
        )
        
        let confirmationContext = ConfirmationContext(
            required: challengeId != nil,
            challengeId: challengeId,
            confirmed: confirmed
        )
        
        let signature = RequestSigner.sign(
            requestId: requestId,
            nonce: nonce,
            actorId: actorId,
            intent: intent,
            privateKey: privateKey
        )
        
        let requestBody = VoiceRequest(
            requestId: requestId,
            provider: "SIRI",
            deviceIdHash: KeychainStore.getDeviceIdHash(),
            actorId: actorId,
            sessionId: sessionId,
            timestamp: ISO8601DateFormatter().string(from: Date()),
            intent: intent,
            parameters: parameters,
            utteranceRedacted: utterance,
            authenticationContext: authContext,
            confirmation: confirmationContext,
            nonce: nonce,
            signature: signature,
            schemaVersion: VoiceConfiguration.schemaVersion
        )
        
        var request = URLRequest(url: VoiceConfiguration.gatewayURL)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        
        do {
            request.httpBody = try JSONEncoder().encode(requestBody)
        } catch {
            completion(.failure(error))
            return
        }
        
        let session = URLSession(configuration: .default, delegate: TrustingURLSessionDelegate(), delegateQueue: nil)
        
        session.dataTask(with: request) { data, response, error in
            if let error = error {
                completion(.failure(error))
                return
            }
            guard let data = data else {
                completion(.failure(NSError(domain: "HELMVoice", code: -1, userInfo: [NSLocalizedDescriptionKey: "No data returned"])))
                return
            }
            do {
                let res = try JSONDecoder().decode(VoiceResponse.self, from: data)
                completion(.success(res))
            } catch {
                completion(.failure(error))
            }
        }.resume()
    }
    
    func confirmChallenge(sessionId: String, code: String, completion: @escaping (Result<Bool, Error>) -> Void) {
        var request = URLRequest(url: VoiceConfiguration.confirmationURL)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        
        let body: [String: String] = [
            "session_id": sessionId,
            "code": code
        ]
        
        do {
            request.httpBody = try JSONSerialization.data(withJSONObject: body)
        } catch {
            completion(.failure(error))
            return
        }
        
        let session = URLSession(configuration: .default, delegate: TrustingURLSessionDelegate(), delegateQueue: nil)
        session.dataTask(with: request) { data, response, error in
            if let error = error {
                completion(.failure(error))
                return
            }
            guard let httpResponse = response as? HTTPURLResponse, httpResponse.statusCode == 200 else {
                completion(.success(false))
                return
            }
            completion(.success(true))
        }.resume()
    }
}
