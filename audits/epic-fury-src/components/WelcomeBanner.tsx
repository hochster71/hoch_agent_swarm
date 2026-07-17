'use client'

import { useState, useEffect } from 'react'
import { X, ShieldAlert, Radio, Info } from 'lucide-react'

/**
 * WelcomeBanner — shown once to first-time visitors, dismissed to localStorage.
 * Explains what the dashboard is and sets expectations for US citizens.
 */
export function WelcomeBanner() {
  const [visible, setVisible] = useState(false)

  useEffect(() => {
    // Only show if not already dismissed
    const dismissed = localStorage.getItem('ef-welcome-dismissed-v2')
    if (!dismissed) setVisible(true)
  }, [])

  const dismiss = () => {
    localStorage.setItem('ef-welcome-dismissed-v2', '1')
    setVisible(false)
  }

  if (!visible) return null

  return (
    <div
      role="dialog"
      aria-label="Welcome to Epic Fury War Dashboard"
      className="fixed inset-0 z-[100] flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm"
    >
      <div className="relative w-full max-w-lg rounded-xl border border-emerald-800/50 bg-zinc-950/95 backdrop-blur-xl shadow-2xl shadow-emerald-950/50 p-6 space-y-4">
        {/* Close */}
        <button
          onClick={dismiss}
          className="absolute top-3 right-3 flex items-center justify-center w-10 h-10 rounded-lg text-zinc-600 hover:text-zinc-300 hover:bg-zinc-800/50 active:scale-95 transition-all"
          aria-label="Close welcome message"
        >
          <X size={18} />
        </button>

        {/* Header */}
        <div className="flex items-center gap-2 border-b border-emerald-900/50 pb-3">
          <ShieldAlert size={14} className="text-amber-400" />
          <p className="text-[10px] font-bold tracking-[0.3em] text-amber-400 uppercase">
            Welcome — What This Is
          </p>
        </div>

        {/* Body */}
        <div className="space-y-3">
          <p className="text-sm text-zinc-300 leading-relaxed">
            You&apos;ve entered the <strong className="text-emerald-300">Epic Fury War Dashboard</strong> — 
            an open-source intelligence aggregation platform tracking the 2026 US–Iran conflict in real time, 
            built for American citizens.
          </p>

          <div className="rounded border border-red-900/50 bg-red-950/30 p-3">
            <p className="text-[10px] font-bold text-red-400 tracking-widest uppercase mb-1">⚠ Important Notice</p>
            <p className="text-xs text-red-300/80 leading-relaxed">
              This is an <strong>unclassified, open-source analysis tool</strong>. 
              It does not contain real government intelligence. 
              All data is derived from public sources: wire services, official statements, 
              think tanks, and OSINT. Treat all analysis as civilian context, not official DoD assessment.
            </p>
          </div>

          <div className="grid grid-cols-2 gap-2 text-[11px]">
            <div className="flex items-start gap-2 rounded border border-zinc-800 p-2">
              <Radio size={11} className="text-emerald-400 mt-0.5 shrink-0" />
              <span className="text-zinc-400 leading-snug">Live intel feed updated every 60 seconds from open sources</span>
            </div>
            <div className="flex items-start gap-2 rounded border border-zinc-800 p-2">
              <Info size={11} className="text-sky-400 mt-0.5 shrink-0" />
              <span className="text-zinc-400 leading-snug">AI Newsroom with 9 diverse anchors reads the daily briefing aloud</span>
            </div>
          </div>

          <p className="text-[11px] text-zinc-500 leading-relaxed">
            For official information visit&nbsp;
            <a href="https://www.centcom.mil" target="_blank" rel="noopener noreferrer" className="text-emerald-400 hover:underline">centcom.mil</a>,&nbsp;
            <a href="https://www.defense.gov" target="_blank" rel="noopener noreferrer" className="text-emerald-400 hover:underline">defense.gov</a>, or&nbsp;
            <a href="https://www.cisa.gov" target="_blank" rel="noopener noreferrer" className="text-emerald-400 hover:underline">cisa.gov</a>.
          </p>
        </div>

        {/* CTA */}
        <button
          onClick={dismiss}
          className="w-full rounded-lg bg-emerald-800 hover:bg-emerald-700 text-emerald-100 font-bold text-xs tracking-widest uppercase min-h-[48px] py-3 active:scale-[0.98] transition-all shadow-lg shadow-emerald-900/30"
        >
          I Understand — Enter Command Center
        </button>
      </div>
    </div>
  )
}
