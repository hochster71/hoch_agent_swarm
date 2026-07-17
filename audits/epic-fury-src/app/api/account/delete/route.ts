/**
 * DELETE /api/account/delete
 *
 * Schedules the authenticated user's account for deletion within 30 days,
 * matching the privacy policy at /privacy. Signs out immediately.
 *
 * Apple App Store Guidelines §5.1.1: initiation must be available within app.
 * Source: developer.apple.com/app-store/review/guidelines/
 */
import { NextResponse }       from 'next/server'
import { cookies }            from 'next/headers'
import { createServerClient } from '@supabase/ssr'

export async function DELETE() {
  const cookieStore = await cookies()
  const supabase = createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    {
      cookies: {
        getAll: ()  => cookieStore.getAll(),
        setAll: (cookiesToSet: { name: string; value: string; options?: Record<string, unknown> }[]) =>
          cookiesToSet.forEach(({ name, value, options }) => cookieStore.set(name, value, options as never)),
      },
    }
  )

  const { data: { user }, error } = await supabase.auth.getUser()
  if (error || !user) return NextResponse.json({ error: 'Not authenticated' }, { status: 401 })

  // Return early if a pending request already exists
  const { data: existing } = await supabase
    .from('deletion_requests')
    .select('id, scheduled_for')
    .eq('user_id', user.id)
    .eq('status', 'pending')
    .maybeSingle()

  if (existing) {
    return NextResponse.json({
      message: 'Deletion already scheduled',
      scheduled_for: existing.scheduled_for,
    })
  }

  const scheduledFor = new Date(Date.now() + 30 * 24 * 60 * 60 * 1000).toISOString()

  const { error: insertErr } = await supabase
    .from('deletion_requests')
    .insert({
      user_id:       user.id,
      user_email:    user.email,
      requested_at:  new Date().toISOString(),
      scheduled_for: scheduledFor,
      status:        'pending',
    })

  if (insertErr) {
    console.error('[account/delete]', insertErr)
    return NextResponse.json({ error: 'Failed to schedule deletion. Please try again.' }, { status: 500 })
  }

  await supabase.auth.signOut()

  return NextResponse.json({
    message: 'Account scheduled for deletion',
    scheduled_for: scheduledFor,
    note: 'Your account and all associated data will be permanently deleted within 30 days.',
  })
}
