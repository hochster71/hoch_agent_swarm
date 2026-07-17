'use client'

import { useState } from 'react'

type Props = {
  text: string
  voiceId?: string
}

export function TtsPlayer({ text, voiceId = '21m00Tcm4TlvDq8ikWAM' }: Props) {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function play() {
    if (!text.trim()) return
    setLoading(true)
    setError(null)

    try {
      const response = await fetch('/api/tts', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text, voiceId }),
      })

      if (!response.ok) {
        throw new Error(`TTS failed (${response.status})`)
      }

      const audioBuffer = await response.arrayBuffer()
      const blob = new Blob([audioBuffer], { type: 'audio/mpeg' })
      const url = URL.createObjectURL(blob)
      const audio = new Audio(url)
      audio.onended = () => URL.revokeObjectURL(url)
      await audio.play()
    } catch {
      setError('Audio unavailable')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="inline-flex items-center gap-2">
      <button
        type="button"
        onClick={play}
        disabled={loading}
        className="px-3 py-1 rounded border border-zinc-700 text-xs text-zinc-300 hover:border-emerald-700 hover:text-emerald-300 disabled:opacity-50"
      >
        {loading ? 'Generating audio...' : 'Play SITREP Audio'}
      </button>
      {error ? <span className="text-[11px] text-amber-400">{error}</span> : null}
    </div>
  )
}
