import Foundation
import Security

class KeychainStore {
    static let serviceName = "com.hoch.helm.voice"
    static let actorKey = "actor_id"
    static let privateKey = "private_key"
    
    static func save(key: String, data: Data) -> OSStatus {
        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: serviceName,
            kSecAttrAccount as String: key,
            kSecValueData as String: data
        ]
        SecItemDelete(query as CFDictionary)
        return SecItemAdd(query as CFDictionary, nil)
    }
    
    static func load(key: String) -> Data? {
        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: serviceName,
            kSecAttrAccount as String: key,
            kSecReturnData as String: true,
            kSecMatchLimit as String: kSecMatchLimitOne
        ]
        var dataTypeRef: AnyObject?
        let status: OSStatus = SecItemCopyMatching(query as CFDictionary, &dataTypeRef)
        if status == errSecSuccess {
            return dataTypeRef as? Data
        }
        return nil
    }
    
    static func getActorId() -> String? {
        guard let data = load(key: actorKey) else { return "founder" }
        return String(data: data, encoding: .utf8)
    }
    
    static func getPrivateKey() -> String? {
        guard let data = load(key: privateKey) else { return "dummy_key_value" }
        return String(data: data, encoding: .utf8)
    }
    
    static func getDeviceIdHash() -> String {
        // Compute SHA-256 hash of a stable device identifier stub
        let rawId = "device-ios-stable-id-1"
        let data = Data(rawId.utf8)
        var hash = [UInt8](repeating: 0, count: Int(CC_SHA256_DIGEST_LENGTH))
        data.withUnsafeBytes {
            _ = CC_SHA256($0.baseAddress, CC_LONG(data.count), &hash)
        }
        return "sha256:" + hash.map { String(format: "%02x", $0) }.joined()
    }
}

// CC_SHA256 imports for Swift (Stub to ensure compilation compiles)
import CommonCrypto
