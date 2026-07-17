/**
 * Diagnostic page — zero external imports, zero Supabase, zero components.
 * Visit http://localhost:3003/debug to verify Next.js is running.
 * If THIS page loads, the issue is inside the dashboard components.
 * If THIS page also 500s, the issue is in app/layout.tsx or Node/Next.js itself.
 */
export default function DebugPage() {
  const ts = new Date().toISOString()
  return (
    <div style={{ background: '#000', color: '#00ff00', fontFamily: 'monospace', padding: 32, minHeight: '100vh' }}>
      <h1 style={{ fontSize: 20, marginBottom: 16 }}>✅ NEXT.JS IS WORKING</h1>
      <p style={{ color: '#aaa', marginBottom: 8 }}>This page has zero external imports.</p>
      <p style={{ color: '#aaa', marginBottom: 8 }}>Server timestamp: <strong style={{ color: '#00ff00' }}>{ts}</strong></p>
      <p style={{ color: '#aaa', marginBottom: 24 }}>NODE_ENV: <strong style={{ color: '#ffd700' }}>{process.env.NODE_ENV}</strong></p>
      <p style={{ color: '#666', fontSize: 12 }}>
        If you see this but /dashboard still 500s, the error is in a dashboard component.
        Check your Terminal.app where npm run dev is running for the red error stack trace.
      </p>
    </div>
  )
}
