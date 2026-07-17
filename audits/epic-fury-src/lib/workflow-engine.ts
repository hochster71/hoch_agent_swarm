/**
 * lib/workflow-engine.ts
 *
 * Temporal.io-inspired Durable Workflow Engine
 * ─────────────────────────────────────────────
 * Implements Temporal patterns on Vercel serverless + Supabase:
 *   • Durable execution state   (workflow_runs table)
 *   • Activity task history     (workflow_tasks table)
 *   • Complete event history    (workflow_events table)
 *   • Task Queue Priority       (priority 1–10, ordered queries)
 *   • Worker versioning         (workflow_version per run)
 *   • Continue-as-new           (parent_run_id chain)
 *   • Nexus cross-service calls (startChildWorkflow + NEXUS_CALL events)
 *   • Automatic retry tracking  (retry_count / max_retries)
 */

import { createClient } from '@supabase/supabase-js'

// ---------------------------------------------------------------------------
// Supabase client (server-side service role)
// ---------------------------------------------------------------------------

function getSupabase() {
  return createClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.SUPABASE_SERVICE_ROLE_KEY!,
  )
}

// ---------------------------------------------------------------------------
// Public types
// ---------------------------------------------------------------------------

export type WorkflowType =
  | 'GOVERNOR_CYCLE'
  | 'DEBATE_SESSION'
  | 'VISUAL_GEN'
  | 'REVENUE_OPT'
  | 'HEAL_CYCLE'
  | 'DGM_MUTATION'
  | 'INTEL_INGEST'

export type WorkflowStatus = 'RUNNING' | 'COMPLETED' | 'FAILED' | 'PAUSED' | 'RETRYING'
export type TaskStatus     = 'PENDING' | 'RUNNING'  | 'COMPLETED' | 'FAILED' | 'SKIPPED'
export type TaskType       = 'ACTIVITY' | 'SIGNAL' | 'TIMER' | 'NEXUS_CALL'

export interface WorkflowRun {
  id:               string
  workflow_type:    WorkflowType
  workflow_version: string
  status:           WorkflowStatus
  priority:         number
  namespace:        string
  task_queue:       string
  input_payload:    Record<string, unknown>
  output_payload:   Record<string, unknown> | null
  started_at:       string
  completed_at:     string | null
  retry_count:      number
  max_retries:      number
  parent_run_id:    string | null
  duration_ms:      number | null
  error:            string | null
  created_at:       string
}

export interface WorkflowTask {
  id:           string
  run_id:       string
  task_name:    string
  task_type:    TaskType
  status:       TaskStatus
  started_at:   string | null
  completed_at: string | null
  output:       Record<string, unknown> | null
  error:        string | null
  retry_count:  number
  created_at:   string
}

export interface WorkflowEvent {
  id:         string
  run_id:     string
  event_type: string
  payload:    Record<string, unknown>
  created_at: string
}

export interface WorkflowMetrics {
  total:          number
  running:        number
  completed:      number
  failed:         number
  retrying:       number
  avgDurationMs:  number | null
  successRate:    number   // 0–100
  recentRuns:     WorkflowRun[]
}

export interface StartWorkflowOpts {
  priority?:    number   // 1 (low) – 10 (critical), default 5
  taskQueue?:   string   // e.g. 'governor', 'debate', 'visual', default 'default'
  namespace?:   string   // Temporal namespace isolation, default 'epic-fury'
  maxRetries?:  number   // default 3
  version?:     string   // worker version, default 'v1'
  parentRunId?: string   // Nexus / continue-as-new parent link
}

// ---------------------------------------------------------------------------
// startWorkflow — Temporal: workflow.start()
// Creates a durable run record and emits WORKFLOW_STARTED event.
// Returns the new run ID (uuid).
// ---------------------------------------------------------------------------

export async function startWorkflow(
  type:  WorkflowType,
  input: Record<string, unknown>,
  opts:  StartWorkflowOpts = {},
): Promise<string> {
  enforceTruthProtocol(input, type, 'input')
  const sb = getSupabase()

  const { data, error } = await sb
    .from('workflow_runs')
    .insert({
      workflow_type:    type,
      workflow_version: opts.version    ?? 'v1',
      status:           'RUNNING',
      priority:         opts.priority   ?? 5,
      namespace:        opts.namespace  ?? 'epic-fury',
      task_queue:       opts.taskQueue  ?? 'default',
      input_payload:    input,
      max_retries:      opts.maxRetries ?? 3,
      parent_run_id:    opts.parentRunId ?? null,
      started_at:       new Date().toISOString(),
    })
    .select('id')
    .single()

  if (error || !data) throw new Error(`startWorkflow(${type}) failed: ${error?.message}`)

  // Fire WORKFLOW_STARTED event — non-blocking fire-and-forget; errors are swallowed
  void appendEvent(data.id, 'WORKFLOW_STARTED', { type, priority: opts.priority ?? 5, taskQueue: opts.taskQueue ?? 'default', version: opts.version ?? 'v1', input })

  return data.id as string
}

