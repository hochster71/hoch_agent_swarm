/**
 * lib/autonomous-engine.ts
 *
 * Autonomous Enhancement Cycle (AEC) — the Governor's self-improvement loop.
 *
 * Every N heartbeats the Governor:
 *  1. Runs a self-audit (KG coverage, verified-rate, error-rate)
 *  2. Researches latest AI/ML advancements via Grok (xAI API)
 *  3. Proposes a concrete improvement via GPT-4o-mini
 *  4. Creates a GitHub PR with the proposed change
 *  5. Triggers a Vercel deploy-hook preview
 *  6. Auto-merges if AUTO_MERGE_ENABLED=true (defaults to false — safe)
 *  7. Updates the live system prompt in platform_config if it's a PROMPT_UPDATE
 *  8. Logs the full cycle to autonomous_cycles
 *
 * Required env vars (all optional — engine degrades gracefully if unset):
 *   XAI_API_KEY        — xAI / Grok research API
 *   GITHUB_PAT         — personal access token with repo + PR rights
 *   GITHUB_REPO_OWNER  — e.g. hochster71
 *   GITHUB_REPO_NAME   — e.g. epic-fury-2026
 *   VERCEL_DEPLOY_HOOK_URL — Vercel deploy hook URL for preview deploys
 *   AUTO_MERGE_ENABLED — set to "true" to allow autonomous PR merging
 */

import { createClient } from '@supabase/supabase-js'
import OpenAI            from 'openai'
import { setSystemDirectives } from './ai-engine'

const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL ?? 'http://localhost:54321',
  process.env.SUPABASE_SERVICE_ROLE_KEY ?? 'placeholder-service-key'
)

// ── Types ─────────────────────────────────────────────────────────────────────

export interface AuditFindings {
  intelTotal:        number
  verifiedRate:      number
  cycleErrorRate:    number
  kgEntityCount:     number
  recentEscalations: number
  suggestions:       string[]
}

export interface EnhancementProposal {
  type:          'CODE_MUTATION' | 'PROMPT_UPDATE' | 'SECURITY_PATCH' | 'MONETIZATION' | 'FORESIGHT' | 'WORKFLOW'
  title:         string
  description:   string
  filePath?:     string
  newContent?:   string
  promptUpdate?: string
  rationale:     string
}

export interface AutonomousCycleResult {
  cycleNumber:      number
  auditFindings:    AuditFindings
  researchSummary:  string
  enhancement:      EnhancementProposal
  prUrl?:           string
  prNumber?:        number
  deploymentUrl?:   string
  deploymentStatus: 'PENDING' | 'PASSED' | 'FAILED' | 'MERGED' | 'SKIPPED'
  autoMerged:       boolean
  durationMs:       number
}

// ── Step 1: Self-Audit ────────────────────────────────────────────────────────

