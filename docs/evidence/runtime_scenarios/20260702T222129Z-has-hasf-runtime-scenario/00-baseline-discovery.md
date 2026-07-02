# Baseline Discovery Report

## Local Repository Status
```bash
pwd:
/Users/michaelhoch/hoch_agent_swarm

git status --short:
 M docs/evidence/runtime/global_verify_latest.md
 M docs/evidence/runtime/hoch-pods-runtime-evidence.md
 M has_live_project_tracker/data/global_verify.json
 M has_live_project_tracker/data/goal_runner_status.json
 M has_live_project_tracker/data/hoch_pod_schedule.json
 M has_live_project_tracker/data/hoch_pods_runtime_state.json
 M has_live_project_tracker/data/live_telemetry_freshness.json
 M has_live_project_tracker/data/live_telemetry_refresh_result.json
?? .github/workflows/has-local-runtime-runner.yml
?? .github/workflows/has-qa-runner.yml
?? .github/workflows/has-release-runner.yml
?? config/compute_assets.example.json
?? data/runtime_scenarios/
?? docs/design/approved-visual-authority-inbox/
?? docs/design/quarantine/
?? docs/evidence/goal_runner/goal_runner_20260702T184719Z.md
?? docs/evidence/goal_runner/goal_runner_20260702T193727Z.md
?? docs/evidence/goal_runner/goal_runner_20260702T194727Z.md
?? docs/evidence/goal_runner/goal_runner_20260702T195738Z.md
?? docs/evidence/goal_runner/goal_runner_20260702T200749Z.md
?? docs/evidence/goal_runner/goal_runner_20260702T201800Z.md
?? docs/evidence/goal_runner/goal_runner_20260702T202811Z.md
?? docs/evidence/goal_runner/goal_runner_20260702T203822Z.md
?? docs/evidence/goal_runner/goal_runner_20260702T204832Z.md
?? docs/evidence/goal_runner/goal_runner_20260702T205843Z.md
?? docs/evidence/goal_runner/goal_runner_20260702T210854Z.md
?? docs/evidence/goal_runner/goal_runner_20260702T211908Z.md
?? docs/evidence/goal_runner/goal_runner_20260702T212919Z.md
?? docs/evidence/goal_runner/goal_runner_20260702T213929Z.md
?? docs/evidence/goal_runner/goal_runner_20260702T214949Z.md
?? docs/evidence/goal_runner/goal_runner_20260702T220012Z.md
?? docs/evidence/goal_runner/goal_runner_20260702T221034Z.md
?? docs/evidence/goal_runner/goal_runner_20260702T222044Z.md
?? docs/evidence/moonshot/moonshot_audit_20260702T193448Z.md
?? docs/evidence/moonshot/moonshot_readiness_20260702T193448Z.md
?? docs/evidence/runtime/blank-image-reset-cleanup.md
?? docs/evidence/runtime/fresh-grok-session-clean-start.md
?? docs/evidence/runtime/image-repopulation-protocol.md
?? docs/evidence/runtime/rc61-local-first-cost-governor-fresh-pert-live-ui.md
?? docs/evidence/runtime/voice-sidecar-phase-1-implementation.md
?? docs/evidence/runtime/voice-sidecar-phase-1-plan.md
?? docs/evidence/runtime/workspace-visual-garbage-cleanup.md
?? docs/evidence/runtime_scenarios/
?? has_live_project_tracker/data/agent_pulse_matrix.json
?? has_live_project_tracker/data/cost_governor.json
?? has_live_project_tracker/data/deployment_readiness_audit.json
?? has_live_project_tracker/data/fresh_pert_gap_analysis.json
?? has_live_project_tracker/data/frontier_escalation_queue.json
?? has_live_project_tracker/data/has_hasf_scope_lock.json
?? has_live_project_tracker/data/human_approval_queue.json
?? has_live_project_tracker/data/live_runner_status.json
?? has_live_project_tracker/data/local_ai_inventory.json
?? has_live_project_tracker/data/local_runtime_proof.json
?? has_live_project_tracker/data/model_routing_policy.json
?? has_live_project_tracker/data/operator_next_actions.json
?? has_live_project_tracker/data/qa_gate_matrix.json
?? has_live_project_tracker/data/revenue_readiness_audit.json
?? scripts/autonomous_facilitation_check.py
?? scripts/check_local_has_runtime.py
?? scripts/fresh_has_hasf_gap_pert_audit.py
?? scripts/frontier_escalation_gate.py
?? scripts/local_ai_inventory.py
?? scripts/setup_has_hasf_live_runner.py
?? scripts/setup_has_hasf_live_runner.sh
?? scripts/verify_has_hasf_scope_lock.py
?? setup_has_qa_runner_now.sh
?? setup_has_qa_runner_with_ui_token.sh
?? tests/e2e/rc54-voice-sidecar-policy.spec.ts
?? tests/e2e/rc57-autonomous-facilitation-loop.spec.ts
?? tests/e2e/ui-v21-operator-console.spec.ts
?? tools/has_live_truth_sidecar.py
?? tools/hoch_pods_theme_guard/hoch_pods_theme_guard/file.png

git rev-parse HEAD:
0915d65413200c182b8a3a9c0eedcc0c61a4c81b

git log --oneline -n 5:
0915d65 docs(mission): update ledger with HELM, visual baseline, CI, and PERT tracker
0aa34cb feat(goal): add digital PERT live tracker for HAS HASF
a1322aa ci: add Linux QA runner parity for HAS and HASF
a1a98d1 docs(ui): lock HOCH PODS THEATER V6 visual baseline
f5136b3 feat(helm): onboard HELM execution agent and status route
```