// ---------------------------------------------------------------------------
// recordTask — Temporal: activity result
// Appends a task record and emits a TASK_<STATUS> event.
// ---------------------------------------------------------------------------

export async function recordTask(
  runId:    string,
  taskName: string,
  taskType: TaskType,
  status:   TaskStatus,
  output?:  Record<string, unknown>,
  error?:   string,
): Promise<void> {
  if (output) {
    enforceTruthProtocol(output, taskType, 'output')
  }
  const sb  = getSupabase()
  const now = new Date().toISOString()

  await sb.from('workflow_tasks').insert({
    run_id:       runId,
    task_name:    taskName,
    task_type:    taskType,
    status,
    started_at:   now,
    completed_at: now,
    output:       output ?? null,
    error:        error  ?? null,
  })

  void appendEvent(runId, `TASK_${status}`, { taskName, taskType, output, error })
}

// ---------------------------------------------------------------------------
// appendEvent — Temporal: event history append
// Writes a single event to workflow_events for full audit trail.
// ---------------------------------------------------------------------------

export async function appendEvent(
  runId:     string,
  eventType: string,
  payload:   Record<string, unknown>,
): Promise<void> {
  const sb = getSupabase()

  await sb.from('workflow_events').insert({
    run_id:     runId,
    event_type: eventType,
    payload,
    created_at: new Date().toISOString(),
  })
}

// ---------------------------------------------------------------------------
// TRUTH PROTOCOL ENFORCEMENT
// ---------------------------------------------------------------------------
export function enforceTruthProtocol(payload: Record<string, unknown>, type: string, direction: 'input'|'output') {
  // Mandate 'sources' array for any intel payload to ensure 100% accuracy via citations
  if (type === 'INTEL_INGEST' && direction === 'output') {
    if (!Array.isArray(payload.sources) || payload.sources.length === 0) {
      console.warn(`[TRUTH PROTOCOL] Warning: ${type} missing sources array in ${direction}. Flagged as RUMOR.`);
      payload.isRumor = true;
    }
  }
}


// ---------------------------------------------------------------------------
// completeWorkflow — Temporal: workflow result resolved
// ---------------------------------------------------------------------------

export async function completeWorkflow(
  runId:  string,
  output: Record<string, unknown>,
): Promise<void> {
  const sb  = getSupabase()
  const now = new Date().toISOString()

  const { data: run } = await sb
    .from('workflow_runs')
    .select('started_at')
    .eq('id', runId)
    .single()

  const durationMs = run ? Date.now() - new Date(run.started_at).getTime() : null

  await sb.from('workflow_runs').update({
    status:         'COMPLETED',
    output_payload: output,
    completed_at:   now,
    duration_ms:    durationMs,
  }).eq('id', runId)

  void appendEvent(runId, 'WORKFLOW_COMPLETED', { output, durationMs })
}

// ---------------------------------------------------------------------------
// failWorkflow — Temporal: workflow terminated with error
// If shouldRetry=true and retry_count < max_retries, sets status = RETRYING.
// ---------------------------------------------------------------------------

export async function failWorkflow(
  runId:       string,
  error:       string,
  shouldRetry  = false,
): Promise<void> {
  const sb  = getSupabase()
  const now = new Date().toISOString()

  const { data: run } = await sb
    .from('workflow_runs')
    .select('started_at, retry_count, max_retries')
    .eq('id', runId)
    .single()

  const durationMs = run ? Date.now() - new Date(run.started_at).getTime() : null
  const canRetry   = shouldRetry && run && run.retry_count < run.max_retries

  await sb.from('workflow_runs').update({
    status:       canRetry ? 'RETRYING' : 'FAILED',
    error,
    completed_at: canRetry ? null : now,
    duration_ms:  durationMs,
    retry_count:  run ? run.retry_count + (canRetry ? 1 : 0) : 0,
  }).eq('id', runId)

  void appendEvent(runId, canRetry ? 'WORKFLOW_RETRYING' : 'WORKFLOW_FAILED', {
    error,
    canRetry,
    durationMs,
    retryCount: run ? run.retry_count + (canRetry ? 1 : 0) : 0,
  })
}

// ---------------------------------------------------------------------------
// continueAsNew — Temporal: continueAsNew()
// Archives the current run as COMPLETED (with a continue-as-new marker),
// then starts a fresh run of the same workflow type linked via parent_run_id.
// Used for long-running governor cycles to avoid payload bloat.
// ---------------------------------------------------------------------------

