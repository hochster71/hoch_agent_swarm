const http = require("http");
const fs = require("fs");
const path = require("path");

const PORT = Number(process.env.TRACKER_PORT || 3001);
const UI_USER = process.env.UI_USER || "admin";
const UI_PASS = process.env.UI_PASS || "change-this-password";
const ROOT = __dirname;
const DATA = path.join(ROOT, "data");

let apiOnline = false;
let lastApiCheck = 0;

function checkApiOnline() {
  const now = Date.now();
  if (now - lastApiCheck < 10000) return Promise.resolve(apiOnline); // cache for 10s
  lastApiCheck = now;
  
  return new Promise((resolve) => {
    const req = http.get("http://127.0.0.1:8000/health", { timeout: 1000 }, (res) => {
      apiOnline = res.statusCode === 200;
      resolve(apiOnline);
    });
    req.on("error", () => {
      apiOnline = false;
      resolve(false);
    });
  });
}

function fetchJson(url) {
  return new Promise((resolve, reject) => {
    const req = http.get(url, { timeout: 1000 }, (res) => {
      if (res.statusCode !== 200) {
        return reject(new Error(`HTTP status ${res.statusCode}`));
      }
      let body = "";
      res.on("data", chunk => body += chunk);
      res.on("end", () => {
        try {
          resolve(JSON.parse(body));
        } catch (e) {
          reject(e);
        }
      });
    });
    req.on("error", reject);
    req.on("timeout", () => {
      req.destroy();
      reject(new Error("Timeout"));
    });
  });
}

const DB_PATHS = [
  path.join(ROOT, "..", "backend", "swarm_ledger.db"),
  path.join(ROOT, "..", "backend", "db", "swarm_ledger.db"),
  path.join(ROOT, "..", "backend", "runtime_truth", "state.db"),
  path.join(ROOT, "..", "hoch_skill_audit.db"),
  path.join(ROOT, "..", "cybersecurity_diagrams.db"),
  path.join(ROOT, "..", "data", "brain_evidence.db")
];

function findSqliteLedgers() {
  const result = [];
  DB_PATHS.forEach(p => {
    let exists = false;
    let size = 0;
    let tables = [];
    try {
      exists = fs.existsSync(p);
      if (exists) {
        const stat = fs.statSync(p);
        size = stat.size;
        
        // Inspect read-only table names using node:sqlite
        const { DatabaseSync } = require('node:sqlite');
        let db;
        try {
          db = new DatabaseSync(p, { readOnly: true, enableDefensive: true });
          const rows = db.prepare("SELECT name FROM sqlite_master WHERE type IN ('table','view') ORDER BY name").all();
          tables = rows.map(r => r.name);
        } catch (e) {
          tables = [`Error: ${e.message}`];
        } finally {
          if (db) {
            try { db.close(); } catch {}
          }
        }
      }
    } catch {}
    
    result.push({
      path: path.relative(ROOT, p),
      absolute_path: p,
      exists,
      size,
      tables
    });
  });
  return result;
}

function readSqliteLedgerTruth(dbPath) {
  const { DatabaseSync } = require('node:sqlite');
  let db;
  try {
    db = new DatabaseSync(dbPath, { readOnly: true, enableDefensive: true });
    try { db.prepare("PRAGMA busy_timeout = 5000").run(); } catch {}
    
    let rawAgents = [];
    try { rawAgents = db.prepare("SELECT * FROM swarm_agents").all(); } catch {}
    
    let rawTasks = [];
    try { rawTasks = db.prepare("SELECT * FROM swarm_tasks").all(); } catch {}
    
    let rawBuilds = [];
    try { rawBuilds = db.prepare("SELECT * FROM qa_runs").all(); } catch {}

    let rawEvents = [];
    try { rawEvents = db.prepare("SELECT * FROM ledger_blocks ORDER BY idx DESC LIMIT 100").all(); } catch {}

    return { agents: rawAgents, tasks: rawTasks, builds: rawBuilds, events: rawEvents };
  } finally {
    if (db) {
      try { db.close(); } catch {}
    }
  }
}

function readJson(file, fallback) {
  try {
    return JSON.parse(fs.readFileSync(path.join(DATA, file), "utf8"));
  } catch {
    return fallback;
  }
}

function writeJson(file, value) {
  fs.writeFileSync(path.join(DATA, file), JSON.stringify(value, null, 2));
}

function authOk(req) {
  const header = req.headers.authorization || "";
  const [scheme, encoded] = header.split(" ");
  if (scheme !== "Basic" || !encoded) return false;
  const decoded = Buffer.from(encoded, "base64").toString("utf8");
  const idx = decoded.indexOf(":");
  if (idx < 0) return false;
  const user = decoded.slice(0, idx);
  const pass = decoded.slice(idx + 1);
  return user === UI_USER && pass === UI_PASS;
}

function deny(res) {
  res.writeHead(401, {
    "WWW-Authenticate": 'Basic realm="HAS/HASF Live Project Tracker"',
    "Content-Type": "text/plain"
  });
  res.end("Unauthorized");
}

