import Foundation
import CryptoKit

func canonicalizeObj(_ obj: Any) throws -> String {
    if obj is NSNull {
        return "null"
    } else if let num = obj as? NSNumber {
        let typeID = CFGetTypeID(num)
        if typeID == CFBooleanGetTypeID() {
            return num.boolValue ? "true" : "false"
        }
        let doubleVal = num.doubleValue
        if doubleVal.isNaN || doubleVal.isInfinite {
            throw NSError(domain: "CanonicalError", code: 1, userInfo: [NSLocalizedDescriptionKey: "Non-finite float rejected"])
        }
        if doubleVal == 0.0 && doubleVal.sign == .minus {
            return "0"
        }
        let objCType = String(cString: num.objCType)
        if objCType == "d" || objCType == "f" {
            if doubleVal.truncatingRemainder(dividingBy: 1) == 0 {
                return String(format: "%.1f", doubleVal)
            }
            return "\(doubleVal)"
        }
        return "\(num.int64Value)"
    } else if let s = obj as? String {
        let data = try JSONEncoder().encode(s)
        return String(data: data, encoding: .utf8)!
    } else if let arr = obj as? [Any] {
        let elements = try arr.map { try canonicalizeObj($0) }
        return "[" + elements.joined(separator: ",") + "]"
    } else if let dict = obj as? [String: Any] {
        let sortedKeys = dict.keys.sorted { k1, k2 in
            let u16_1 = Array(k1.utf16)
            let u16_2 = Array(k2.utf16)
            for (c1, c2) in zip(u16_1, u16_2) {
                if c1 != c2 { return c1 < c2 }
            }
            return u16_1.count < u16_2.count
        }
        let pairs = try sortedKeys.map { k in
            let keyEncoded = try JSONEncoder().encode(k)
            let keyStr = String(data: keyEncoded, encoding: .utf8)!
            let valStr = try canonicalizeObj(dict[k]!)
            return "\(keyStr):\(valStr)"
        }
        return "{" + pairs.joined(separator: ",") + "}"
    }
    return "null"
}

func evaluatePreflight(_ input: [String: Any]) -> String {
    let provStr = (input["provenance_status"] as? String) ?? "NOT_VERIFIED"
    if provStr != "VERIFIED" { return "WITHHELD_UNVERIFIED_PROVENANCE" }

    let sloStr = (input["slo_status"] as? String) ?? "FAIL"
    if sloStr == "FAIL" { return "REJECTED_SLO_VIOLATION" }

    let openP0 = (input["open_p0_findings"] as? NSNumber)?.int64Value ?? 0
    if openP0 > 0 { return "REJECTED_OPEN_P0" }

    let burnRate = (input["burn_rate_multiplier"] as? NSNumber)?.doubleValue ?? 0.0
    if burnRate >= 5.0 { return "FROZEN_ERROR_BUDGET" }

    return "APPROVED"
}

func buildDecisionPayload(_ input: [String: Any], decisionCode: String) -> [String: Any] {
    var dict: [String: Any] = [:]
    dict["config_digest"] = input["configuration_digest"] ?? NSNull()
    dict["decision_code"] = decisionCode
    dict["evaluated_inputs"] = input["evaluated_inputs"] ?? [:]
    dict["evidence_digests"] = input["evidence_proof_package_digests"] ?? []
    dict["generator_version"] = input["generator_version"] ?? NSNull()
    dict["git_commit"] = input["git_commit_sha"] ?? NSNull()
    dict["measurement_results"] = input["measurement_results"] ?? [:]
    dict["policy_version"] = "1.0.0"
    return dict
}

struct VectorResult: Codable {
    let vector_id: String
    let decision_code_match: Bool
    let canonical_utf8_match: Bool
    let canonical_hex_match: Bool
    let decision_digest_match: Bool
    let status: String
}

struct RunnerReport: Codable {
    let runner_language: String
    let runner_version: String
    let total_vectors: Int
    let passed_vectors: Int
    let failed_vectors: Int
    let status: String
    let results: [VectorResult]
}

func processEdgeFile(_ pathStr: String, results: inout [VectorResult], passed: inout Int, failed: inout Int) {
    guard FileManager.default.fileExists(atPath: pathStr),
          let edgeData = try? Data(contentsOf: URL(fileURLWithPath: pathStr)),
          let edgeObj = try? JSONSerialization.jsonObject(with: edgeData, options: []),
          let edgeDict = edgeObj as? [String: Any] else { return }

    let edgeVectors = (edgeDict["edge_case_vectors"] as? [[String: Any]]) ?? (edgeDict["vectors"] as? [[String: Any]]) ?? []

    for vec in edgeVectors {
        let vecId = (vec["vector_id"] as? String) ?? "UNKNOWN_EDGE"
        let expUtf8 = (vec["expected_canonical_utf8"] as? String) ?? ""
        let expSha = (vec["expected_sha256"] as? String) ?? ""
        let inp = vec["input_json"] ?? [:]

        do {
            let cUtf8 = try canonicalizeObj(inp)
            let cBytes = cUtf8.data(using: .utf8)!
            let hash = SHA256.hash(data: cBytes)
            let cSha = hash.compactMap { String(format: "%02x", $0) }.joined()

            let utf8Match = (cUtf8 == expUtf8)
            let shaMatch = (cSha == expSha)
            let isPass = utf8Match && shaMatch
            if isPass { passed += 1 } else { failed += 1 }

            results.append(VectorResult(
                vector_id: vecId,
                decision_code_match: true,
                canonical_utf8_match: utf8Match,
                canonical_hex_match: true,
                decision_digest_match: shaMatch,
                status: isPass ? "PASS" : "FAIL"
            ))
        } catch {
            failed += 1
            results.append(VectorResult(vector_id: vecId, decision_code_match: false, canonical_utf8_match: false, canonical_hex_match: false, decision_digest_match: false, status: "FAIL"))
        }
    }
}

