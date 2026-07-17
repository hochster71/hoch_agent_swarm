import Link from 'next/link'

export const metadata = {
  title: '404 — Route Not Found | Epic Fury',
}

export default function NotFound() {
  return (
    <html lang="en" className="dark">
      <body className="min-h-screen bg-zinc-950 text-emerald-300 font-mono flex items-center justify-center p-8">
        <div className="max-w-xl w-full border border-zinc-800 bg-zinc-900/60 p-8 space-y-6">
          <div className="space-y-1">
            <p className="text-[9px] tracking-[0.3em] text-zinc-500 uppercase">Operation Epic Fury — NEXUS Navigation</p>
            <h1 className="text-2xl font-bold text-red-400 tracking-widest">404 — ROUTE NOT FOUND</h1>
          </div>
          <p className="text-[11px] text-zinc-400 leading-relaxed">
            The requested path does not exist in the NEXUS routing table.
            This asset may have been decommissioned or the URL may be incorrect.
          </p>
          <div className="border-t border-zinc-800 pt-4 flex gap-4">
            <Link
              href="/dashboard"
              className="text-[10px] tracking-[0.2em] uppercase border border-emerald-900 text-emerald-500 px-4 py-2 hover:border-emerald-600 transition-colors"
            >
              ↩ Return to Hub
            </Link>
            <Link
              href="/dashboard/feed"
              className="text-[10px] tracking-[0.2em] uppercase border border-zinc-700 text-zinc-400 px-4 py-2 hover:border-zinc-500 transition-colors"
            >
              Live Feed
            </Link>
          </div>
        </div>
      </body>
    </html>
  )
}
