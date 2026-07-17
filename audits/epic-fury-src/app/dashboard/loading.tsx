export default function DashboardLoading() {
  return (
    <div className="flex flex-col items-center justify-center min-h-[60vh] gap-6 animate-in fade-in duration-300">
      {/* Radar sweep spinner */}
      <div className="relative w-20 h-20">
        {/* Outer ring */}
        <div className="absolute inset-0 rounded-full border border-emerald-800/40" />
        {/* Middle ring */}
        <div className="absolute inset-2 rounded-full border border-emerald-700/30" />
        {/* Inner ring */}
        <div className="absolute inset-4 rounded-full border border-emerald-600/20" />
        {/* Center dot */}
        <div className="absolute inset-[34px] rounded-full bg-emerald-400 shadow-lg shadow-emerald-400/50" />
        {/* Sweep beam */}
        <div
          className="absolute inset-0 rounded-full"
          style={{
            background: 'conic-gradient(from 0deg, transparent 0deg, transparent 330deg, rgba(16,185,129,0.4) 350deg, rgba(16,185,129,0.15) 360deg)',
            animation: 'radar-sweep 2s linear infinite',
          }}
        />
      </div>

      {/* Loading text */}
      <div className="flex flex-col items-center gap-1.5">
        <p className="text-xs font-bold tracking-[0.3em] text-emerald-400 uppercase glow-green">
          Loading Intel
        </p>
        <div className="flex items-center gap-1">
          {[0, 1, 2].map((i) => (
            <span
              key={i}
              className="w-1.5 h-1.5 rounded-full bg-emerald-400"
              style={{
                animation: 'loading-dot 1.2s ease-in-out infinite',
                animationDelay: `${i * 0.2}s`,
              }}
            />
          ))}
        </div>
      </div>

      {/* Inline keyframes */}
      <style>{`
        @keyframes radar-sweep {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }
        @keyframes loading-dot {
          0%, 80%, 100% { opacity: 0.2; transform: scale(0.8); }
          40% { opacity: 1; transform: scale(1.2); }
        }
      `}</style>
    </div>
  )
}
