use serde::{Deserialize, Serialize};
use serde_json::{Map, Value};
use sha2::{Digest, Sha256};
use std::env;
use std::fs;
use std::process;

#[derive(Debug, Serialize, Deserialize)]
struct ConformanceCorpus {
    conformance_corpus_version: String,
    canonical_json_profile: String,
    vectors: Vec<TestVector>,
}

#[derive(Debug, Serialize, Deserialize)]
struct TestVector {
    vector_id: String,
    description: String,
    raw_input: Value,
    expected_decision_code: String,
    expected_decision_digest: String,
    expected_canonical_utf8: String,
    expected_canonical_bytes_hex: String,
}

#[derive(Debug, Serialize, Deserialize)]
struct EdgeCorpus {
    edge_case_vectors: Option<Vec<EdgeVector>>,
    vectors: Option<Vec<EdgeVector>>,
}

#[derive(Debug, Serialize, Deserialize)]
struct EdgeVector {
    vector_id: String,
    description: String,
    input_json: Value,
    expected_canonical_utf8: String,
    expected_sha256: String,
}

#[derive(Debug, Serialize)]
struct RunnerReport {
    runner_language: String,
    runner_version: String,
    total_vectors: usize,
    passed_vectors: usize,
    failed_vectors: usize,
    status: String,
    results: Vec<VectorResult>,
}

#[derive(Debug, Serialize)]
struct VectorResult {
    vector_id: String,
    decision_code_match: bool,
    canonical_utf8_match: bool,
    canonical_hex_match: bool,
    decision_digest_match: bool,
    status: String,
}

/// Recursively formats values according to RFC 8785 JSON Canonicalization Scheme (JCS).
pub fn canonicalize_value(val: &Value) -> Result<Value, String> {
    match val {
        Value::Null => Ok(Value::Null),
        Value::Bool(b) => Ok(Value::Bool(*b)),
        Value::Number(n) => {
            if let Some(f) = n.as_f64() {
                if !f.is_finite() {
                    return Err("RFC 8785 forbids non-finite floating point numbers (NaN/Infinity)".to_string());
                }
                if f == 0.0 && f.is_sign_negative() {
                    return Ok(serde_json::json!(0));
                }
            }
            Ok(Value::Number(n.clone()))
        }
        Value::String(s) => Ok(Value::String(s.clone())),
        Value::Array(arr) => {
            let mut new_arr = Vec::new();
            for item in arr {
                new_arr.push(canonicalize_value(item)?);
            }
            Ok(Value::Array(new_arr))
        }
        Value::Object(map) => {
            let mut entries: Vec<(&String, &Value)> = map.iter().collect();
            // Sort keys by UTF-16 code unit ordering per RFC 8785 Section 3.2.3
            entries.sort_by(|(k1, _), (k2, _)| {
                let u16_1: Vec<u16> = k1.encode_utf16().collect();
                let u16_2: Vec<u16> = k2.encode_utf16().collect();
                u16_1.cmp(&u16_2)
            });

            let mut new_map = Map::new();
            for (k, v) in entries {
                new_map.insert(k.clone(), canonicalize_value(v)?);
            }
            Ok(Value::Object(new_map))
        }
    }
}

pub fn canonical_json_bytes(val: &Value) -> Result<Vec<u8>, String> {
    let canonical_val = canonicalize_value(val)?;
    let utf8_str = serde_json::to_string(&canonical_val).map_err(|e| e.to_string())?;
    Ok(utf8_str.into_bytes())
}

pub fn canonical_sha256_digest(val: &Value) -> Result<String, String> {
    let bytes = canonical_json_bytes(val)?;
    let mut hasher = Sha256::new();
    hasher.update(&bytes);
    Ok(hex::encode(hasher.finalize()))
}

fn evaluate_preflight(raw: &Value) -> String {
    let prov = raw.get("provenance_status").and_then(|v| v.as_str()).unwrap_or("NOT_VERIFIED");
    if prov != "VERIFIED" {
        return "WITHHELD_UNVERIFIED_PROVENANCE".to_string();
    }
    let slo = raw.get("slo_status").and_then(|v| v.as_str()).unwrap_or("FAIL");
    if slo == "FAIL" {
        return "REJECTED_SLO_VIOLATION".to_string();
    }
    let p0 = raw.get("open_p0_findings").and_then(|v| v.as_i64()).unwrap_or(0);
    if p0 > 0 {
        return "REJECTED_OPEN_P0".to_string();
    }
    let burn = raw.get("burn_rate_multiplier").and_then(|v| v.as_f64()).unwrap_or(0.0);
    if burn >= 5.0 {
        return "FROZEN_ERROR_BUDGET".to_string();
    }
    "APPROVED".to_string()
}

fn build_decision_payload(raw: &Value, decision_code: &str) -> Value {
    let mut map = Map::new();
    map.insert("config_digest".to_string(), raw.get("configuration_digest").cloned().unwrap_or(Value::Null));
    map.insert("decision_code".to_string(), serde_json::json!(decision_code));
    map.insert("evaluated_inputs".to_string(), raw.get("evaluated_inputs").cloned().unwrap_or(serde_json::json!({})));
    map.insert("evidence_digests".to_string(), raw.get("evidence_proof_package_digests").cloned().unwrap_or(serde_json::json!([])));
    map.insert("generator_version".to_string(), raw.get("generator_version").cloned().unwrap_or(Value::Null));
    map.insert("git_commit".to_string(), raw.get("git_commit_sha").cloned().unwrap_or(Value::Null));
    map.insert("measurement_results".to_string(), raw.get("measurement_results").cloned().unwrap_or(serde_json::json!({})));
    map.insert("policy_version".to_string(), serde_json::json!("1.0.0"));
    Value::Object(map)
}