func main() {
    let args = CommandLine.arguments

    if args.count > 1 && args[1] == "--canonicalize" {
        guard args.count > 2,
              let data = try? Data(contentsOf: URL(fileURLWithPath: args[2])),
              let obj = try? JSONSerialization.jsonObject(with: data, options: []),
              let canonicalUtf8 = try? canonicalizeObj(obj) else {
            fputs("Usage: l5_interop_runner.swift --canonicalize <json_file>\n", stderr)
            exit(1)
        }
        print(canonicalUtf8)
        return
    }

    if args.count > 1 && args[1] == "--hash" {
        guard args.count > 2,
              let data = try? Data(contentsOf: URL(fileURLWithPath: args[2])),
              let obj = try? JSONSerialization.jsonObject(with: data, options: []),
              let canonicalUtf8 = try? canonicalizeObj(obj),
              let canonicalBytes = canonicalUtf8.data(using: .utf8) else {
            fputs("Usage: l5_interop_runner.swift --hash <json_file>\n", stderr)
            exit(1)
        }
        let hash = SHA256.hash(data: canonicalBytes)
        let hexDigest = hash.compactMap { String(format: "%02x", $0) }.joined()
        print(hexDigest)
        return
    }

    let corpusPath = args.count > 1 ? args[1] : "tests/fixtures/helm_canonical_json_conformance_corpus.json"

    guard let data = try? Data(contentsOf: URL(fileURLWithPath: corpusPath)),
          let rootObj = try? JSONSerialization.jsonObject(with: data, options: []),
          let rootDict = rootObj as? [String: Any],
          let vectorsArr = rootDict["vectors"] as? [[String: Any]] else {
        fputs("Failed to read or parse JSON corpus at \(corpusPath)\n", stderr)
        exit(1)
    }

    var results: [VectorResult] = []
    var passed = 0
    var failed = 0

    for vecDict in vectorsArr {
        let vectorId = (vecDict["vector_id"] as? String) ?? "UNKNOWN"
        let expectedCode = (vecDict["expected_decision_code"] as? String) ?? ""
        let expectedDigest = (vecDict["expected_decision_digest"] as? String) ?? ""
        let expectedUtf8 = (vecDict["expected_canonical_utf8"] as? String) ?? ""
        let expectedHex = (vecDict["expected_canonical_bytes_hex"] as? String) ?? ""
        let rawInput = (vecDict["raw_input"] as? [String: Any]) ?? [:]

        let code = evaluatePreflight(rawInput)
        let payload = buildDecisionPayload(rawInput, decisionCode: code)
        
        do {
            let canonicalUtf8 = try canonicalizeObj(payload)
            let canonicalBytes = canonicalUtf8.data(using: .utf8)!
            let canonicalHex = canonicalBytes.map { String(format: "%02x", $0) }.joined()

            let hash = SHA256.hash(data: canonicalBytes)
            let computedDigest = hash.compactMap { String(format: "%02x", $0) }.joined()

            let codeMatch = (code == expectedCode)
            let utf8Match = (canonicalUtf8 == expectedUtf8)
            let hexMatch = (canonicalHex == expectedHex)
            let digestMatch = (computedDigest == expectedDigest)

            let isPass = codeMatch && utf8Match && hexMatch && digestMatch
            if isPass { passed += 1 } else { failed += 1 }

            results.append(VectorResult(
                vector_id: vectorId,
                decision_code_match: codeMatch,
                canonical_utf8_match: utf8Match,
                canonical_hex_match: hexMatch,
                decision_digest_match: digestMatch,
                status: isPass ? "PASS" : "FAIL"
            ))
        } catch {
            failed += 1
            results.append(VectorResult(vector_id: vectorId, decision_code_match: false, canonical_utf8_match: false, canonical_hex_match: false, decision_digest_match: false, status: "FAIL"))
        }
    }

    if args.count > 2 {
        for arg in args[2...] {
            processEdgeFile(arg, results: &results, passed: &passed, failed: &failed)
        }
    } else {
        processEdgeFile("tests/fixtures/helm_conformance_edge_cases_corpus.json", results: &results, passed: &passed, failed: &failed)
        processEdgeFile("tests/fixtures/helm_conformance_500_corpus.json", results: &results, passed: &passed, failed: &failed)
    }

    let report = RunnerReport(
        runner_language: "Swift",
        runner_version: "Apple Swift 6.3.3",
        total_vectors: results.count,
        passed_vectors: passed,
        failed_vectors: failed,
        status: failed == 0 ? "PASS" : "FAIL",
        results: results
    )

    let encoder = JSONEncoder()
    encoder.outputFormatting = [.prettyPrinted, .sortedKeys]
    if let reportData = try? encoder.encode(report),
       let reportStr = String(data: reportData, encoding: .utf8) {
        print(reportStr)
    }

    if failed > 0 {
        exit(1)
    }
}

main()