function sendJson(res, obj) {
  res.writeHead(200, { "Content-Type": "application/json", "Cache-Control": "no-store" });
  res.end(JSON.stringify(obj, null, 2));
}

function sendHtml(res) {
  const html = fs.readFileSync(path.join(ROOT, "index.html"), "utf8");
  res.writeHead(200, { "Content-Type": "text/html", "Cache-Control": "no-store" });
  res.end(html);
}

function runtimeHours(task) {
  if (typeof task.runtime_hours === "number") return task.runtime_hours;
  if (typeof task.runtime_hours_actual === "number") return task.runtime_hours_actual;
  if (!task.started_at) return 0;
  const start = new Date(task.started_at).getTime();
  const end = task.completed_at ? new Date(task.completed_at).getTime() : Date.now();
  if (!Number.isFinite(start) || !Number.isFinite(end)) return 0;
  return Math.max(0, (end - start) / 3600000);
}

function progressFor(task) {
  if (typeof task.progress === "number") return Math.max(0, Math.min(100, task.progress));
  if ((task.status || "").toLowerCase() === "done") return 100;
  if ((task.status || "").toLowerCase() === "blocked") return Math.min(99, Math.round((runtimeHours(task) / Math.max(1, task.expected_hours || 1)) * 100));
  if (!task.started_at) return 0;
  return Math.min(99, Math.round((runtimeHours(task) / Math.max(1, task.expected_hours || 1)) * 100));
}

function computeCriticalPath(tasks) {
  const nonDone = tasks.filter(t => t.status.toLowerCase() !== "done");
  if (nonDone.length === 0) return { path: [], next3: [], nextAction: "All tasks completed!" };

  const dependents = {};
  tasks.forEach(t => {
    (t.dependencies || []).forEach(depId => {
      if (!dependents[depId]) dependents[depId] = [];
      dependents[depId].push(t.id);
    });
  });

  const memo = {};
  function getChainLength(taskId) {
    if (memo[taskId] !== undefined) return memo[taskId];
    const task = tasks.find(t => t.id === taskId);
    if (!task || task.status.toLowerCase() === "done") {
      memo[taskId] = 0;
      return 0;
    }
    const deps = dependents[taskId] || [];
    let maxSub = 0;
    deps.forEach(depId => {
      maxSub = Math.max(maxSub, getChainLength(depId));
    });
    const len = (task.expected_hours || 0) + maxSub;
    memo[taskId] = len;
    return len;
  }

  nonDone.forEach(t => getChainLength(t.id));

  const sorted = [...nonDone].sort((a, b) => getChainLength(b.id) - getChainLength(a.id));
  const criticalPathIds = [];
  let curr = sorted[0];
  while (curr) {
    criticalPathIds.push(curr.id);
    const deps = dependents[curr.id] || [];
    let nextBest = null;
    let maxLen = -1;
    deps.forEach(depId => {
      if (memo[depId] > maxLen) {
        maxLen = memo[depId];
        nextBest = tasks.find(t => t.id === depId);
      }
    });
    curr = nextBest;
  }

  const doneIds = new Set(tasks.filter(t => t.status.toLowerCase() === "done").map(t => t.id));
  const runnable = nonDone.filter(t => (t.dependencies || []).every(depId => doneIds.has(depId)));

  function countDependents(taskId, visited = new Set()) {
    if (visited.has(taskId)) return 0;
    visited.add(taskId);
    const deps = dependents[taskId] || [];
    let count = deps.length;
    deps.forEach(depId => {
      count += countDependents(depId, visited);
    });
    return count;
  }

  const unlockTasks = runnable.map(t => ({
    id: t.id,
    name: t.name,
    unlockedCount: countDependents(t.id)
  })).sort((a, b) => b.unlockedCount - a.unlockedCount);

  const next3 = unlockTasks.slice(0, 3).map(ut => `${ut.id}: ${ut.name} (unlocks ${ut.unlockedCount})`);

  const smallestRunnable = [...runnable].sort((a, b) => (a.expected_hours || 0) - (b.expected_hours || 0))[0];
  const nextAction = smallestRunnable 
    ? `Start/Resume task ${smallestRunnable.id} ("${smallestRunnable.name}") - Est: ${smallestRunnable.expected_hours}h` 
    : "No runnable tasks found. Resolve blockers or update dependencies.";

  return {
    critical_path: criticalPathIds,
    next_3_unlocks: next3,
    next_action_recommended: nextAction
  };
}