export async function continueAsNew(
  runId:    string,
  newInput: Record<string, unknown>,
): Promise<string> {
  const sb  = getSupabase()
  const now = new Date().toISOString()

  const { data: run } = await sb
    .from('workflow_runs')
    .select('workflow_type, workflow_version, priority, namespace, task_queue, max_retries, started_at')
    .eq('id', runId)
    .single()

  if (!run) throw new Error(`continueAsNew: run ${runId} not found`)

  const durationMs = Date.now() - new Date(run.started_at).getTime()

  // Archive old run
  await sb.from('workflow_runs').update({
    status:         'COMPLETED',
    output_payload: { continued_as_new: true },
    completed_at:   now,
    duration_ms:    durationMs,
  }).eq('id', runId)

  void appendEvent(runId, 'CONTINUE_AS_NEW', { newInput, durationMs })

  // Start fresh run, linked to archived run
  return startWorkflow(run.workflow_type as WorkflowType, newInput, {
    priority:    run.priority,
    taskQueue:   run.task_queue,
    namespace:   run.namespace,
    maxRetries:  run.max_retries,
    version:     run.workflow_version,
    parentRunId: runId,
  })
}

// ---------------------------------------------------------------------------
// startChildWorkflow — Temporal: Nexus cross-service orchestration
// Starts a child workflow linked to a parent run via parent_run_id.
// Emits a NEXUS_CALL event on the parent for full audit trail.
// ---------------------------------------------------------------------------

export async function startChildWorkflow(
  parentRunId: string,
  type:        WorkflowType,
  input:       Record<string, unknown>,
  opts:        Omit<StartWorkflowOpts, 'parentRunId'> = {},
): Promise<string> {
  const childRunId = await startWorkflow(type, input, { ...opts, parentRunId })
  void appendEvent(parentRunId, 'NEXUS_CALL', { childType: type, childRunId, input })
  return childRunId
}

// ---------------------------------------------------------------------------
// getPriorityQueue — Task Queue Priority & Fairness
// Returns active runs ordered by priority DESC (highest first), then FIFO.
// ---------------------------------------------------------------------------

export async function getPriorityQueue(
  taskQueue: string,
  limit      = 20,
): Promise<WorkflowRun[]> {
  const sb = getSupabase()

  const { data } = await sb
    .from('workflow_runs')
    .select('*')
    .eq('task_queue', taskQueue)
    .in('status', ['RUNNING', 'PAUSED', 'RETRYING'])
    .order('priority',   { ascending: false })
    .order('created_at', { ascending: true })
    .limit(limit)

  return (data ?? []) as WorkflowRun[]
}

// ---------------------------------------------------------------------------
// getWorkflowMetrics — aggregate stats for WorkflowPanel
// ---------------------------------------------------------------------------

export async function getWorkflowMetrics(): Promise<WorkflowMetrics> {
  const sb = getSupabase()

  const [allRes, recentRes] = await Promise.all([
    sb.from('workflow_runs')
      .select('status, duration_ms')
      .order('created_at', { ascending: false })
      .limit(200),
    sb.from('workflow_runs')
      .select('*')
      .order('created_at', { ascending: false })
      .limit(10),
  ])

  const runs      = allRes.data ?? []
  const total     = runs.length
  const running   = runs.filter(r => r.status === 'RUNNING').length
  const completed = runs.filter(r => r.status === 'COMPLETED').length
  const failed    = runs.filter(r => r.status === 'FAILED').length
  const retrying  = runs.filter(r => r.status === 'RETRYING').length

  const durations = runs
    .filter(r => r.duration_ms != null)
    .map(r => r.duration_ms as number)
  const avgDurationMs = durations.length
    ? Math.round(durations.reduce((a, b) => a + b, 0) / durations.length)
    : null

  const successRate = total > 0 ? Math.round((completed / total) * 100) : 0

  return {
    total,
    running,
    completed,
    failed,
    retrying,
    avgDurationMs,
    successRate,
    recentRuns: (recentRes.data ?? []) as WorkflowRun[],
  }
}

// ---------------------------------------------------------------------------
// getRecentWorkflows — last N runs for dashboard list
// ---------------------------------------------------------------------------

export async function getRecentWorkflows(limit = 20): Promise<WorkflowRun[]> {
  const sb = getSupabase()

  const { data } = await sb
    .from('workflow_runs')
    .select('*')
    .order('created_at', { ascending: false })
    .limit(limit)

  return (data ?? []) as WorkflowRun[]
}

// ---------------------------------------------------------------------------
// getWorkflowTasks — task history for a single run
// ---------------------------------------------------------------------------

export async function getWorkflowTasks(runId: string): Promise<WorkflowTask[]> {
  const sb = getSupabase()

  const { data } = await sb
    .from('workflow_tasks')
    .select('*')
    .eq('run_id', runId)
    .order('created_at', { ascending: true })

  return (data ?? []) as WorkflowTask[]
}

// ---------------------------------------------------------------------------
// getWorkflowEvents — full event history for a single run
// ---------------------------------------------------------------------------

export async function getWorkflowEvents(runId: string): Promise<WorkflowEvent[]> {
  const sb = getSupabase()

  const { data } = await sb
    .from('workflow_events')
    .select('*')
    .eq('run_id', runId)
    .order('created_at', { ascending: true })

  return (data ?? []) as WorkflowEvent[]
}

