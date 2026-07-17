import { createClient } from '@supabase/supabase-js'

type AgentRunStatus = 'STARTED' | 'SUCCESS' | 'FAILED' | 'SKIPPED'

export interface AgentRunLogInput {
  agentName: string
  route?: string
  trigger?: string
  status: AgentRunStatus
  conflictDay?: number
  durationMs?: number
  detail?: Record<string, unknown>
  errorMessage?: string
  startedAt?: string
  finishedAt?: string
}

export async function logAgentRun(input: AgentRunLogInput): Promise<void> {
  const url = process.env.NEXT_PUBLIC_SUPABASE_URL
  const key = process.env.SUPABASE_SERVICE_ROLE_KEY ?? process.env.SUPABASE_SERVICE_KEY
  if (!url || !key) return

  try {
    const sb = createClient(url, key)
    await sb.from('agent_run_logs').insert({
      agent_name: input.agentName,
      route: input.route ?? null,
      trigger: input.trigger ?? 'manual',
      status: input.status,
      conflict_day: input.conflictDay ?? null,
      duration_ms: input.durationMs ?? null,
      detail: input.detail ?? {},
      error_message: input.errorMessage ?? null,
      started_at: input.startedAt ?? null,
      finished_at: input.finishedAt ?? null,
    })
  } catch {
    // Logging must never break primary route behavior.
  }
}