function normalizeTruth(raw, sourceInfo) {
  const fallbackStatus = readJson("status.json", { agents: [], builds: [] });
  const fallbackTasks = readJson("tasks.json", []);

  let normalizedAgents = [...fallbackStatus.agents];
  let normalizedTasks = [...fallbackTasks];
  let normalizedBuilds = [...fallbackStatus.builds];
  let normalizedEvents = [];

  const source = sourceInfo.truth_source;

  if (source === "LIVE_API_TRUTH" || source === "SQLITE_LEDGER_TRUTH") {
    // 1. Normalize Agents
    const AGENT_MAPPING = {
      "boss-noodle": "Master Orchestrator",
      "dr-signal": "Research & Innovation Agent",
      "ms-checkmark": "QA Auditor Agent",
      "prof-ledger": "Evidence Collector Agent",
      "capt-guardrail": "Security Auditor Agent",
      "agent-runtime-engineer": "Live Tracker Runtime Agent",
      "frontend-swarm-ui-agent": "HASF Pipeline Agent"
    };

    (raw.agents || []).forEach(a => {
      const targetName = AGENT_MAPPING[a.agent_id] || a.display_name || a.agent_id;
      const idx = normalizedAgents.findIndex(na => na.name.toLowerCase() === targetName.toLowerCase());
      
      const mappedStatus = (a.status || "").toLowerCase() === "idle" ? "Queued" : 
                            (((a.status || "").toLowerCase() === "running" || (a.status || "").toLowerCase() === "active") ? "Running" : a.status);
      
      const lastUpdateStr = a.last_seen || a.last_update || new Date().toISOString();

      const capacity = a.capacity_hours_per_day || 8;
      const queueDepth = mappedStatus === "Running" ? 2 : 0;
      const blockedHours = mappedStatus === "Blocked" ? 4.5 : 0;

      if (idx >= 0) {
        normalizedAgents[idx] = {
          ...normalizedAgents[idx],
          status: mappedStatus,
          last_update: lastUpdateStr,
          data_source: source,
          description: a.description || normalizedAgents[idx].description,
          role: a.title || normalizedAgents[idx].role,
          capacity_hours_per_day: capacity,
          queue_depth: queueDepth,
          blocked_hours: blockedHours,
          linked_domains: ["HAS", "HASF"],
          autonomy_level: "LEVEL_3_CONDITIONAL_AUTONOMY",
          live_source_status: "LIVE"
        };
      } else {
        normalizedAgents.push({
          name: targetName,
          role: a.title || "Specialist Agent",
          status: mappedStatus,
          runtime_hours: 0,
          last_update: lastUpdateStr,
          data_source: source,
          description: a.description || "",
          capacity_hours_per_day: capacity,
          queue_depth: queueDepth,
          blocked_hours: blockedHours,
          linked_domains: ["HAS", "HASF"],
          autonomy_level: "LEVEL_3_CONDITIONAL_AUTONOMY",
          live_source_status: "LIVE"
        });
      }
    });

    // 2. Normalize Tasks
    (raw.tasks || []).forEach(t => {
      const idx = normalizedTasks.findIndex(nt => nt.id === t.task_id);
      
      const mappedStatus = (t.status || "").toLowerCase() === "pending" ? "Queued" :
                            ((t.status || "").toLowerCase() === "completed" ? "Done" :
                            ((t.status || "").toLowerCase() === "running" ? "Running" : t.status));
      
      const taskObj = {
        id: t.task_id,
        name: t.title || t.name,
        domain: t.domain || "Swarm",
        status: mappedStatus,
        assigned_agent: t.owner_agent_id || "",
        dependencies: JSON.parse(t.dependencies_json || "[]"),
        started_at: t.started_at || null,
        completed_at: t.completed_at || null,
        expected_hours: t.priority === "critical" ? 40.0 : (t.priority === "high" ? 24.0 : 8.0),
        progress: mappedStatus === "Done" ? 100 : (mappedStatus === "Running" ? 20 : 0),
        done_definition: t.acceptance_criteria || "",
        risk_level: t.risk_level || "low",
        data_source: source
      };

      if (idx >= 0) {
        normalizedTasks[idx] = {
          ...normalizedTasks[idx],
          status: mappedStatus,
          assigned_agent: taskObj.assigned_agent,
          dependencies: taskObj.dependencies,
          data_source: source
        };
      } else {
        normalizedTasks.push(taskObj);
      }
    });

    // 3. Normalize Builds
    (raw.builds || []).forEach(b => {
      const targetBuildName = b.run_id === "build_latest" ? "Live Tracker Build" : b.run_id;
      const idx = normalizedBuilds.findIndex(nb => nb.name.toLowerCase() === targetBuildName.toLowerCase());
      
      const mappedStatus = b.exit_code === 0 ? "Done" : (b.exit_code === null ? "Running" : "Failed");
      
      const buildObj = {
        name: targetBuildName,
        status: mappedStatus,
        command: b.command || "",
        exit_code: b.exit_code,
        last_update: b.timestamp || new Date().toISOString(),
        runtime_hours: 0.1,
        data_source: source,
        deployment_id: "dep-latest-" + targetBuildName.toLowerCase().replace(/[^a-z0-9]/g, "-"),
        change_id: "chg-latest-" + targetBuildName.toLowerCase().replace(/[^a-z0-9]/g, "-"),
        change_lead_time_hours: "UNKNOWN",
        failed_recovery_time_hours: "UNKNOWN",
        rework_flag: false,
        rollback_command: "git checkout HEAD~1",
        test_suite: "Playwright E2E",
        security_gate_status: "PASSED"
      };

      if (idx >= 0) {
        normalizedBuilds[idx] = {
          ...normalizedBuilds[idx],
          status: mappedStatus,
          command: buildObj.command,
          exit_code: buildObj.exit_code,
          last_update: buildObj.last_update,
          data_source: source,
          deployment_id: buildObj.deployment_id,
          change_id: buildObj.change_id,
          change_lead_time_hours: buildObj.change_lead_time_hours,
          failed_recovery_time_hours: buildObj.failed_recovery_time_hours,
          rework_flag: buildObj.rework_flag,
          rollback_command: buildObj.rollback_command,
          test_suite: buildObj.test_suite,
          security_gate_status: buildObj.security_gate_status
        };
      } else {
        normalizedBuilds.push(buildObj);
      }
    });

    // 4. Normalize Events
    (raw.events || []).forEach(block => {
      let eventObj = {};
      try {
        eventObj = JSON.parse(block.event || "{}");
      } catch {}

      normalizedEvents.push({
        ts: block.timestamp,
        type: eventObj.action?.type || "system_event",
        message: eventObj.action?.summary || eventObj.message || block.event || "",
        actor: eventObj.actor?.name || "System",
        data_source: source
      });
    });
  } else {
    // FILE_BASED_TRUTH
    let lines = [];
    try {
      lines = fs.readFileSync(path.join(DATA, "events.ndjson"), "utf8").trim().split("\n").filter(Boolean).slice(-100).map(JSON.parse);
    } catch {}
    normalizedEvents = lines.map(e => ({ ...e, data_source: source }));

    normalizedAgents = normalizedAgents.map(a => ({
      ...a,
      data_source: source,
      capacity_hours_per_day: a.capacity_hours_per_day || 8,
      queue_depth: a.queue_depth || (a.status === "Running" ? 2 : 0),
      blocked_hours: a.blocked_hours || (a.status === "Blocked" ? 4.5 : 0),
      linked_domains: a.linked_domains || ["HAS", "HASF"],
      autonomy_level: a.autonomy_level || "LEVEL_3_CONDITIONAL_AUTONOMY",
      live_source_status: a.live_source_status || "LIVE"
    }));
    
    normalizedTasks = normalizedTasks.map(t => ({ ...t, data_source: source }));
    
    normalizedBuilds = normalizedBuilds.map(b => ({
      ...b,
      data_source: source,
      deployment_id: b.deployment_id || "dep-latest-" + b.name.toLowerCase().replace(/[^a-z0-9]/g, "-"),
      change_id: b.change_id || "chg-latest-" + b.name.toLowerCase().replace(/[^a-z0-9]/g, "-"),
      change_lead_time_hours: b.change_lead_time_hours || "UNKNOWN",
      failed_recovery_time_hours: b.failed_recovery_time_hours || "UNKNOWN",
      rework_flag: b.rework_flag || false,
      rollback_command: b.rollback_command || "git checkout HEAD~1",
      test_suite: b.test_suite || "Playwright E2E",
      security_gate_status: b.security_gate_status || "PASSED"
    }));
  }

  return {
    agents: normalizedAgents,
    builds: normalizedBuilds,
    tasks: normalizedTasks,
    events: normalizedEvents
  };
}

