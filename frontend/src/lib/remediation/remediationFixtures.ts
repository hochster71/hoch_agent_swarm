import type { Runbook, RunbookExecution } from "./runbookTypes";

export const initialRunbooks: Runbook[] = [
  {
    runbook_id: "phishing-response",
    name: "Phishing Response Runbook",
    version: "v2.1.0",
    status: "approved",
    owner: "SecOps Team",
    risk: "low",
    trigger_conditions: ["Alert: Phishing Campaign Detected", "Incident: Phishing email reported"],
    steps: [
      { step_id: "pr-1", order: 1, type: "diagnostic", title: "Collect Evidence", description: "Fetch email headers, sender address, and trace server IPs.", requires_approval: false },
      { step_id: "pr-2", order: 2, type: "diagnostic", title: "Identify Scope", description: "Search logs to identify other tenants or users who received the campaign.", requires_approval: false },
      { step_id: "pr-3", order: 3, type: "command", title: "Quarantine Targets", description: "Delete campaign email from user inboxes across affected tenants.", command_text: "quarantine-emails --sender phishing@malicious-domain.com", requires_approval: false, rollback_step_id: "pr-3-rb" },
      { step_id: "pr-4", order: 4, type: "integration", title: "Notify Stakeholders", description: "Dispatch Slack warning cards and update the global incident tracker.", requires_approval: false },
      { step_id: "pr-5", order: 5, type: "verification", title: "Verify Recovery", description: "Ping affected mailboxes to verify that target emails are removed.", requires_approval: false }
    ],
    verification: {
      success_conditions: ["No target emails found in active client folders", "Sender domain blacklisted"],
      timeout_seconds: 300,
      evidence_refs_required: true
    }
  },
  {
    runbook_id: "privilege-reset",
    name: "Privilege Reset Runbook",
    version: "v2.3.1",
    status: "approved",
    owner: "Security Team",
    risk: "high",
    trigger_conditions: ["Alert: Privilege Escalation Detected", "Incident: Unauthorized API token creation"],
    steps: [
      { step_id: "pw-1", order: 1, type: "diagnostic", title: "Validate Incident Context", description: "Verify caller identity, check cryptographic signatures, and trace location.", requires_approval: false },
      { step_id: "pw-2", order: 2, type: "diagnostic", title: "Identify Affected Identities", description: "List credentials, key pairs, and roles accessed during the audit window.", requires_approval: false },
      { step_id: "pw-3", order: 3, type: "command", title: "Revoke Active Sessions", description: "Instantly force logout and clear session caches for the flagged accounts.", command_text: "revoke-user-sessions --target user-18231", requires_approval: true, rollback_step_id: "pw-3-rb" },
      { step_id: "pw-4", order: 4, type: "command", title: "Reset Credentials", description: "Rotate access keys and flags to require password/MFA update.", command_text: "reset-user-credentials --target user-18231 --force", requires_approval: true },
      { step_id: "pw-5", order: 5, type: "verification", title: "Verify Access State", description: "Confirm identity tokens block new requests until reset completed.", requires_approval: false }
    ],
    verification: {
      success_conditions: ["Active user tokens revoked", "Client session caches cleared", "MFA reset flag set"],
      timeout_seconds: 600,
      evidence_refs_required: true
    }
  },
  {
    runbook_id: "contain-isolate",
    name: "Contain & Isolate Runbook",
    version: "v2.8.0",
    status: "approved",
    owner: "Ops Team",
    risk: "high",
    trigger_conditions: ["Alert: Suspicious Data Exfiltration", "Incident: Extreme outbound socket usage"],
    steps: [
      { step_id: "co-1", order: 1, type: "diagnostic", title: "Analyze Socket Connections", description: "Trace destination IPs, data rates, and check domain ratings.", requires_approval: false },
      { step_id: "co-2", order: 2, type: "command", title: "Deploy Microsegmentation Rules", description: "Block outbound traffic to the destination IP using local firewall filters.", command_text: "block-destination-ip --ip 203.0.113.50", requires_approval: true, rollback_step_id: "co-2-rb" },
      { step_id: "co-3", order: 3, type: "command", title: "Isolate Docker Container", description: "Suspend Docker node container from the active cluster mesh.", command_text: "suspend-cluster-node --node W1", requires_approval: true, rollback_step_id: "co-3-rb" },
      { step_id: "co-4", order: 4, type: "verification", title: "Verify Outbound Data Rate", description: "Verify outbound bandwidth usage is restored below baseline.", requires_approval: false }
    ],
    verification: {
      success_conditions: ["Mesh node traffic blocked", "Outbound exfiltration rates zeroed out"],
      timeout_seconds: 400,
      evidence_refs_required: true
    }
  },
  {
    runbook_id: "malware-remediation",
    name: "Malware Remediation Runbook",
    version: "v3.1.0",
    status: "approved",
    owner: "Ops Team",
    risk: "high",
    trigger_conditions: ["Alert: Malware Detected on Host", "Incident: Host system file integrity breach"],
    steps: [
      { step_id: "mr-1", order: 1, type: "diagnostic", title: "Identify Malicious Process", description: "List active processes, CPU spikes, and trace filepath targets.", requires_approval: false },
      { step_id: "mr-2", order: 2, type: "command", title: "Terminate Host Process", description: "Kill the malicious PID and lock the parent directories.", command_text: "kill-process --pid 20932", requires_approval: true, rollback_step_id: "mr-2-rb" },
      { step_id: "mr-3", order: 3, type: "command", title: "Restore File Backup", description: "Prune affected directories and sync from local verified snapshots.", command_text: "restore-file-snapshot --target /opt/app/bin", requires_approval: true },
      { step_id: "mr-4", order: 4, type: "verification", title: "Execute Integrity Verify", description: "Re-run SHA-256 hash checksums on all directory assets.", requires_approval: false }
    ],
    verification: {
      success_conditions: ["Process killed", "Local filesystem check clean"],
      timeout_seconds: 600,
      evidence_refs_required: true
    }
  },
  {
    runbook_id: "access-throttle",
    name: "Access Throttle Runbook",
    version: "v1.6.2",
    status: "draft",
    owner: "Security Team",
    risk: "medium",
    trigger_conditions: ["Alert: Failed Authentication Burst", "Incident: Bruteforce login attack"],
    steps: [
      { step_id: "at-1", order: 1, type: "diagnostic", title: "Trace Origin IP", description: "Verify geolocation, check proxy headers, and identify tenant targets.", requires_approval: false },
      { step_id: "at-2", order: 2, type: "command", title: "Throttle Origin Rates", description: "Apply API rate limits to origin IP blocks.", command_text: "apply-rate-limits --target-ip 198.51.100.12 --limit 5/min", requires_approval: false, rollback_step_id: "at-2-rb" },
      { step_id: "at-3", order: 3, type: "verification", title: "Verify Login Attempts", description: "Confirm bruteforce pattern is blocked or throttled successfully.", requires_approval: false }
    ],
    verification: {
      success_conditions: ["Origin rates throttled below 5 requests/min", "No active failures from IP"],
      timeout_seconds: 200,
      evidence_refs_required: false
    }
  }
];