## HOCH-200 Local Verification
```bash

[0;36mℹ[0m  HOCH-200 VPS Verification
[0;36mℹ[0m  Target: root@50.116.41.183
[0;36mℹ[0m  Timestamp: 2026-07-02T22:21:35Z
---
[0;32m✅[0m  ssh-connectivity: 50.116.41.183 reachable

[0;32m✅[0m  hostname: hoch-relay-001
[0;32m✅[0m  os: Ubuntu 24.04.4 LTS
[0;32m✅[0m  kernel: 6.8.0-124-generic
[0;32m✅[0m  docker-version: 29.6.1
[0;32m✅[0m  docker-compose-version: 5.2.0
[0;32m✅[0m  ufw-active: UFW is active
[0;32m✅[0m  ufw-port-3012-blocked: No public ALLOW rule for 3012 (rules: none)
[0;32m✅[0m  fail2ban-active: fail2ban running
[0;32m✅[0m  container-running: hoch-relay-api: running
[0;32m✅[0m  container-healthy: hoch-relay-api health: healthy
[0;32m✅[0m  port-binding-tailscale-only: Bound to 100.87.18.15:3012
[0;32m✅[0m  relay-health-endpoint: http://100.87.18.15:3012/health → OK
[0;32m✅[0m  port-3012-not-public: Public IP 50.116.41.183:3012 unreachable — constraint satisfied
[0;32m✅[0m  evidence-file: /root/hoch200_node_status.txt exists
[0;32m✅[0m  worker-registry-HAS-WORKER-RELAY-001: Worker ID confirmed in /health

================================================================
  HOCH-200 VPS Verification: CONDITIONAL_GO
================================================================
  Node:        hoch-relay-001 (50.116.41.183)
  Tailscale:   100.87.18.15
  Container:   running / healthy
  Port 3012:   Tailscale-only = YES
  Status file: /Users/michaelhoch/hoch_agent_swarm/hoch_pods/compute/setup_status.json
================================================================

  Failures: 0

```

