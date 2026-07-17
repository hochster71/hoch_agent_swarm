import { redirect } from 'next/navigation'
import { cookies } from 'next/headers'
import { createServerClient } from '@supabase/ssr'
import AutonomousPanel from '@/components/AutonomousPanel'

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
  title: 'Autonomous Enhancement — EPIC FURY 2026+',
}

export default async function AutonomousPage() {
  await requireAdmin()
  return (
    <div className="p-6 max-w-5xl mx-auto">
      <AutonomousPanel />
    </div>
  )
}