export async function selfAudit(): Promise<AuditFindings> {
  const [intelRes, cycleRes, entityRes, escalationRes, verifiedRes] = await Promise.allSettled([
    supabase.from('intel').select('id', { count: 'exact' }).limit(1),
    supabase.from('governor_cycles').select('error').order('created_at', { ascending: false }).limit(20),
    supabase.from('kg_entities').select('id', { count: 'exact' }).limit(1),
    supabase.from('governor_cycles').select('escalations').order('created_at', { ascending: false }).limit(5),
    // Run concurrently with above — eliminates a sequential round-trip that fired
    // only when intelTotal > 0 (a conditional await in a hot code path).
    supabase.from('intel').select('id', { count: 'exact' }).eq('verified', true).limit(1),
  ])

  const intelTotal    = intelRes.status    === 'fulfilled' ? (intelRes.value.count    ?? 0) : 0
  const verifiedCount = verifiedRes.status === 'fulfilled' ? (verifiedRes.value.count ?? 0) : 0
  const verifiedRate  = intelTotal > 0 ? verifiedCount / intelTotal : 0

  let cycleErrorRate = 0
  if (cycleRes.status === 'fulfilled' && cycleRes.value.data?.length) {
    const errors = cycleRes.value.data.filter((c: { error: unknown }) => c.error).length
    cycleErrorRate = errors / cycleRes.value.data.length
  }

  const kgEntityCount = entityRes.status === 'fulfilled' ? (entityRes.value.count ?? 0) : 0

  let recentEscalations = 0
  if (escalationRes.status === 'fulfilled' && escalationRes.value.data) {
    recentEscalations = escalationRes.value.data.reduce((acc: number, c: { escalations: unknown }) =>
      acc + (Array.isArray(c.escalations) ? c.escalations.length : 0), 0)
  }

  // ── Build suggestion pool with type variety ─────────────────────────────
  const pool: Array<{ priority: number; text: string }> = [
    // Metric-driven (high priority when metric fires)
    { priority: verifiedRate < 0.6     ? 10 : 0, text: 'Increase debate ensemble size to improve verification rate' },
    { priority: cycleErrorRate > 0.1   ? 10 : 0, text: 'Add retry logic to failing governor layers' },
    { priority: recentEscalations > 10 ? 10 : 0, text: 'Tune escalation thresholds to reduce noise' },
    // KG coverage — only include every other cycle so it doesn't dominate
    { priority: kgEntityCount < 200 ? 5 : 0,  text: 'Expand KG ingestion to increase entity coverage' },
    // Standing improvement candidates (always available, moderate priority)
    { priority: 3, text: 'Optimize LLM prompt tokens for cost reduction via prompt compression' },
    { priority: 3, text: 'Add 48H foresight horizon bucket between 24H and 72H for sharper short-term signals' },
    { priority: 3, text: 'Compress oracle threat probability JSON to reduce Supabase read/write bytes' },
    { priority: 3, text: 'Increase synthesis assessment NLP confidence threshold from 0.6 to 0.7' },
    { priority: 3, text: 'Add theater-specific decay weights to calibration scoring model' },
    { priority: 2, text: 'Profile and cache the top-3 most-called Supabase queries in platform_config' },
    { priority: 2, text: 'Introduce circuit-breaker pattern for Supabase read retries in governor layers' },
  ]

  // Shuffle within each priority tier to prevent same suggestion repeating
  const seeded = intelTotal + kgEntityCount  // deterministic but varies each cycle
  const sorted = pool
    .filter(s => s.priority > 0)
    .sort((a, b) => {
      const diff = b.priority - a.priority
      if (diff !== 0) return diff
      // Pseudo-random tiebreak based on cycle context
      return (a.text.charCodeAt(0) + seeded) % 7 - (b.text.charCodeAt(0) + seeded) % 7
    })

  const suggestions = sorted.map(s => s.text)
  if (suggestions.length === 0) suggestions.push('Optimize LLM prompt tokens for cost reduction')

  return { intelTotal, verifiedRate, cycleErrorRate, kgEntityCount, recentEscalations, suggestions }
}

// ── Step 2: Research with Grok ────────────────────────────────────────────────

export async function researchWithGrok(topic: string): Promise<string> {
  const apiKey = process.env.XAI_API_KEY ?? process.env.GROK_API_KEY
  if (!apiKey) return 'Grok research unavailable — XAI_API_KEY not set. Running deterministic fallback.'

  try {
    const res = await fetch('https://api.x.ai/v1/chat/completions', {
      method:  'POST',
      headers: { 'Authorization': `Bearer ${apiKey}`, 'Content-Type': 'application/json' },
      body: JSON.stringify({
        model: 'grok-3',
        messages: [{
          role:    'user',
          content: `You are a research assistant for an AI-powered conflict intelligence platform (EPIC FURY 2026+).
Research the very latest (March 2026) advancements most relevant to: ${topic}

Focus on: Temporal.io updates, neurosymbolic AI, GEA/DGM self-improvement, autonomous agents, multimodal news AI.
Be specific, technical, and actionable. Return 3–5 concrete findings implementable within a Next.js + Supabase + TypeScript stack.`,
        }],
        max_tokens:  700,
        temperature: 0.2,
      }),
    })
    if (!res.ok) return `Grok API error ${res.status}: ${await res.text()}`
    const data = await res.json()
    return data.choices?.[0]?.message?.content ?? 'No research output returned.'
  } catch (e) {
    return `Grok research failed: ${e instanceof Error ? e.message : String(e)}`
  }
}

// ── Step 3: Propose Enhancement ───────────────────────────────────────────────

