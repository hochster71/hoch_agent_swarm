'use client'

import { useRef, useState } from 'react'
import { Radio } from 'lucide-react'

export interface TickerItem {
  id: string
  label: string   // Short category/source: "CENTCOM" | "BREAKING" | "REUTERS" etc.
  text: string
  urgent?: boolean
}

/** Breaking news scrolling ticker bar */
export function NewsTicker({ items }: { items: TickerItem[] }) {
  const trackRef = useRef<HTMLDivElement>(null)
  const [paused, setPaused] = useState(false)

  // Duplicate items so the loop appears seamless
  const doubled = [...items, ...items]

  return (
    <div
      className="relative flex items-center gap-0 overflow-hidden border border-zinc-800 bg-black/60 rounded-sm h-7 select-none"
      onMouseEnter={() => setPaused(true)}
      onMouseLeave={() => setPaused(false)}
      aria-live="polite"
      aria-label="Breaking news ticker"
    >
      {/* Static "BREAKING" pill */}
      <div className="shrink-0 flex items-center gap-1.5 px-3 h-full border-r border-zinc-800 bg-red-950/60 z-10">
        <Radio size={9} className="text-red-400 animate-pulse" />
        <span className="text-[9px] font-bold tracking-widest text-red-400 uppercase whitespace-nowrap">
          BREAKING
        </span>
      </div>

      {/* Scrolling track */}
      <div className="flex-1 overflow-hidden">
        <div
          ref={trackRef}
          className="flex gap-0 whitespace-nowrap"
          style={{
            animation: paused ? 'none' : 'ticker-scroll 60s linear infinite',
          }}
        >
          {doubled.map((item, idx) => (
            <span key={`${item.id}-${idx}`} className="inline-flex items-center gap-2 px-6">
              <span
                className={
                  item.urgent
                    ? 'text-[9px] font-bold tracking-widest text-red-400 uppercase'
                    : 'text-[9px] font-bold tracking-widest text-amber-500/80 uppercase'
                }
              >
                {item.label}
              </span>
              <span className="text-[10px] text-zinc-400">
                {item.text}
              </span>
              <span className="text-zinc-700 mx-2">◆</span>
            </span>
          ))}
        </div>
      </div>
    </div>
  )
}
