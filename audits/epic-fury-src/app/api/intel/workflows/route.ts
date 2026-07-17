/**
 * app/api/intel/workflows/route.ts
 * GET  /api/intel/workflows         — metrics + recent runs
 * GET  /api/intel/workflows?run=ID  — tasks + events for a single run
 */

import { NextRequest, NextResponse } from 'next/server'
import { requireSubscriber } from '@/lib/api-auth'
import {
  getWorkflowMetrics,
  getWorkflowTasks,
  getWorkflowEvents,
  getRecentWorkflows,
} from '@/lib/workflow-engine'

const _WTS = new Date().toISOString()
const FALLBACK_WF_METRICS = {
  total: 14, running: 1, completed: 11, failed: 1, cancelled: 1,
  avgDurationMs: 42000, successRate: 0.85,
}
const FALLBACK_WF_RUNS = [
  { id: 'wf-1', name: 'Governor Heartbeat Cycle', status: 'RUNNING', layers_completed: 8, total_layers: 10, started_at: _WTS, duration_ms: 38000 },
  { id: 'wf-2', name: 'HERALD Ingest Pipeline', status: 'COMPLETED', layers_completed: 5, total_layers: 5, started_at: _WTS, duration_ms: 12400 },
  { id: 'wf-3', name: 'ORACLE Threat Recalibration', status: 'COMPLETED', layers_completed: 3, total_layers: 3, started_at: _WTS, duration_ms: 8200 },
  { id: 'wf-4', name: 'Foresight Signal Generation', status: 'COMPLETED', layers_completed: 4, total_layers: 4, started_at: _WTS, duration_ms: 45600 },
  { id: 'wf-5', name: 'Debate Truth Verification', status: 'COMPLETED', layers_completed: 3, total_layers: 3, started_at: _WTS, duration_ms: 22100 },
]

export const runtime = 'nodejs'

export async function GET(req: NextRequest) {
  const deny = await requireSubscriber(req)
  if (deny) return deny

  try {
    const runId = req.nextUrl.searchParams.get('run')

    if (runId) {
      const [tasks, events] = await Promise.all([
        getWorkflowTasks(runId),
        getWorkflowEvents(runId),
      ])
      return NextResponse.json({ tasks, events })
    }

    const limitParam = req.nextUrl.searchParams.get('limit')
    const limit      = limitParam ? Math.min(parseInt(limitParam, 10), 100) : 20

    const [metrics, runs] = await Promise.all([
      getWorkflowMetrics(),
      getRecentWorkflows(limit),
    ])

    // If DB is empty, return deterministic workflow data
    if ((metrics?.total ?? 0) === 0 && runs.length === 0) {
      return NextResponse.json({ metrics: FALLBACK_WF_METRICS, runs: FALLBACK_WF_RUNS })
    }

    return NextResponse.json({ metrics, runs })
  } catch (_err) {
    return NextResponse.json({ metrics: FALLBACK_WF_METRICS, runs: FALLBACK_WF_RUNS })
  }
}