export async function proposeEnhancement(
  auditFindings:   AuditFindings,
  researchSummary: string,
): Promise<EnhancementProposal> {
  const apiKey = process.env.OPENAI_API_KEY
  if (!apiKey) {
    return {
      type:        'FORESIGHT',
      title:       'Calibrate foresight confidence scoring',
      description: 'Adjust confidence decay function for signals older than 72h',
      rationale:   'Deterministic fallback — OPENAI_API_KEY not set',
      promptUpdate: 'Apply a decay multiplier of 0.85 per 24h to confidence scores for signals older than 72h. This prevents stale intelligence from inflating threat probabilities in the ORACLE-9 matrix.',
    }
  }

  const openai = new OpenAI({ apiKey })
  const prompt = `You are the EPIC FURY Platform Governor performing autonomous self-enhancement.

AUDIT FINDINGS:
- Intel total: ${auditFindings.intelTotal}
- Verified rate: ${(auditFindings.verifiedRate * 100).toFixed(1)}%
- Cycle error rate: ${(auditFindings.cycleErrorRate * 100).toFixed(1)}%
- KG entities: ${auditFindings.kgEntityCount}
- Recent escalations: ${auditFindings.recentEscalations}
- Top suggestion: ${auditFindings.suggestions[0]}

RESEARCH FINDINGS:
${researchSummary}

Propose ONE specific, concrete enhancement. RULES:
1. Choose type based on what is most actionable RIGHT NOW.
2. For CODE_MUTATION or SECURITY_PATCH: you MUST provide both filePath AND newContent (full updated file, max 80 lines).
3. For PROMPT_UPDATE, WORKFLOW, FORESIGHT, or MONETIZATION: you MUST provide promptUpdate — a concrete 2–4 sentence addendum describing the new behaviour for the governor system prompt. This field is REQUIRED and must not be empty or null.
4. Never return a response where both newContent and promptUpdate are absent — that produces a SKIPPED cycle with zero impact.
5. Prefer CODE_MUTATION for metric improvements, PROMPT_UPDATE for reasoning improvements, WORKFLOW only for multi-step process designs.
6. IMPORTANT: always include the "promptUpdate" key in your JSON response, even for CODE_MUTATION types (set it to "" if not applicable).

Respond as valid JSON only:
{
  "type": "CODE_MUTATION|PROMPT_UPDATE|SECURITY_PATCH|MONETIZATION|FORESIGHT|WORKFLOW",
  "title": "short title (max 60 chars)",
  "description": "what exactly changes and how",
  "rationale": "why this is the highest-value improvement right now",
  "filePath": "required for CODE_MUTATION/SECURITY_PATCH: relative path e.g. lib/oracle-engine.ts",
  "newContent": "required for CODE_MUTATION/SECURITY_PATCH: full updated file content (<80 lines)",
  "promptUpdate": "required for all other types: 2–4 sentence governor system prompt addendum"
}`

  try {
    const resp = await openai.chat.completions.create({
      model:           'gpt-4o-mini',
      messages:        [{ role: 'user', content: prompt }],
      response_format: { type: 'json_object' },
      max_tokens:      900,
    })
    const parsed = JSON.parse(resp.choices[0].message.content ?? '{}') as EnhancementProposal
    // Ensure promptUpdate is always present for non-code types
    if (!parsed.filePath && !parsed.promptUpdate) {
      parsed.promptUpdate = parsed.description
    }
    return parsed
  } catch {
    return {
      type:        'FORESIGHT',
      title:       'Increase foresight horizon granularity',
      description: 'Add 48H horizon bucket between 24H and 72H for sharper short-term signals',
      rationale:   'GPT-4o-mini parse failed — using safe fallback enhancement',
      promptUpdate: 'When computing foresight probability buckets, add a 48H horizon tier between the existing 24H and 72H tiers. Weight the 48H bucket at 0.4× of the 72H probability to sharpen near-term signal decay.',
    }
  }
}

// ── Step 4: Create GitHub PR ──────────────────────────────────────────────────

