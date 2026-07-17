'use client'

/**
 * global-error.tsx — catches errors thrown in app/layout.tsx and its children.
 * MUST have its own <html>/<body> tags (replaces the root layout when active).
 * Different from error.tsx which only catches page-level errors.
 */
export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string }
  reset: () => void
}) {
  return (
    <html lang="en">
      <body style={{ background: '#0a0a0a', color: '#ef4444', fontFamily: 'monospace', padding: 32, margin: 0, minHeight: '100vh' }}>
        <h1 style={{ fontSize: 18, marginBottom: 12, color: '#ef4444' }}>
          ⚠ ROOT LAYOUT ERROR — Operation Epic Fury
        </h1>
        <p style={{ color: '#71717a', fontSize: 12, marginBottom: 16 }}>
          This error is in app/layout.tsx or app/dashboard/layout.tsx (not the page itself).
        </p>
        <pre style={{
          background: '#18181b',
          color: '#d4d4d8',
          padding: 16,
          fontSize: 11,
          overflowX: 'auto',
          borderLeft: '2px solid #ef4444',
          marginBottom: 16,
          whiteSpace: 'pre-wrap',
          wordBreak: 'break-all',
        }}>
          {process.env.NODE_ENV === 'development'
            ? (error?.message || 'No error message') + '\n\n' + (error?.stack || '(no stack)')
            : (error?.message || 'An unexpected error occurred')}
        </pre>
        {error?.digest && (
          <p style={{ color: '#52525b', fontSize: 11, marginBottom: 16 }}>
            Digest: {error.digest}
          </p>
        )}
        <button
          onClick={reset}
          style={{
            background: 'transparent',
            border: '1px solid #22c55e',
            color: '#22c55e',
            padding: '8px 16px',
            cursor: 'pointer',
            fontFamily: 'monospace',
            fontSize: 12,
            letterSpacing: '0.1em',
          }}
        >
          ↺ RETRY
        </button>
      </body>
    </html>
  )
}