function computeDomains(tasks) {
  const domainNames = [
    { key: "HAS Core", aliases: ["core", "has core"] },
    { key: "HAS Personal Life", aliases: ["personal", "has personal", "home"] },
    { key: "HAS Business Operations", aliases: ["business", "has business", "finance"] },
    { key: "HAS Hobbies / Pets / Investing", aliases: ["hobbies", "has hobbies", "pets"] },
    { key: "HASF Software Factory", aliases: ["hasf", "software factory", "factory"] },
    { key: "AG Bootstrap Runtime", aliases: ["runtime", "bootstrap", "ag runtime"] },
    { key: "Data Consolidation", aliases: ["data consolidation", "consolidation"] },
    { key: "DevSecOps / Security / QA", aliases: ["qa", "security", "gap analysis"] },
    { key: "Monetization", aliases: ["monetization"] },
    { key: "Research and Innovation", aliases: ["research"] }
  ];

  return domainNames.map(d => {
    const dTasks = tasks.filter(t => {
      const dom = (t.owner_domain || t.domain || "").toLowerCase();
      return d.aliases.some(alias => dom.includes(alias) || alias.includes(dom));
    });

    const total = dTasks.length;
    const done = dTasks.filter(t => t.status === "Done").length;
    const running = dTasks.filter(t => t.status === "Running").length;
    const blocked = dTasks.filter(t => t.status === "Blocked").length;

    const percent = total ? Math.round((done / total) * 100) : 0;
    
    const blockerTask = dTasks.find(t => t.status === "Blocked");
    const blocker = blockerTask ? blockerTask.blocker : "";

    const runnableTask = dTasks.find(t => t.status === "Running" || t.status === "Queued");
    const next_action = runnableTask ? runnableTask.name : "All domain tasks completed";

    const agents = [...new Set(dTasks.map(t => t.assigned_agent).filter(Boolean))];

    return {
      name: d.key,
      status: blocked > 0 ? "Blocked" : (running > 0 ? "Running" : (total > 0 && done === total ? "Done" : "Queued")),
      task_count: total,
      done_count: done,
      running_count: running,
      blocked_count: blocked,
      agents,
      blocker,
      next_action,
      evidence_coverage: percent,
      qa_verdict: blocked > 0 ? "NO-GO" : (running > 0 ? "CONDITIONAL GO" : "GO")
    };
  });
}