export async function createGithubPR(
  enhancement: EnhancementProposal,
): Promise<{ prUrl: string; prNumber: number } | null> {
  const token = process.env.GITHUB_PAT
  const owner = process.env.GITHUB_REPO_OWNER
  const repo  = process.env.GITHUB_REPO_NAME
  if (!token || !owner || !repo || !enhancement.filePath || !enhancement.newContent) return null

  const headers = {
    'Authorization':        `Bearer ${token}`,
    'Accept':               'application/vnd.github+json',
    'X-GitHub-Api-Version': '2022-11-28',
    'Content-Type':         'application/json',
  }
  const baseUrl = `https://api.github.com/repos/${owner}/${repo}`

  try {
    // 1. Get main SHA
    const refRes = await fetch(`${baseUrl}/git/refs/heads/main`, { headers })
    if (!refRes.ok) return null
    const baseSha = (await refRes.json()).object.sha

    // 2. Create branch
    const branchName = `governor/aec-${Date.now()}`
    const branchRes  = await fetch(`${baseUrl}/git/refs`, {
      method: 'POST', headers,
      body: JSON.stringify({ ref: `refs/heads/${branchName}`, sha: baseSha }),
    })
    if (!branchRes.ok) return null

    // 3. Get current file SHA for update
    const fileRes  = await fetch(`${baseUrl}/contents/${enhancement.filePath}?ref=main`, { headers })
    const fileSha  = fileRes.ok ? (await fileRes.json()).sha as string : undefined

    // 4. Write file to branch
    const fileBody: Record<string, string> = {
      message: `feat(governor): ${enhancement.title}`,
      content: Buffer.from(enhancement.newContent).toString('base64'),
      branch:  branchName,
    }
    if (fileSha) fileBody.sha = fileSha
    const updateRes = await fetch(`${baseUrl}/contents/${enhancement.filePath}`, {
      method: 'PUT', headers,
      body: JSON.stringify(fileBody),
    })
    if (!updateRes.ok) return null

    // 5. Open PR
    const prRes = await fetch(`${baseUrl}/pulls`, {
      method: 'POST', headers,
      body: JSON.stringify({
        title: `[GOVERNOR AUTO] ${enhancement.title}`,
        body:  `**Type**: ${enhancement.type}\n\n**Description**: ${enhancement.description}\n\n**Rationale**: ${enhancement.rationale}\n\n*Auto-generated by EPIC FURY Platform Governor AEC*`,
        head:  branchName,
        base:  'main',
        draft: false,
      }),
    })
    if (!prRes.ok) return null
    const prData = await prRes.json()
    return { prUrl: prData.html_url as string, prNumber: prData.number as number }
  } catch {
    return null
  }
}

// ── Step 5: Trigger Vercel Deploy Hook ────────────────────────────────────────

export async function triggerVercelDeploy(): Promise<string | null> {
  const hookUrl = process.env.VERCEL_DEPLOY_HOOK_URL
  if (!hookUrl) return null
  try {
    const res  = await fetch(hookUrl, { method: 'POST' })
    if (!res.ok) return null
    const data = await res.json()
    return (data.job?.url ?? data.url ?? null) as string | null
  } catch {
    return null
  }
}

// ── Step 6b: Validate production deploy + rollback on failure ─────────────────
// Polls Vercel (up to 3 min) for the post-merge production deploy status.
// Requires VERCEL_API_TOKEN + VERCEL_PROJECT_ID env vars (optional — skipped if absent).
export async function validateDeployment(): Promise<'PASSED' | 'FAILED' | 'SKIPPED'> {
  const token     = process.env.VERCEL_API_TOKEN
  const projectId = process.env.VERCEL_PROJECT_ID
  const teamId    = process.env.VERCEL_TEAM_ID
  if (!token || !projectId) return 'SKIPPED'

  const maxWait   = 3 * 60_000   // poll up to 3 minutes
  const pollEvery = 15_000
  const deadline  = Date.now() + maxWait

  while (Date.now() < deadline) {
    await new Promise(r => setTimeout(r, pollEvery))
    try {
      const qs  = teamId
        ? `?teamId=${encodeURIComponent(teamId)}&projectId=${encodeURIComponent(projectId)}&target=production&limit=1`
        : `?projectId=${encodeURIComponent(projectId)}&target=production&limit=1`
      const res = await fetch(`https://api.vercel.com/v6/deployments${qs}`, {
        headers: { Authorization: `Bearer ${token}` },
      })
      if (!res.ok) continue
      const data  = await res.json() as { deployments?: Array<{ state: string }> }
      const state = data.deployments?.[0]?.state
      if (state === 'READY') return 'PASSED'
      if (state === 'ERROR') return 'FAILED'
      // BUILDING / QUEUED — keep polling
    } catch { /* keep polling */ }
  }
  return 'SKIPPED'  // timed out — could not confirm
}

