# Local Model Worker Onboarding Evidence — mbpro (Offline Candidate)

This document records the onboarding and validation results for the local Ollama model worker `mbpro` at `10.0.0.115` as a candidate node for the Hoch Agent Swarm (HAS).

## 1. Network Reachability & Current Status

* **Status**: `candidate_offline`
* **IP Address**: `10.0.0.115`
* **Port**: `11434`

ICMP Ping requests and TCP connections to `10.0.0.115` are currently timing out. The node is registered as a candidate but remains inactive until network access is restored and the node is approved.

```bash
$ ping -c 3 10.0.0.115
PING 10.0.0.115 (10.0.0.115): 56 data bytes
Request timeout for icmp_seq 0
Request timeout for icmp_seq 1

--- 10.0.0.115 ping statistics ---
3 packets transmitted, 0 packets received, 100.0% packet loss
```

## 2. Ollama API Verification (Timeout Error)

The API is currently unreachable from the controller machine (`10.0.0.10`):

```bash
$ curl -fsS --connect-timeout 5 http://10.0.0.115:11434/api/tags
curl: (28) Failed to connect to 10.0.0.115 port 11434 after 5000 ms: Connection timed out
```

## 3. Required Action to Expose Ollama to the Swarm

To activate and promote this candidate node, the operator must execute the following on the MBPro (`10.0.0.115`) itself:

1. Ensure the Ollama daemon is running:
   ```bash
   ollama serve
   ```
2. Verify local connectivity:
   ```bash
   curl -fsS http://127.0.0.1:11434/api/tags | jq
   ```
3. Expose the service to the LAN:
   ```bash
   launchctl setenv OLLAMA_HOST "0.0.0.0:11434"
   pkill ollama || true
   ollama serve
   ```
4. Verify exposure from the HAS controller:
   ```bash
   curl -fsS http://10.0.0.115:11434/api/tags | jq
   ```

## 4. Node Candidate Record

The candidate record is preserved in the system configuration as:

```json
{
  "node_name": "mbpro",
  "host": "10.0.0.115",
  "ollama_base_url": "http://10.0.0.115:11434",
  "role": "local_model_worker",
  "trust_zone": "home_lan",
  "status": "candidate_offline",
  "approval_required": true,
  "routing_enabled": false,
  "models_observed": [
    "gemma3:4b",
    "llama3:8b",
    "llama3.1:8b"
  ],
  "last_good_generation_test": {
    "model": "llama3.1:8b",
    "response": "OK",
    "status": "pass"
  },
  "current_connectivity": {
    "status": "fail",
    "error": "curl timeout to http://10.0.0.115:11434/api/tags"
  }
}
```

No active routing is enabled for this node.