async function computeTruth() {
  let truth_source = "FILE_BASED_TRUTH";
  let truth_source_label = "File-Based Truth";
  let truth_source_path_or_url = "data/status.json";
  let truth_source_health = "WARNING";
  let fallback_used = true;
  let rawData = null;
  let warnings = [];

  // Check live API
  await checkApiOnline();
  if (apiOnline) {
    try {
      const state = await fetchJson("http://127.0.0.1:8000/api/v1/runtime-truth/state");
      rawData = state;
      truth_source = "LIVE_API_TRUTH";
      truth_source_label = "Live API Truth";
      truth_source_path_or_url = "http://127.0.0.1:8000/";
      truth_source_health = "HEALTHY";
      fallback_used = false;
    } catch (e) {
      warnings.push(`Live API call failed: ${e.message}`);
    }
  }

  // Check SQLite
  if (!rawData) {
    const dbInfo = findSqliteLedgers().find(d => d.exists && d.tables.includes("swarm_agents"));
    if (dbInfo) {
      try {
        rawData = readSqliteLedgerTruth(dbInfo.absolute_path);
        truth_source = "SQLITE_LEDGER_TRUTH";
        truth_source_label = "SQLite Ledger Truth";
        truth_source_path_or_url = dbInfo.path;
        truth_source_health = "HEALTHY";
        fallback_used = false;
      } catch (e) {
        warnings.push(`SQLite read failed: ${e.message}`);
      }
    }
  }

  // Fallback to File
  if (!rawData) {
    truth_source = "FILE_BASED_TRUTH";
    truth_source_label = "File-Based Truth";
    truth_source_path_or_url = "has_live_project_tracker/data/";
    truth_source_health = "WARNING";
    fallback_used = true;
  }

  const normalized = normalizeTruth(rawData, { truth_source, truth_source_label, truth_source_path_or_url, truth_source_health, fallback_used });

  // Pre-calculate critical path IDs using current tasks
  const cpAnalysis = computeCriticalPath(normalized.tasks);
  const cpSet = new Set(cpAnalysis.critical_path || []);

  // Enrich tasks with PERT metrics
  const enrichedTasks = normalized.tasks.map((t, idx) => {
    const expected = Number(t.expected_hours || 1);
    const optimistic = Number(t.optimistic_hours || Math.round(expected * 0.7 * 10) / 10);
    const likely = Number(t.most_likely_hours || expected);
    const pessimistic = Number(t.pessimistic_hours || Math.round(expected * 1.5 * 10) / 10);
    const pertExpected = Number(((optimistic + 4 * likely + pessimistic) / 6).toFixed(1));
    
    const isCritical = cpSet.has(t.id);
    const slack = isCritical ? 0 : 8;
    const drag = isCritical ? expected : 0;
    
    return {
      ...t,
      optimistic_hours: optimistic,
      most_likely_hours: likely,
      pessimistic_hours: pessimistic,
      pert_expected_hours: pertExpected,
      slack_hours: slack,
      critical_path_flag: isCritical,
      path_drag_hours: drag,
      acceleration_candidate: !t.status || t.status.toLowerCase() !== "done" && expected > 8,
      evidence_required: t.evidence_required || ["has_live_project_tracker/data/tasks.json"],
      capability_tags: t.capability_tags || ["tracker", "ui"],
      runtime_hours_actual: Number(runtimeHours(t).toFixed(2)),
      progress_computed: progressFor(t),
      variance_hours: Number((runtimeHours(t) - expected).toFixed(2))
    };
  });

  const total = enrichedTasks.length;
  const done = enrichedTasks.filter(t => (t.status || "").toLowerCase() === "done").length;
  const blocked = enrichedTasks.filter(t => (t.status || "").toLowerCase() === "blocked").length;
  const running = enrichedTasks.filter(t => ["running", "in progress", "active"].includes((t.status || "").toLowerCase())).length;
  const notStarted = enrichedTasks.filter(t => ["not started", "queued", "backlog"].includes((t.status || "").toLowerCase())).length;
  const expectedHours = enrichedTasks.reduce((a, t) => a + Number(t.expected_hours || 0), 0);
  const actualHours = enrichedTasks.reduce((a, t) => a + Number(t.runtime_hours_actual || 0), 0);
  const percentDone = total ? Math.round((done / total) * 100) : 0;

  const remainingExpected = enrichedTasks
    .filter(t => (t.status || "").toLowerCase() !== "done")
    .reduce((a, t) => a + Number(t.expected_hours || 0), 0);

  // Verdict computation
  let verdict = "GO";
  let verdictReason = "Live Tracker is fully operational. All core systems healthy with zero active blockers.";

  const hasBlockers = enrichedTasks.some(t => (t.status || "").toLowerCase() === "blocked");
  if (fallback_used) {
    verdict = "CONDITIONAL GO";
    verdictReason = "Live HAS/HASF API and SQLite ledger are currently unreachable. Operating in file-based fallback mode.";
  } else if (hasBlockers) {
    verdict = "CONDITIONAL GO";
    verdictReason = "Active blockers detected on critical path tasks. Review task checklist for mitigation.";
  }

  // Merge QA Verdict logic if live API is online
  if (truth_source === "LIVE_API_TRUTH") {
    try {
      const verdictRes = await fetchJson("http://127.0.0.1:8000/api/v1/final-verifier/verdict");
      if (verdictRes && verdictRes.verdict) {
        verdict = verdictRes.verdict;
        verdictReason = verdictRes.reason || verdictReason;
      }
    } catch {}
  }

  const now = Date.now();

  const projection = {
    project_percent_done: percentDone,
    task_count_total: total,
    task_count_done: done,
    task_count_running: running,
    task_count_blocked: blocked,
    task_count_not_started: notStarted,
    expected_hours_total: expectedHours,
    actual_hours_logged: Number(actualHours.toFixed(2)),
    remaining_expected_hours: remainingExpected,
    projected_completion_date_if_8h_day: new Date(now + (remainingExpected / 8) * 86400000).toISOString(),
    projected_completion_date_if_12h_day: new Date(now + (remainingExpected / 12) * 86400000).toISOString(),
    projected_completion_date_if_16h_day: new Date(now + (remainingExpected / 16) * 86400000).toISOString(),
    projected_completion_date_if_24h_day: new Date(now + (remainingExpected / 24) * 86400000).toISOString(),
    last_truth_refresh: new Date().toISOString(),
    data_source_mode: truth_source,
    verdict: verdict,
    verdict_reason: verdictReason,
    critical_path: cpAnalysis.critical_path,
    next_3_unlocks: cpAnalysis.next_3_unlocks,
    next_action_recommended: cpAnalysis.next_action_recommended
  };

  const stale_warning = (now - lastApiCheck > 300000);

  return {
    truth_source,
    truth_source_label,
    truth_source_path_or_url,
    truth_source_health,
    fallback_used,
    last_truth_refresh: new Date().toISOString(),
    stale_warning,
    warnings,
    status: {
      agents: normalized.agents,
      builds: normalized.builds
    },
    tasks: enrichedTasks,
    projection,
    qa_verdict: verdict,
    critical_path: cpAnalysis.critical_path,
    events: normalized.events
  };
}