export const initialExecutions: RunbookExecution[] = [
  {
    execution_id: "EXEC-1278",
    runbook_id: "phishing-response",
    correlation_id: "corr-1a2b3c",
    status: "running",
    started_at: "2026-06-24T11:28:00Z",
    current_step_id: "pr-3",
    step_results: [
      { step_id: "pr-1", status: "succeeded", started_at: "2026-06-24T11:28:05Z", completed_at: "2026-06-24T11:28:20Z", output: "Collected 4 phishing headers. Target domain: phishing@malicious-domain.com", evidence_refs: ["evidence.email_header.txt"] },
      { step_id: "pr-2", status: "succeeded", started_at: "2026-06-24T11:28:22Z", completed_at: "2026-06-24T11:28:50Z", output: "Identified 8 affected user inboxes across Tenants Acme & Globex.", evidence_refs: ["evidence.affected_users.json"] },
      { step_id: "pr-3", status: "running", started_at: "2026-06-24T11:28:55Z", evidence_refs: [] },
      { step_id: "pr-4", status: "pending", evidence_refs: [] },
      { step_id: "pr-5", status: "pending", evidence_refs: [] }
    ],
    rollback: {
      available: true,
      triggered: false
    }
  },
  {
    execution_id: "EXEC-1275",
    runbook_id: "privilege-reset",
    correlation_id: "corr-5x6y7z",
    status: "succeeded",
    started_at: "2026-06-24T09:10:00Z",
    completed_at: "2026-06-24T09:18:20Z",
    current_step_id: "pw-5",
    step_results: [
      { step_id: "pw-1", status: "succeeded", started_at: "2026-06-24T09:10:05Z", completed_at: "2026-06-24T09:10:35Z", output: "Incident verified. Rogue token created for user-18231.", evidence_refs: ["evidence.incident_validation.txt"] },
      { step_id: "pw-2", status: "succeeded", started_at: "2026-06-24T09:10:40Z", completed_at: "2026-06-24T09:11:20Z", output: "Roles accessed: Swarm Admin, DB Reader.", evidence_refs: ["evidence.roles_list.json"] },
      { step_id: "pw-3", status: "succeeded", started_at: "2026-06-24T09:11:45Z", completed_at: "2026-06-24T09:13:00Z", output: "Active sessions terminated across all gateways.", evidence_refs: ["evidence.sessions_revoked.txt"] },
      { step_id: "pw-4", status: "succeeded", started_at: "2026-06-24T09:13:20Z", completed_at: "2026-06-24T09:17:40Z", output: "Credentials reset. MFA update flag pushed to directory.", evidence_refs: ["evidence.reset_auth.json"] },
      { step_id: "pw-5", status: "succeeded", started_at: "2026-06-24T09:17:45Z", completed_at: "2026-06-24T09:18:20Z", output: "Success: Directory blocking old tokens. Credentials secure.", evidence_refs: ["evidence.directory_verification.txt"] }
    ],
    rollback: {
      available: true,
      triggered: false
    }
  }
];
