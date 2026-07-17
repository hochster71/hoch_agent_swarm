'use client'

import { useState } from 'react'
import { Share2, Check, Copy, Twitter, Link2 } from 'lucide-react'

interface ShareButtonProps {
  title?: string
  text?: string
  /** Override the URL — defaults to current page URL */
  url?: string
  className?: string
}

/**
 * ShareButton — copy-to-clipboard + native Web Share API + Twitter quick-share.
 * Designed for public-facing intelligence pages so US citizens can easily
 * share the dashboard with friends and family.
 */
export function ShareButton({ title, text, url, className = '' }: ShareButtonProps) {
  const [state, setState] = useState<'idle' | 'open' | 'copied'>('idle')
  const [dropdownCopied, setDropdownCopied] = useState(false)

  const getUrl = () => (typeof window !== 'undefined' ? url ?? window.location.href : url ?? '')

  const copyLink = async () => {
    try {
      await navigator.clipboard.writeText(getUrl())
    } catch {
      const inp = document.createElement('input')
      inp.value = getUrl()
      document.body.appendChild(inp)
      inp.select()
      document.execCommand('copy')
      document.body.removeChild(inp)
    }
    // Both in dropdown and standalone modes
    if (state === 'open') {
      setDropdownCopied(true)
      setTimeout(() => { setDropdownCopied(false); setState('idle') }, 2000)
    } else {
      setState('copied')
      setTimeout(() => setState('idle'), 2000)
    }
  }

  const nativeShare = async () => {
    if (typeof navigator !== 'undefined' && navigator.share) {
      try {
        await navigator.share({
          title: title ?? 'Epic Fury War Dashboard',
          text: text ?? 'Live OSINT tracking of the 2026 US–Iran conflict — Operation Epic Fury',
          url: getUrl(),
        })
      } catch { /* user dismissed */ }
    } else {
      setState(s => s === 'open' ? 'idle' : 'open')
    }
  }

  const twitterShare = () => {
    const t = encodeURIComponent((text ?? 'Live OSINT — 2026 US–Iran War Dashboard') + ' ' + getUrl())
    window.open(`https://twitter.com/intent/tweet?text=${t}`, '_blank', 'noopener,noreferrer')
  }

  return (
    <div className={`relative inline-flex ${className}`}>
      <button
        onClick={nativeShare}
        className="flex items-center gap-1.5 px-3 py-1.5 rounded border border-zinc-700 bg-zinc-900/60 hover:border-emerald-700 hover:bg-zinc-800 text-zinc-400 hover:text-emerald-400 text-[10px] tracking-widest uppercase transition-all"
        title="Share this page"
        aria-label="Share"
      >
        <Share2 size={11} />
        Share
      </button>

      {/* Dropdown for non-native-share environments */}
      {state === 'open' && (
        <div className="absolute right-0 top-full mt-1 z-50 w-44 rounded border border-zinc-700 bg-zinc-900 shadow-xl shadow-black/60 py-1">
          <button
            onClick={copyLink}
            className="flex w-full items-center gap-2 px-3 py-2 text-[10px] tracking-widest uppercase text-zinc-400 hover:text-emerald-400 hover:bg-zinc-800 transition-colors"
          >
            {dropdownCopied ? <Check size={11} className="text-emerald-400" /> : <Copy size={11} />}
            {dropdownCopied ? 'Copied!' : 'Copy Link'}
          </button>
          <button
            onClick={twitterShare}
            className="flex w-full items-center gap-2 px-3 py-2 text-[10px] tracking-widest uppercase text-zinc-400 hover:text-sky-400 hover:bg-zinc-800 transition-colors"
          >
            <Twitter size={11} />
            Tweet This
          </button>
        </div>
      )}

      {/* Inline copied confirmation (for native share environments) */}
      {state === 'copied' && (
        <span className="absolute -top-6 right-0 flex items-center gap-1 text-[10px] text-emerald-400 whitespace-nowrap">
          <Check size={10} /> Link copied!
        </span>
      )}
    </div>
  )
}

/**
 * Inline copy-link-only variant for use inside text paragraphs.
 */
export function CopyLinkButton({ url, className = '' }: { url?: string; className?: string }) {
  const [copied, setCopied] = useState(false)
  const getUrl = () => (typeof window !== 'undefined' ? url ?? window.location.href : url ?? '')

  const copy = async () => {
    try { await navigator.clipboard.writeText(getUrl()) } catch { /* fallback */ }
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <button
      onClick={copy}
      className={`inline-flex items-center gap-1 text-zinc-600 hover:text-emerald-400 transition-colors ${className}`}
      title="Copy page link"
    >
      {copied ? <Check size={11} className="text-emerald-400" /> : <Link2 size={11} />}
      <span className="text-[10px] tracking-widest uppercase">{copied ? 'Copied' : 'Link'}</span>
    </button>
  )
}