## Remote Host Status (HOCH-200)
```bash
hoch-relay-001
Thu Jul  2 10:21:38 PM UTC 2026
Linux hoch-relay-001 6.8.0-124-generic #124-Ubuntu SMP PREEMPT_DYNAMIC Tue May 26 13:00:45 UTC 2026 x86_64 x86_64 x86_64 GNU/Linux
 22:21:38 up 1 day, 19:07,  2 users,  load average: 0.03, 0.01, 0.00
NAMES            STATUS                  PORTS
hoch-relay-api   Up 42 hours (healthy)   100.87.18.15:3012->3012/tcp
NAME                STATUS              CONFIG FILES
hoch-relay          running(1)          /opt/hoch-relay/docker-compose.yml
Netid State  Recv-Q Send-Q               Local Address:Port  Peer Address:PortProcess                                                                                                                    
udp   UNCONN 0      0                       127.0.0.54:53         0.0.0.0:*    users:(("systemd-resolve",pid=472,fd=16)) uid:991 ino:5882 sk:1001 cgroup:/system.slice/systemd-resolved.service <->      
udp   UNCONN 0      0                    127.0.0.53%lo:53         0.0.0.0:*    users:(("systemd-resolve",pid=472,fd=14)) uid:991 ino:5880 sk:1002 cgroup:/system.slice/systemd-resolved.service <->      
udp   UNCONN 0      0                          0.0.0.0:41641      0.0.0.0:*    users:(("tailscaled",pid=761,fd=21)) ino:17843 sk:1003 fwmark:0x80000 cgroup:/system.slice/tailscaled.service <->         
udp   UNCONN 0      0                             [::]:41641         [::]:*    users:(("tailscaled",pid=761,fd=20)) ino:17842 sk:1004 fwmark:0x80000 cgroup:/system.slice/tailscaled.service v6only:1 <->
tcp   LISTEN 0      128                   100.87.18.15:8765       0.0.0.0:*    users:(("sshd",pid=118358,fd=5)) ino:475016 sk:1005 cgroup:/user.slice/user-0.slice/session-426.scope <->                 
tcp   LISTEN 0      4096                    127.0.0.54:53         0.0.0.0:*    users:(("systemd-resolve",pid=472,fd=17)) uid:991 ino:5883 sk:2 cgroup:/system.slice/systemd-resolved.service <->         
tcp   LISTEN 0      4096                  100.87.18.15:35941      0.0.0.0:*    users:(("tailscaled",pid=761,fd=12)) ino:8189 sk:3 cgroup:/system.slice/tailscaled.service <->                            
tcp   LISTEN 0      4096                  100.87.18.15:3012       0.0.0.0:*    users:(("docker-proxy",pid=8357,fd=8)) ino:33137 sk:4 cgroup:/system.slice/docker.service <->                             
tcp   LISTEN 0      4096                 127.0.0.53%lo:53         0.0.0.0:*    users:(("systemd-resolve",pid=472,fd=15)) uid:991 ino:5881 sk:5 cgroup:/system.slice/systemd-resolved.service <->         
tcp   LISTEN 0      4096                       0.0.0.0:22         0.0.0.0:*    users:(("sshd",pid=118127,fd=3),("systemd",pid=1,fd=93)) ino:7355 sk:6 cgroup:/system.slice/ssh.socket <->                
tcp   LISTEN 0      4096   [fd7a:115c:a1e0::cd39:1210]:59322         [::]:*    users:(("tailscaled",pid=761,fd=22)) ino:8191 sk:7 cgroup:/system.slice/tailscaled.service v6only:1 <->                   
tcp   LISTEN 0      4096                          [::]:22            [::]:*    users:(("sshd",pid=118127,fd=4),("systemd",pid=1,fd=94)) ino:7357 sk:8 cgroup:/system.slice/ssh.socket v6only:1 <->       
Status: active
Logging: on (low)
Default: deny (incoming), allow (outgoing), deny (routed)
New profiles: skip

To                         Action      From
--                         ------      ----
22/tcp                     ALLOW IN    99.22.37.25               

Status
|- Number of jail:	1
`- Jail list:	sshd
Filesystem      Size  Used Avail Use% Mounted on
tmpfs           2.4G  1.2M  2.4G   1% /run
/dev/sda         20G  4.1G   15G  23% /
tmpfs            12G     0   12G   0% /dev/shm
tmpfs           5.0M     0  5.0M   0% /run/lock
overlay          20G  4.1G   15G  23% /var/lib/docker/rootfs/overlayfs/02c2e6fb27935f47af4567fbd3a294a5e63dc5308817d767240551d559fc3a5b
tmpfs           2.4G   12K  2.4G   1% /run/user/0
               total        used        free      shared  buff/cache   available
Mem:            23Gi       725Mi        21Gi       1.1Mi       1.9Gi        22Gi
Swap:          495Mi          0B       495Mi
```
