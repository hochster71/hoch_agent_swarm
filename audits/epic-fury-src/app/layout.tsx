import type { Metadata, Viewport } from 'next'
import { JetBrains_Mono } from 'next/font/google'
import { headers } from 'next/headers'
import './globals.css'
import { ScanlineOverlay }    from '@/components/ScanlineOverlay'
import { PurchasesProvider }  from '@/components/PurchasesProvider'

const jetbrainsMono = JetBrains_Mono({
  subsets: ['latin'],
  weight: ['300', '400', '500', '700'],
  display: 'swap',
  variable: '--font-jetbrains-mono',
})

export const metadata: Metadata = {
  title: {
    default: 'Epic Fury — Conflict Modeling & Analysis Tool (Not Live Reporting)',
    template: '%s | Epic Fury',
  },
  // This app does NOT observe live events. It projects figures from a model. Describing
  // it as "real-time", "live war news", or "casualty tracking" ranked it for exactly the
  // searches a frightened citizen makes -- and then showed them numbers that are not
  // current reporting and can contradict what is actually happening.
  description:
    'An analytical modeling tool for the 2026 US-Iran conflict. Figures are model PROJECTIONS, not verified current reporting, and may contradict live events. For current news, use CENTCOM, DoD, or a wire service.',
  keywords: [
    'conflict modeling', 'analysis tool', 'scenario modeling', 'wargaming',
  ],
  metadataBase: new URL(
    process.env.NEXT_PUBLIC_APP_URL
      ?? (process.env.VERCEL_PROJECT_PRODUCTION_URL
          ? `https://${process.env.VERCEL_PROJECT_PRODUCTION_URL}`
          : 'https://epic-fury-2026.vercel.app')
  ),
  authors: [{ name: 'Epic Fury Intelligence Network' }],
  robots: { index: true, follow: true, googleBot: { index: true, follow: true } },
  openGraph: {
    type: 'website',
    locale: 'en_US',
    siteName: 'Epic Fury',
    title: 'Epic Fury — Conflict Modeling Tool (Not Live Reporting)',
    description:
      'Analytical conflict modeling. Figures are model projections, NOT verified current reporting. Do not rely on this for current events.',
    images: [
      {
        url: '/opengraph-image',
        width: 1200,
        height: 630,
        alt: 'Epic Fury — conflict modeling tool. Projections, not live reporting.',
      },
    ],
  },
  twitter: {
    card: 'summary_large_image',
    title: 'Epic Fury — Conflict Modeling Tool (Not Live Reporting)',
    description:
      'Model projections, not verified current reporting. Do not rely on this for current events.',
    images: ['/opengraph-image'],
  },
  manifest: '/manifest.json',
}

export const viewport: Viewport = {
  width: 'device-width',
  initialScale: 1,
  maximumScale: 1,
  viewportFit: 'cover',
  themeColor: '#09090b',
}

export default async function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  // Read the per-request nonce forwarded by middleware (x-nonce request header).
  // Pass `nonce` to any <Script nonce={nonce}> tags to allow them under the
  // strict nonce-based CSP set in middleware.ts.
  const nonce = (await headers()).get('x-nonce') ?? ''

  return (
      <html lang="en" className="dark" suppressHydrationWarning data-scroll-behavior="smooth">
      <head>
      </head>
      <body className={`min-h-screen bg-zinc-950 ${jetbrainsMono.variable} font-mono antialiased`} data-nonce={nonce || undefined}>
        {/* HUD overlay effects */}
        <ScanlineOverlay />
        {/* RevenueCat — initialises StoreKit on native iOS only */}
        <PurchasesProvider />
        {children}
      </body>
    </html>
  )
}
