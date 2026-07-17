import { redirect } from 'next/navigation'
import { cookies } from 'next/headers'
import { createServerClient } from '@supabase/ssr'
import WorkflowPanel from '@/components/WorkflowPanel'

async function requireAdmin() {
  const cookieStore = await cookies()
  const supabase = createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    { cookies: { getAll: () => cookieStore.getAll(), setAll: () => {} } }
  )
  const { data: { user } } = await supabase.auth.getUser()
  const isAdmin = (user?.app_metadata?.role as string) === 'admin' || user?.email === process.env.ADMIN_EMAIL
  if (!isAdmin) redirect('/dashboard')
}

export const metadata = {
  title: 'Workflow Engine — EPIC FURY 2026',
  description: 'Temporal-inspired durable workflow audit log: priority queues, versioning, Nexus',
}

export default async function WorkflowsPage() {
  await requireAdmin()
  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="border-b border-gray-800 pb-4">
        <h1 className="text-xl font-bold font-mono text-cyan-400 tracking-wider">
          ⚡ WORKFLOW ENGINE
        </h1>
        <p className="text-sm text-gray-500 mt-1 font-mono">
          Temporal.io-inspired durable execution — priority queues · worker versioning · Nexus composition · event history
        </p>
      </div>

      {/* Full workflow panel */}
      <WorkflowPanel />
    </div>
  )
}