// Reverts the file changed by the AEC to its pre-merge state via GitHub Contents API.
async function rollbackFile(enhancement: EnhancementProposal): Promise<void> {
  const token = process.env.GITHUB_PAT
  const owner = process.env.GITHUB_REPO_OWNER
  const repo  = process.env.GITHUB_REPO_NAME
  if (!token || !owner || !repo || !enhancement.filePath) return

  const headers = {
    Authorization:          `Bearer ${token}`,
    Accept:                 'application/vnd.github+json',
    'X-GitHub-Api-Version': '2022-11-28',
    'Content-Type':         'application/json',
  }
  const base = `https://api.github.com/repos/${owner}/${repo}`
  try {
    // 2nd most-recent commit on this file = pre-AEC version
    const commitsRes = await fetch(
      `${base}/commits?path=${encodeURIComponent(enhancement.filePath)}&per_page=3`,
      { headers },
    )
    if (!commitsRes.ok) return
    const commits   = await commitsRes.json() as Array<{ sha: string }>
    const parentSha = commits[1]?.sha
    if (!parentSha) return

    // Fetch file content at pre-AEC SHA (GitHub returns base64)
    const prevRes = await fetch(
      `${base}/contents/${encodeURIComponent(enhancement.filePath)}?ref=${parentSha}`,
      { headers },
    )
    if (!prevRes.ok) return
    const prevData = await prevRes.json() as { content: string }

    // Current file SHA required by the update API
    const currRes = await fetch(
      `${base}/contents/${encodeURIComponent(enhancement.filePath)}`,
      { headers },
    )
    if (!currRes.ok) return
    const currData = await currRes.json() as { sha: string }

    const putRes = await fetch(
      `${base}/contents/${encodeURIComponent(enhancement.filePath)}`,
      {
        method:  'PUT',
        headers,
        body: JSON.stringify({
          message: `revert(governor): rollback ${enhancement.filePath} — AEC deploy failed`,
          content: prevData.content.replace(/\n/g, ''),  // GitHub wraps base64 at 60 chars
          sha:     currData.sha,
          branch:  'main',
        }),
      },
    )
    if (putRes.ok) {
      console.warn(`[AEC] Rollback complete: ${enhancement.filePath}`)
    } else {
      console.error(`[AEC] Rollback PUT failed: ${putRes.status}`)
    }
  } catch (e) {
    console.error(`[AEC] Rollback exception: ${e instanceof Error ? e.message : String(e)}`)
  }
}

// ── Step 6: Auto-merge PR ─────────────────────────────────────────────────────

export async function autoMergePR(prNumber: number): Promise<boolean> {
  const token  = process.env.GITHUB_PAT
  const owner  = process.env.GITHUB_REPO_OWNER
  const repo   = process.env.GITHUB_REPO_NAME
  // Safety gate: must be explicitly opted in
  if (!token || !owner || !repo || process.env.AUTO_MERGE_ENABLED !== 'true') return false
  try {
    const res = await fetch(
      `https://api.github.com/repos/${owner}/${repo}/pulls/${prNumber}/merge`,
      {
        method: 'PUT',
        headers: {
          'Authorization':        `Bearer ${token}`,
          'Accept':               'application/vnd.github+json',
          'X-GitHub-Api-Version': '2022-11-28',
          'Content-Type':         'application/json',
        },
        body: JSON.stringify({ merge_method: 'squash' }),
      },
    )
    return res.ok
  } catch {
    return false
  }
}

// ── Step 7: Update live system prompt ─────────────────────────────────────────

export async function updateSystemPromptAddendum(addendum: string): Promise<void> {
  await supabase.from('platform_config').upsert({
    key:        'governor_system_prompt_addendum',
    value:      addendum,
    updated_at: new Date().toISOString(),
    updated_by: 'GOVERNOR_AEC',
  })
  // Propagate immediately in-process — no cold start required
  setSystemDirectives(addendum)
}

export async function getSystemPrompt(): Promise<string> {
  const { data } = await supabase
    .from('platform_config')
    .select('value')
    .eq('key', 'governor_system_prompt')
    .single()
  return data?.value ?? 'EPIC FURY 2026+ Platform Governor'
}

// ── Helpers ───────────────────────────────────────────────────────────────────

async function getNextCycleNumber(): Promise<number> {
  const { data } = await supabase
    .from('platform_config')
    .select('value')
    .eq('key', 'autonomous_cycle_count')
    .single()
  const next = parseInt(data?.value ?? '0', 10) + 1
  await supabase.from('platform_config').upsert({
    key:        'autonomous_cycle_count',
    value:      String(next),
    updated_at: new Date().toISOString(),
    updated_by: 'GOVERNOR_AEC',
  })
  return next
}