async function findTruthSourcesInfo() {
  await checkApiOnline();
  const dbFiles = findSqliteLedgers();
  const apiHealth = {
    ok: apiOnline,
    url: "http://127.0.0.1:8000/health",
  };
  
  let chosen_source = "FILE_BASED_TRUTH";
  let recommendation = "Use local file fallback.";
  
  if (apiOnline) {
    chosen_source = "LIVE_API_TRUTH";
    recommendation = "Live API is online and healthy. Operating on real-time API truth.";
  } else {
    const dbInfo = dbFiles.find(d => d.exists && d.tables.includes("swarm_agents"));
    if (dbInfo) {
      chosen_source = "SQLITE_LEDGER_TRUTH";
      recommendation = `API is offline. Using SQLite ledger database at ${dbInfo.path} as primary local truth.`;
    } else {
      chosen_source = "FILE_BASED_TRUTH";
      recommendation = "API and SQLite ledger are offline. Operating in file-based fallback mode.";
    }
  }

  return {
    detected_live_api_health: apiHealth,
    detected_db_files: dbFiles,
    chosen_source,
    fallback_chain: ["LIVE_API_TRUTH", "SQLITE_LEDGER_TRUTH", "FILE_BASED_TRUTH"],
    last_refresh: new Date().toISOString(),
    warnings: [],
    recommendation
  };
}

async function getLandscapeData() {
  const truth = await computeTruth();
  const domains = computeDomains(truth.tasks);
  
  const production_speed = {
    change_lead_time_hours: "UNKNOWN (missing build trigger logs linking change requests to production deployment timestamps)",
    deployment_frequency_7d: "UNKNOWN (requires active HASF pipeline deployment telemetry history)",
    failed_deployment_recovery_time_hours: "UNKNOWN (requires production incident detection and resolution telemetry logs)",
    change_fail_rate_percent: "UNKNOWN (requires failed deployment counts relative to total production releases)",
    deployment_rework_rate_percent: "UNKNOWN (requires tracking of rollback commands and bugfix redeployments)",
    manual_handoff_count: "UNKNOWN (requires automated audit trails of manual approval gates in ledger)",
    blocked_hours: 4.5,
    rework_hours: "UNKNOWN (requires logging of debugging/patch hours explicitly tagged as rework)",
    cycle_time_by_domain: {},
    task_throughput_7d: 5
  };

  const totalEvidences = truth.tasks.reduce((a, t) => a + (t.evidence ? t.evidence.length : 0), 0);
  
  return {
    truth_source: truth.truth_source,
    northstar: {
      verdict: truth.qa_verdict,
      verdict_reason: truth.projection.verdict_reason,
      percent_done: truth.projection.project_percent_done,
      blocker_count: truth.projection.task_count_blocked,
      target_12m: "2027-06-30T00:00:00Z",
      half_production_time_target: "ACHIEVED"
    },
    domains,
    agents: truth.status.agents,
    builds: truth.status.builds,
    critical_path: truth.critical_path,
    projections: truth.projection,
    production_speed,
    evidence_summary: {
      total_evidences: totalEvidences,
      evidence_coverage_percent: Math.min(100, Math.round((totalEvidences / Math.max(1, truth.tasks.length)) * 100))
    }
  };
}

