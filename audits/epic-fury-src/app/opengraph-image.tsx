import { ImageResponse } from 'next/og'

export const size        = { width: 1200, height: 630 }
export const contentType = 'image/png'
export const alt         = 'Epic Fury — Live US-Iran War Intelligence Dashboard'

export default function OgImage() {

  return new ImageResponse(
    (
      <div
        style={{
          width: 1200,
          height: 630,
          background: '#09090b',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'flex-start',
          justifyContent: 'flex-end',
          padding: 64,
          fontFamily: 'monospace',
          position: 'relative',
        }}
      >
        {/* Scanline grid overlay */}
        <div
          style={{
            position: 'absolute',
            inset: 0,
            background:
              'repeating-linear-gradient(0deg, transparent, transparent 3px, rgba(0,0,0,0.08) 3px, rgba(0,0,0,0.08) 4px)',
            pointerEvents: 'none',
          }}
        />

        {/* Green border glow */}
        <div
          style={{
            position: 'absolute',
            inset: 0,
            border: '1px solid #166534',
            boxShadow: 'inset 0 0 80px rgba(22,101,52,0.15)',
          }}
        />

        {/* Top-right: LIVE badge */}
        <div
          style={{
            position: 'absolute',
            top: 40,
            right: 48,
            display: 'flex',
            alignItems: 'center',
            gap: 8,
            border: '1px solid #dc2626',
            borderRadius: 4,
            padding: '6px 14px',
            background: 'rgba(220,38,38,0.08)',
          }}
        >
          <div
            style={{
              width: 8,
              height: 8,
              borderRadius: '50%',
              background: '#ef4444',
            }}
          />
          <span style={{ color: '#fca5a5', fontSize: 13, letterSpacing: 4, fontWeight: 700 }}>
            MODEL
          </span>
        </div>

        {/* Conflict day */}
        <div
          style={{
            color: '#52525b',
            fontSize: 13,
            letterSpacing: 5,
            textTransform: 'uppercase',
            marginBottom: 16,
          }}
        >
          {'CONFLICT MODELING TOOL // PROJECTIONS, NOT LIVE REPORTING'}
        </div>

        {/* Main title */}
        <div
          style={{
            color: '#4ade80',
            fontSize: 64,
            fontWeight: 900,
            letterSpacing: 8,
            textTransform: 'uppercase',
            lineHeight: 1,
            textShadow: '0 0 40px rgba(74,222,128,0.4)',
            marginBottom: 24,
          }}
        >
          EPIC FURY
        </div>

        {/* Subtitle */}
        <div
          style={{
            color: '#a1a1aa',
            fontSize: 22,
            letterSpacing: 3,
            textTransform: 'uppercase',
            marginBottom: 40,
          }}
        >
          CONFLICT MODELING TOOL — NOT LIVE REPORTING
        </div>

        {/* Stat pills */}
        <div style={{ display: 'flex', gap: 16 }}>
          {[
            
            { label: 'Ceasefire 72h',    value: '68%',    color: '#38bdf8', bg: 'rgba(56,189,248,0.08)', border: '#075985' },
            { label: 'Brent Crude',      value: '$109',   color: '#fb923c', bg: 'rgba(251,146,60,0.08)', border: '#9a3412' },
            { label: 'Threat Level',     value: 'SEVERE', color: '#f87171', bg: 'rgba(248,113,113,0.08)', border: '#7f1d1d' },
          ].map((s) => (
            <div
              key={s.label}
              style={{
                display: 'flex',
                flexDirection: 'column',
                gap: 4,
                border: `1px solid ${s.border}`,
                borderRadius: 6,
                padding: '10px 18px',
                background: s.bg,
              }}
            >
              <span style={{ color: '#71717a', fontSize: 11, letterSpacing: 3, textTransform: 'uppercase' }}>
                {s.label}
              </span>
              <span style={{ color: s.color, fontSize: 20, fontWeight: 800, letterSpacing: 2 }}>
                {s.value}
              </span>
            </div>
          ))}
        </div>

        {/* Bottom right: URL */}
        <div
          style={{
            position: 'absolute',
            bottom: 40,
            right: 48,
            color: '#27272a',
            fontSize: 14,
            letterSpacing: 2,
          }}
        >
          epicfury.app
        </div>
      </div>
    ),
    { ...size },
  )
}
