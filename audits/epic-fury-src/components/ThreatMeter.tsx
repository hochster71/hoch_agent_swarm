'use client'

export type ThreatLevel = 'LOW' | 'GUARDED' | 'ELEVATED' | 'HIGH' | 'SEVERE'

interface ThreatMeterProps {
  level?: ThreatLevel
  showLabel?: boolean
  size?: 'sm' | 'md' | 'lg'
  className?: string
}

interface LevelConfig {
  code: ThreatLevel
  label: string
  description: string
  textColor: string
  bgActive: string
  ring: string
  value: number
}

const LEVELS: LevelConfig[] = [
  {
    code: 'LOW',
    label: 'LOW',
    description: 'No specific threat identified',
    textColor: 'text-emerald-400',
    bgActive: 'bg-emerald-500',
    ring: 'ring-emerald-400',
    value: 1,
  },
  {
    code: 'GUARDED',
    label: 'GUARDED',
    description: 'General threat — increased vigilance',
    textColor: 'text-blue-400',
    bgActive: 'bg-blue-500',
    ring: 'ring-blue-400',
    value: 2,
  },
  {
    code: 'ELEVATED',
    label: 'ELEVATED',
    description: 'Significant threat — heightened posture',
    textColor: 'text-yellow-400',
    bgActive: 'bg-yellow-500',
    ring: 'ring-yellow-400',
    value: 3,
  },
  {
    code: 'HIGH',
    label: 'HIGH',
    description: 'High risk — active operations ongoing',
    textColor: 'text-orange-400',
    bgActive: 'bg-orange-500',
    ring: 'ring-orange-400',
    value: 4,
  },
  {
    code: 'SEVERE',
    label: 'SEVERE',
    description: 'Imminent / ongoing major attack',
    textColor: 'text-red-400',
    bgActive: 'bg-red-500',
    ring: 'ring-red-400',
    value: 5,
  },
]

export function ThreatMeter({
  level = 'HIGH',
  showLabel = true,
  size = 'md',
  className = '',
}: ThreatMeterProps) {
  const current = LEVELS.find((l) => l.code === level) ?? LEVELS[3]
  const isPulsing = level === 'HIGH' || level === 'SEVERE'

  const barH = size === 'sm' ? 'h-1.5' : size === 'lg' ? 'h-4' : 'h-2.5'
  const barW = size === 'sm' ? 'w-5' : size === 'lg' ? 'w-10' : 'w-7'

  return (
    <div className={`flex flex-col gap-1.5 ${className}`}>
      {showLabel && (
        <div className="flex items-center justify-between gap-2">
          <span className="text-[9px] tracking-[0.2em] text-zinc-500 uppercase">
            Threat Level
          </span>
          <span
            className={`text-xs font-bold tracking-widest uppercase ${current.textColor} ${
              isPulsing ? 'animate-pulse' : ''
            }`}
          >
            ► {current.label}
          </span>
        </div>
      )}

      <div className="flex items-center gap-1">
        {LEVELS.map((l) => (
          <div
            key={l.code}
            title={`${l.label}: ${l.description}`}
            className={[
              barH,
              barW,
              'rounded-sm transition-all duration-500',
              l.value <= current.value ? l.bgActive : 'bg-zinc-800',
              l.value === current.value
                ? `ring-1 ${l.ring} ring-offset-1 ring-offset-zinc-950`
                : '',
            ]
              .filter(Boolean)
              .join(' ')}
          />
        ))}
      </div>

      {size === 'lg' && (
        <p className="text-[10px] text-zinc-500 tracking-wide">
          {current.description}
        </p>
      )}
    </div>
  )
}

/** Compact inline badge for use in narrow spaces (e.g. TopBar) */
export function ThreatBadge({ level = 'HIGH' }: { level?: ThreatLevel }) {
  const current = LEVELS.find((l) => l.code === level) ?? LEVELS[3]
  const isPulsing = level === 'HIGH' || level === 'SEVERE'

  const badgeBg: Record<ThreatLevel, string> = {
    LOW:      'bg-emerald-950/80 text-emerald-400 border-emerald-700/50',
    GUARDED:  'bg-blue-950/80    text-blue-400    border-blue-700/50',
    ELEVATED: 'bg-yellow-950/80  text-yellow-400  border-yellow-700/50',
    HIGH:     'bg-orange-950/80  text-orange-400  border-orange-700/50',
    SEVERE:   'bg-red-950/80     text-red-400     border-red-700/50',
  }

  const dotColor: Record<ThreatLevel, string> = {
    LOW:      'bg-emerald-400',
    GUARDED:  'bg-blue-400',
    ELEVATED: 'bg-yellow-400',
    HIGH:     'bg-orange-400',
    SEVERE:   'bg-red-500',
  }

  return (
    <span
      className={`inline-flex items-center gap-1.5 px-2.5 py-1 text-[9px] font-bold tracking-widest border rounded-lg backdrop-blur-sm uppercase ${
        badgeBg[level]
      }`}
    >
      <span className={`w-1.5 h-1.5 rounded-full shrink-0 ${dotColor[level]} ${isPulsing ? 'animate-pulse' : ''}`} />
      {current.label}
    </span>
  )
}