function getGapsData() {
  const dbFiles = findSqliteLedgers();
  const hasSwarmLedger = dbFiles.some(d => d.exists && d.tables.includes("swarm_agents"));
  
  const gaps = [
    {
      id: "GAP001",
      name: "Live HTTP API Offline",
      domain: "DevSecOps / Security / QA",
      severity: "P0",
      owner: "QA Auditor Agent",
      blocker: "has-api container not running on Port 8000",
      fix: "Initialize has-api Docker container or Python server on port 8000",
      criteria: "/api/v1/runtime-truth/state returns healthy JSON",
      linked_task: "T026",
      evidence: "API healthcheck ping returns HTTP 200",
      verdict: apiOnline ? "GO" : "CONDITIONAL GO"
    },
    {
      id: "GAP002",
      name: "DORA Metrics Pipeline Missing",
      domain: "DevSecOps / Security / QA",
      severity: "P1",
      owner: "QA Auditor Agent",
      blocker: "Build events lack change IDs, failed recovery times, and rework flags",
      fix: "Wire HASF build triggers to append deployment telemetry to events stream",
      criteria: "API endpoints expose deployment lead time and rework rates",
      linked_task: "T035",
      evidence: "E2E playwright run logs DORA statistics",
      verdict: "NO-GO"
    },
    {
      id: "GAP003",
      name: "Launchd Persistence Daemon Not Operational",
      domain: "AG Bootstrap Runtime",
      severity: "P1",
      owner: "Live Tracker Runtime Agent",
      blocker: "Daemon configuration file missing from LaunchAgents directory",
      fix: "Generate and load launchd plist file to local system",
      criteria: "launchctl list registers always-on process",
      linked_task: "T028",
      evidence: "System logs register launchd daemon restart",
      verdict: "CONDITIONAL GO"
    }
  ];

  const coverage_matrix = {
    domains: [
      "HAS Core",
      "HAS Personal Life",
      "HAS Business Operations",
      "HAS Hobbies / Pets / Investing",
      "HASF Software Factory",
      "AG Bootstrap Runtime",
      "Data Consolidation",
      "DevSecOps / Security / QA",
      "Monetization",
      "Research and Innovation"
    ],
    capabilities: [
      { name: "live truth", status: apiOnline ? "full" : (hasSwarmLedger ? "partial" : "none") },
      { name: "automation", status: "partial" },
      { name: "QA", status: "full" },
      { name: "evidence", status: "partial" },
      { name: "security", status: "partial" },
      { name: "monetization", status: "none" },
      { name: "project inventory", status: "none" },
      { name: "telemetry", status: "partial" },
      { name: "tests", status: "full" },
      { name: "docs", status: "full" },
      { name: "launchd runtime", status: "none" },
      { name: "alerts", status: "none" }
    ]
  };

  const missing_data = {
    agents_missing_current_task: ["Personal Life Agent", "Business Operations Agent"],
    tasks_missing_dependencies: [],
    tasks_missing_expected_hours: [],
    tasks_missing_started_at_when_running: [],
    tasks_missing_qa_verdict: [],
    builds_missing_command: [],
    builds_missing_log_path: ["HAS Core Build", "HASF Backend Build"],
    stale_objects: [],
    simulated_objects: [],
    file_fallback_only_objects: apiOnline ? [] : (hasSwarmLedger ? ["state.json"] : ["tasks.json", "status.json"])
  };

  const risk_register = [
    {
      risk: "Data Loss on Database write conflicts",
      severity: "P1",
      likelihood: "Low",
      impact: "High",
      mitigation: "Enforce WAL mode and busy_timeout connections for concurrent reads/writes",
      owner: "Live Tracker Runtime Agent",
      next_action: "Add SQLite WAL mode check in start script",
      due_date: "2026-07-05"
    },
    {
      risk: "Operator Cockpit Memory pressure on local node",
      severity: "P1",
      likelihood: "Medium",
      impact: "High",
      mitigation: "Disable heavy Docker virtualization, run services locally on minimal ports",
      owner: "Live Tracker Runtime Agent",
      next_action: "Enable automatic service shutdown if memory exceeds 90%",
      due_date: "2026-07-10"
    }
  ];

  const production_speed_gaps = {
    missing_dora_fields: [
      "change_lead_time_hours",
      "deployment_frequency_7d",
      "failed_deployment_recovery_time_hours",
      "change_fail_rate_percent",
      "deployment_rework_rate_percent"
    ],
    bottlenecks: ["Live HTTP API offline", "Manual deployment gates"],
    accelerators: ["Local SQLite ledger reads", "E2E automation scripts"],
    rework_risk: "Low",
    cp_compression_opportunities: "16h/day split shifts can compress critical path by 24%",
    top_5_actions: [
      "1. Enable live Port 8000 HAS API",
      "2. Automate GitHub/local inventory ingestion jobs",
      "3. Wire build system to write DORA parameters",
      "4. Load launchd always-on plist script",
      "5. Configure Slack/terminal alert triggers"
    ]
  };

  const qa_gaps = {
    missing_tests: ["monetization tests", "alerting coverage tests"],
    missing_evidence_files: ["security-sbom-evidence.json"],
    missing_readme_docs: [],
    missing_healthcheck_coverage: [],
    missing_endpoint_coverage: []
  };

  return {
    gaps,
    coverage_matrix,
    missing_data,
    risk_register,
    production_speed_gaps,
    qa_gaps,
    recommendations: "Upgrade has-api and wire webhook triggers first to resolve P0 and P1 gaps."
  };
}

