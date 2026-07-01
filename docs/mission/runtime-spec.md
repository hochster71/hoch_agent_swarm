# Runtime Specification — Swarm Task Graph Engine

**Document ID**: RUNTIME-SPEC-2026-06-25  
**Frameworks**: Theory of Constraints, Critical Path Method  
**Author**: Agent Runtime Engineer  

---

## 1. Task Representation Schema
Each task in the Swarm DAG is represented as a structured JSON object conforming to the following type definitions:

```typescript
interface SwarmTask {
  id: string;                      // Unique identifier (e.g., T2-SPEC)
  title: string;                   // Human-readable title
  description: string;             // Detailed description of work
  status: TaskStatus;              // Current execution state
  priority: 'low' | 'medium' | 'high' | 'critical';
  ownerAgentId: string;            // ID of agent assigned to execute the task
  dependencies: string[];          // List of prerequisite Task IDs
  planningFrameworks: string[];    // Frameworks utilized during planning
  acceptanceCriteria: string;      // Assertions required to mark task complete
  riskLevel: 'low' | 'medium' | 'high';
  approvalRequired: boolean;       // Requires human operator gate before execution
}

type TaskStatus = 'pending' | 'running' | 'completed' | 'blocked';
```

---

## 2. DAG Resolution and Execution Algorithm
The orchestration loop parses the task graph JSON and computes execution order dynamically using a topological sort.

### Dependency Lock Check
A task $T_i$ is locked (status `pending` or `blocked`) until all tasks in its dependency set $D(T_i)$ are resolved:
$$D(T_i) = \{ T_j \mid T_j \in \text{dependencies}(T_i) \}$$
Execution of $T_i$ is allowed if and only if:
$$\forall T_j \in D(T_i), \text{status}(T_j) = \text{'completed'}$$

### Blocking propagation
If any task $T_j \in D(T_i)$ has `status` of `blocked` or `failed`, then $T_i$ will transit to `blocked` state.

---

## 3. Human-In-The-Loop Approval Gates
When `approvalRequired` is true, the engine intercepts the execution request:
1. State transition from `pending` to `running` is paused.
2. An entry is pushed into the **Swarm Approval Queue** containing the command, target workspace, risk description, and executing agent.
3. The engine blocks execution of this task until a signed approval payload is received from the UI console operator.
4. If denied, the task is marked `blocked`.

---

## 4. Telemetry Stream Event Schemas
Realtime metrics are streamed over WebSockets from the backend server via `/ws/metrics` at an interval of 2000ms.

### A. Live System Metrics Payload
```json
{
  "type": "system_telemetry",
  "data": {
    "timestamp": "2026-06-25T02:10:28Z",
    "cpu_usage_pct": 18.4,
    "memory_usage_pct": 54.2,
    "active_nodes_count": 6,
    "network_latency_ms": 1.2
  }
}
```

### B. Task State Change Notification Payload
```json
{
  "type": "task_state_change",
  "data": {
    "task_id": "T4-CORE-ENGINE",
    "old_status": "pending",
    "new_status": "running",
    "timestamp": "2026-06-25T02:12:00Z",
    "executor": "agent-runtime-engineer"
  }
}
```