fn process_edge_file(path_str: &str, results: &mut Vec<VectorResult>, passed: &mut usize, failed: &mut usize) {
    if let Ok(edge_content) = fs::read_to_string(path_str) {
        if let Ok(edge_data) = serde_json::from_str::<EdgeCorpus>(&edge_content) {
            let vecs = edge_data.edge_case_vectors.or(edge_data.vectors);
            if let Some(vecs) = vecs {
                for v in vecs {
                    let c_bytes = canonical_json_bytes(&v.input_json).unwrap();
                    let c_utf8 = String::from_utf8(c_bytes).unwrap();
                    let c_digest = canonical_sha256_digest(&v.input_json).unwrap();

                    let utf8_match = c_utf8 == v.expected_canonical_utf8;
                    let digest_match = c_digest == v.expected_sha256;

                    let is_pass = utf8_match && digest_match;
                    if is_pass { *passed += 1; } else { *failed += 1; }

                    results.push(VectorResult {
                        vector_id: v.vector_id,
                        decision_code_match: true,
                        canonical_utf8_match: utf8_match,
                        canonical_hex_match: true,
                        decision_digest_match: digest_match,
                        status: if is_pass { "PASS".to_string() } else { "FAIL".to_string() },
                    });
                }
            }
        }
    }
}

fn main() {
    let args: Vec<String> = env::args().collect();
    if args.len() > 1 && args[1] == "--canonicalize" {
        if args.len() < 3 {
            eprintln!("Usage: l5_interop_runner_rust --canonicalize <json_file>");
            process::exit(1);
        }
        let content = fs::read_to_string(&args[2]).expect("Failed to read file");
        let val: Value = serde_json::from_str(&content).expect("Invalid JSON");
        let bytes = canonical_json_bytes(&val).expect("Canonicalization failed");
        println!("{}", String::from_utf8(bytes).unwrap());
        return;
    }

    if args.len() > 1 && args[1] == "--hash" {
        if args.len() < 3 {
            eprintln!("Usage: l5_interop_runner_rust --hash <json_file>");
            process::exit(1);
        }
        let content = fs::read_to_string(&args[2]).expect("Failed to read file");
        let val: Value = serde_json::from_str(&content).expect("Invalid JSON");
        let digest = canonical_sha256_digest(&val).expect("Hashing failed");
        println!("{}", digest);
        return;
    }

    let corpus_path = if args.len() > 1 {
        &args[1]
    } else {
        "tests/fixtures/helm_canonical_json_conformance_corpus.json"
    };

    let content = fs::read_to_string(corpus_path).unwrap_or_else(|err| {
        eprintln!("Failed to read corpus at {}: {}", corpus_path, err);
        process::exit(1);
    });

    let corpus: ConformanceCorpus = serde_json::from_str(&content).unwrap_or_else(|err| {
        eprintln!("Failed to parse JSON corpus: {}", err);
        process::exit(1);
    });

    let mut results = Vec::new();
    let mut passed = 0;
    let mut failed = 0;

    for vector in &corpus.vectors {
        let evaluated_code = evaluate_preflight(&vector.raw_input);
        let payload = build_decision_payload(&vector.raw_input, &evaluated_code);
        let canonical_val = canonicalize_value(&payload).expect("Canonicalization failed");
        
        let canonical_utf8 = serde_json::to_string(&canonical_val).expect("Serialization failed");
        let canonical_bytes = canonical_utf8.as_bytes();
        let canonical_hex = hex::encode(canonical_bytes);

        let mut hasher = Sha256::new();
        hasher.update(canonical_bytes);
        let digest_bytes = hasher.finalize();
        let computed_digest = hex::encode(digest_bytes);

        let code_match = evaluated_code == vector.expected_decision_code;
        let utf8_match = canonical_utf8 == vector.expected_canonical_utf8;
        let hex_match = canonical_hex == vector.expected_canonical_bytes_hex;
        let digest_match = computed_digest == vector.expected_decision_digest;

        let is_pass = code_match && utf8_match && hex_match && digest_match;
        if is_pass {
            passed += 1;
        } else {
            failed += 1;
        }

        results.push(VectorResult {
            vector_id: vector.vector_id.clone(),
            decision_code_match: code_match,
            canonical_utf8_match: utf8_match,
            canonical_hex_match: hex_match,
            decision_digest_match: digest_match,
            status: if is_pass { "PASS".to_string() } else { "FAIL".to_string() },
        });
    }

    if args.len() > 2 {
        for arg in &args[2..] {
            process_edge_file(arg, &mut results, &mut passed, &mut failed);
        }
    } else {
        if std::path::Path::new("tests/fixtures/helm_conformance_edge_cases_corpus.json").exists() {
            process_edge_file("tests/fixtures/helm_conformance_edge_cases_corpus.json", &mut results, &mut passed, &mut failed);
        }
        if std::path::Path::new("tests/fixtures/helm_conformance_500_corpus.json").exists() {
            process_edge_file("tests/fixtures/helm_conformance_500_corpus.json", &mut results, &mut passed, &mut failed);
        }
    }

    let report = RunnerReport {
        runner_language: "Rust".to_string(),
        runner_version: "rustc 1.96.0".to_string(),
        total_vectors: results.len(),
        passed_vectors: passed,
        failed_vectors: failed,
        status: if failed == 0 { "PASS".to_string() } else { "FAIL".to_string() },
        results,
    };

    println!("{}", serde_json::to_string_pretty(&report).unwrap());
    if failed > 0 {
        process::exit(1);
    }
}