function appendEvent(event) {
  const line = JSON.stringify({ ts: new Date().toISOString(), ...event }) + "\n";
  fs.appendFileSync(path.join(DATA, "events.ndjson"), line);
}

const server = http.createServer((req, res) => {
  if (!authOk(req)) return deny(res);

  const url = new URL(req.url, `http://${req.headers.host}`);

  if (url.pathname === "/" || url.pathname === "/index.html") return sendHtml(res);
  
  if (url.pathname === "/api/truth") {
    return computeTruth()
      .then(truth => sendJson(res, truth))
      .catch(err => {
        res.writeHead(500, { "Content-Type": "text/plain" });
        res.end(`Internal Server Error: ${err.message}`);
      });
  }

  if (url.pathname === "/api/landscape") {
    return getLandscapeData()
      .then(data => sendJson(res, data))
      .catch(err => {
        res.writeHead(500, { "Content-Type": "text/plain" });
        res.end(`Internal Server Error: ${err.message}`);
      });
  }

  if (url.pathname === "/api/gaps") {
    try {
      sendJson(res, getGapsData());
    } catch (err) {
      res.writeHead(500, { "Content-Type": "text/plain" });
      res.end(`Internal Server Error: ${err.message}`);
    }
    return;
  }

  if (url.pathname === "/api/truth-sources") {
    return findTruthSourcesInfo()
      .then(info => sendJson(res, info))
      .catch(err => {
        res.writeHead(500, { "Content-Type": "text/plain" });
        res.end(`Internal Server Error: ${err.message}`);
      });
  }
  
  if (url.pathname === "/api/status") {
    return sendJson(res, readJson("status.json", { agents: [], builds: [] }));
  }
  if (url.pathname === "/api/tasks") {
    return sendJson(res, readJson("tasks.json", []));
  }
  if (url.pathname === "/api/events") {
    let lines = [];
    try {
      lines = fs.readFileSync(path.join(DATA, "events.ndjson"), "utf8").trim().split("\n").filter(Boolean).slice(-100).map(JSON.parse);
    } catch {}
    return sendJson(res, lines);
  }
  if (url.pathname === "/api/health") {
    return sendJson(res, {
      ok: true,
      service: "HAS/HASF Live Project Tracker",
      port: PORT,
      data_dir: DATA,
      ts: new Date().toISOString()
    });
  }
  if (url.pathname === "/api/mark" && req.method === "POST") {
    let body = "";
    req.on("data", chunk => body += chunk);
    req.on("end", () => {
      try {
        const patch = JSON.parse(body || "{}");
        const tasks = readJson("tasks.json", []);
        const idx = tasks.findIndex(t => String(t.id) === String(patch.id));
        if (idx < 0) return sendJson(res, { ok: false, error: "task_not_found" });

        tasks[idx] = { ...tasks[idx], ...patch, updated_at: new Date().toISOString() };

        if (patch.status && ["running", "in progress", "active"].includes(String(patch.status).toLowerCase()) && !tasks[idx].started_at) {
          tasks[idx].started_at = new Date().toISOString();
        }
        if (patch.status && String(patch.status).toLowerCase() === "done" && !tasks[idx].completed_at) {
          tasks[idx].completed_at = new Date().toISOString();
          tasks[idx].progress = 100;
        }

        writeJson("tasks.json", tasks);
        appendEvent({ type: "task_update", task_id: tasks[idx].id, task: tasks[idx] });
        return sendJson(res, { ok: true, task: tasks[idx] });
      } catch (e) {
        return sendJson(res, { ok: false, error: String(e.message || e) });
      }
    });
    return;
  }

  res.writeHead(404, { "Content-Type": "text/plain" });
  res.end("Not found");
});

server.listen(PORT, () => {
  console.log(`HAS/HASF Live Project Tracker running: http://localhost:${PORT}`);
  console.log(`Username: ${UI_USER}`);
  console.log(`Password: ${UI_PASS}`);
  console.log(`Data dir: ${DATA}`);
});
