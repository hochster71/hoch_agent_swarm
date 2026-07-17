'use client'

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string }
  reset: () => void
}) {
  return (
    <html lang="en" className="dark">
      <body className="min-h-screen bg-zinc-950 text-emerald-300 font-mono flex items-center justify-center p-8">
        <div className="max-w-xl w-full border border-red-900 bg-red-950/10 p-6 space-y-4">
          <p className="text-[9px] tracking-[0.3em] text-red-400 uppercase">System Error — Operation Epic Fury</p>
          <h1 className="text-lg font-bold text-red-400 tracking-widest">RENDER FAULT</h1>
          <pre className="text-[10px] text-zinc-400 whitespace-pre-wrap break-all bg-zinc-900 p-3">
            {process.env.NODE_ENV === 'development' ? (error.message || 'Unknown error') : 'An unexpected error occurred. Please retry.'}
          </pre>
          {error.digest && (
            <p className="text-[9px] text-zinc-600">Digest: {error.digest}</p>
          )}
          <button
            onClick={reset}
            className="text-[10px] tracking-[0.2em] uppercase border border-emerald-900 text-emerald-500 px-4 py-2 hover:border-emerald-600 transition-colors"
          >
            ↺ Retry
          </button>
        </div>
      </body>
    </html>
  )
}
