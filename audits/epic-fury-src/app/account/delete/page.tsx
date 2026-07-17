'use client'

/**
 * /account/delete — In-app account deletion
 *
 * Apple App Store Guidelines §5.1.1: apps supporting account creation must
 * allow users to initiate deletion within the app. Accessible to all
 * authenticated users (not admin-only). Unauthenticated users sent to /login.
 *
 * Flow: confirm warnings → type "DELETE MY ACCOUNT" → DELETE /api/account/delete
 * → server schedules deletion 30 days out, signs user out immediately.
 * Source: developer.apple.com/app-store/review/guidelines/ §5.1.1
 */

import { useState }            from 'react'
import { useRouter }           from 'next/navigation'
import { createBrowserClient } from '@/lib/supabase'

export default function DeleteAccountPage() {
  const router = useRouter()
  const [step, setStep]       = useState<'confirm'|'typing'|'deleting'|'done'|'error'>('confirm')
  const [input, setInput]     = useState('')
  const [message, setMessage] = useState('')
  const PHRASE = 'DELETE MY ACCOUNT'

  async function handleDelete() {
    setStep('deleting')
    try {
      const supabase = createBrowserClient()
      const { data: { session } } = await supabase.auth.getSession()
      if (!session) { router.push('/login?next=/account/delete'); return }
      const res  = await fetch('/api/account/delete', { method: 'DELETE', credentials: 'include' })
      const data = await res.json()
      if (!res.ok) { setMessage(data.error ?? 'Something went wrong.'); setStep('error'); return }
      setMessage(data.note ?? 'Account scheduled for deletion within 30 days.')
      setStep('done')
      setTimeout(() => router.push('/'), 4000)
    } catch {
      setMessage('Network error. Check your connection and try again.')
      setStep('error')
    }
  }

  return (
    <main className="min-h-screen bg-black flex items-center justify-center p-4">
      <div className="w-full max-w-md border border-red-900/60 rounded-2xl overflow-hidden bg-zinc-950">

        <div className="bg-red-950/40 border-b border-red-900/40 px-6 py-5 text-center">
          <div className="text-2xl mb-1">⚠</div>
          <h1 className="text-white font-bold text-lg tracking-tight font-mono">Delete Account</h1>
          <p className="text-zinc-400 text-sm mt-1">Epic Fury — Permanent action</p>
        </div>

        <div className="px-6 py-6 space-y-5">

          {step === 'confirm' && (<>
            <div className="space-y-3 text-sm text-zinc-300">
              <p>Deleting your account will:</p>
              <ul className="space-y-1 pl-4">
                {[
                  'Cancel any active subscriptions',
                  'Remove all your saved data and preferences',
                  'Permanently delete your account within 30 days',
                  'Sign you out immediately',
                ].map(item => (
                  <li key={item} className="flex gap-2">
                    <span className="text-red-400 mt-0.5 shrink-0">✕</span>
                    <span>{item}</span>
                  </li>
                ))}
              </ul>
              <p className="text-zinc-500 text-xs pt-1">
                To cancel a subscription first, go to{' '}
                <strong className="text-zinc-400">iOS Settings → Apple ID → Subscriptions</strong>.
              </p>
            </div>
            <button onClick={() => setStep('typing')}
              className="w-full border border-red-700 bg-transparent hover:bg-red-950/40 text-red-400 font-mono font-bold py-3 rounded-xl transition-colors text-sm">
              Continue with deletion →
            </button>
            <button onClick={() => router.back()}
              className="w-full text-zinc-600 hover:text-zinc-400 text-xs py-2 transition-colors">
              Cancel — keep my account
            </button>
          </>)}

          {step === 'typing' && (<>
            <div className="text-sm text-zinc-300 space-y-3">
              <p>Type the following to confirm:</p>
              <code className="block bg-zinc-900 border border-zinc-700 rounded-lg px-3 py-2 text-red-300 font-mono text-sm tracking-widest">
                {PHRASE}
              </code>
            </div>
            <input type="text" value={input}
              onChange={e => setInput(e.target.value.toUpperCase())}
              placeholder="Type confirmation phrase"
              className="w-full bg-zinc-900 border border-zinc-700 focus:border-red-600 rounded-xl px-4 py-3 text-white font-mono text-sm outline-none transition-colors placeholder:text-zinc-600"
              autoComplete="off" autoFocus />
            <button onClick={handleDelete} disabled={input !== PHRASE}
              className="w-full bg-red-700 hover:bg-red-600 disabled:opacity-30 disabled:cursor-not-allowed text-white font-bold py-3 rounded-xl transition-colors font-mono text-sm tracking-wide">
              Permanently delete my account
            </button>
            <button onClick={() => { setStep('confirm'); setInput('') }}
              className="w-full text-zinc-600 hover:text-zinc-400 text-xs py-2 transition-colors">
              Cancel — keep my account
            </button>
          </>)}

          {step === 'deleting' && (
            <div className="text-center py-8">
              <div className="text-zinc-400 font-mono text-sm animate-pulse">Scheduling deletion…</div>
            </div>
          )}

          {step === 'done' && (
            <div className="text-center py-4 space-y-4">
              <div className="text-3xl">✓</div>
              <p className="text-green-400 font-mono text-sm font-bold">Account scheduled for deletion</p>
              <p className="text-zinc-400 text-sm">{message}</p>
              <p className="text-zinc-600 text-xs">Redirecting to home…</p>
            </div>
          )}

          {step === 'error' && (
            <div className="text-center py-4 space-y-4">
              <div className="text-3xl">⚠</div>
              <p className="text-red-400 font-mono text-sm font-bold">Error</p>
              <p className="text-zinc-400 text-sm">{message}</p>
              <button onClick={() => setStep('confirm')}
                className="w-full border border-zinc-700 text-zinc-400 hover:text-white py-2 rounded-xl text-sm transition-colors">
                Try again
              </button>
            </div>
          )}
        </div>

        <div className="px-6 pb-5 text-center">
          <a href="/privacy" className="text-zinc-600 hover:text-zinc-400 text-xs transition-colors">
            Privacy Policy
          </a>
        </div>
      </div>
    </main>
  )
}
