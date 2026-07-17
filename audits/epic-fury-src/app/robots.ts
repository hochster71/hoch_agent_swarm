import type { MetadataRoute } from 'next'

export default function robots(): MetadataRoute.Robots {
  const base =
    process.env.NEXT_PUBLIC_APP_URL
      ?? (process.env.VERCEL_PROJECT_PRODUCTION_URL
          ? `https://${process.env.VERCEL_PROJECT_PRODUCTION_URL}`
          : 'https://epic-fury-2026.vercel.app')

  return {
    rules: [
      {
        userAgent: '*',
        allow: ['/', '/dashboard/'],
        disallow: ['/api/', '/debug/'],
      },
    ],
    sitemap: `${base}/sitemap.xml`,
    host: base,
  }
}
