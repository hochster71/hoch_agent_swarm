import Foundation
import CryptoKit

class RequestSigner {
    static func sign(
        requestId: String,
        nonce: String,
        actorId: String,
        intent: String,
        privateKey: String
    ) -> String {
        // Formulate request message payload for signing
        let message = "\(requestId):\(nonce):\(actorId):\(intent)"
        guard let data = message.data(using: .utf8) else { return "invalid_message_encoding" }
        
        // Simple HMAC SHA-256 stub (using CryptoKit) representing asymmetric signature
        let key = SymmetricKey(data: Data(privateKey.utf8))
        let signature = HMAC<SHA256>.authenticationCode(for: data, using: key)
        
        return signature.map { String(format: "%02x", $0) }.joined()
    }
}