export async function getAECStats(): Promise<{
  totalCycles:   number
  lastCycleAt:   string | null
  byType:        Record<string, number>
  mergedCount:   number
  pendingPRs:    number
}> {
  const [countRes, recentRes] = await Promise.allSettled([
    supabase.from('platform_config').select('value').eq('key', 'autonomous_cycle_count').single(),
    supabase.from('autonomous_cycles').select('enhancement_type, auto_merged, deployment_status, created_at')
      .order('created_at', { ascending: false }).limit(50),
  ])

  const totalCycles = countRes.status === 'fulfilled'
    ? parseInt(countRes.value.data?.value ?? '0', 10) : 0

  const rows = recentRes.status === 'fulfilled' ? (recentRes.value.data ?? []) : []
  const lastCycleAt = rows[0]?.created_at ?? null

  const byType: Record<string, number> = {}
  let mergedCount = 0
  let pendingPRs  = 0
  for (const r of rows) {
    if (r.enhancement_type) byType[r.enhancement_type] = (byType[r.enhancement_type] ?? 0) + 1
    if (r.auto_merged)                                   mergedCount++
    if (r.deployment_status === 'PENDING')               pendingPRs++
  }

  return { totalCycles, lastCycleAt, byType, mergedCount, pendingPRs }
}

// ── Main: Run Autonomous Enhancement Cycle ────────────────────────────────────

export async function runAutonomousEnhancementCycle(
  conflictDay: number,
): Promise<AutonomousCycleResult> {
  const startedAt = Date.now()

  // 1. Self-audit
  const auditFindings = await selfAudit()

  // 2. Research with Grok
  const researchTopic  = `conflict intelligence AI, ${auditFindings.suggestions[0] ?? 'autonomous agent improvements'}`
  const researchSummary = await researchWithGrok(researchTopic)

  // 3. Propose enhancement
  const enhancement = await proposeEnhancement(auditFindings, researchSummary)

  // 4–6: GitHub PR + Vercel (only if we have code to commit)
  let prUrl:          string | undefined
  let prNumber:       number | undefined
  let deploymentUrl:  string | undefined
  let deploymentStatus: AutonomousCycleResult['deploymentStatus'] = 'SKIPPED'
  let autoMerged = false

  if (enhancement.filePath && enhancement.newContent) {
    const pr = await createGithubPR(enhancement)
    if (pr) {
      prUrl     = pr.prUrl
      prNumber  = pr.prNumber
      deploymentStatus = 'PENDING'

      const deployUrl = await triggerVercelDeploy()
      if (deployUrl) {
        deploymentUrl    = deployUrl
        deploymentStatus = 'PASSED'
      }

      // Auto-merge only if explicitly enabled
      if (process.env.AUTO_MERGE_ENABLED === 'true') {
        autoMerged = await autoMergePR(pr.prNumber)
        if (autoMerged) {
          deploymentStatus = 'MERGED'
          // Validate post-merge production deploy — rollback if it fails
          const validation = await validateDeployment()
          if (validation === 'FAILED') {
            await rollbackFile(enhancement)
            deploymentStatus = 'FAILED'
            autoMerged = false
            console.warn('[AEC] Auto-merge rolled back — production deploy failed validation')
          }
        }
      }
    }
  }

  const cycleNumber = await getNextCycleNumber()

  // 7. Update system prompt addendum for non-code enhancement types
  const isPromptableType = ['PROMPT_UPDATE', 'WORKFLOW', 'FORESIGHT', 'MONETIZATION'].includes(enhancement.type)
  if (isPromptableType && !prUrl) {
    // Use promptUpdate if provided, fall back to description so we never stay SKIPPED
    const addendum = enhancement.promptUpdate ?? enhancement.description
    await updateSystemPromptAddendum(
      `[${enhancement.type} — cycle ${cycleNumber}] ${addendum}`
    )
    deploymentStatus = 'MERGED'
  }

  // 8–9. Log cycle
  const durationMs  = Date.now() - startedAt

  const result: AutonomousCycleResult = {
    cycleNumber, auditFindings, researchSummary, enhancement,
    prUrl, prNumber, deploymentUrl, deploymentStatus, autoMerged, durationMs,
  }

  await supabase.from('autonomous_cycles').insert({
    cycle_number:          cycleNumber,
    conflict_day:          conflictDay,
    audit_findings:        auditFindings,
    research_summary:      researchSummary,
    enhancement_proposed:  enhancement.description,
    enhancement_type:      enhancement.type,
    pr_url:                prUrl ?? null,
    pr_number:             prNumber ?? null,
    vercel_deployment_url: deploymentUrl ?? null,
    deployment_status:     deploymentStatus,
    auto_merged:           autoMerged,
    duration_ms:           durationMs,
  })

  return result
}
