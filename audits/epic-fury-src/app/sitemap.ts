import type { MetadataRoute } from 'next'

export default function sitemap(): MetadataRoute.Sitemap {
  const base =
    process.env.NEXT_PUBLIC_APP_URL
      ?? (process.env.VERCEL_PROJECT_PRODUCTION_URL
          ? `https://${process.env.VERCEL_PROJECT_PRODUCTION_URL}`
          : 'https://epic-fury-2026.vercel.app')

  const now = new Date().toISOString()

  const staticRoutes: MetadataRoute.Sitemap = [
    { url: base,                              lastModified: now, changeFrequency: 'hourly',  priority: 1.0 },
    { url: `${base}/dashboard`,              lastModified: now, changeFrequency: 'hourly',  priority: 0.9 },
    { url: `${base}/dashboard/intel`,        lastModified: now, changeFrequency: 'always',  priority: 0.9 },
    { url: `${base}/dashboard/sitrep`,       lastModified: now, changeFrequency: 'always',  priority: 0.9 },
    { url: `${base}/dashboard/feed`,         lastModified: now, changeFrequency: 'always',  priority: 0.8 },
    { url: `${base}/dashboard/news`,         lastModified: now, changeFrequency: 'always',  priority: 0.8 },
    { url: `${base}/dashboard/threats`,      lastModified: now, changeFrequency: 'hourly',  priority: 0.8 },
    { url: `${base}/dashboard/ceasefire`,    lastModified: now, changeFrequency: 'hourly',  priority: 0.8 },
    { url: `${base}/dashboard/econ`,         lastModified: now, changeFrequency: 'hourly',  priority: 0.7 },
    { url: `${base}/dashboard/homeland`,     lastModified: now, changeFrequency: 'hourly',  priority: 0.7 },
    { url: `${base}/dashboard/bda`,          lastModified: now, changeFrequency: 'hourly',  priority: 0.7 },
    { url: `${base}/dashboard/timeline`,     lastModified: now, changeFrequency: 'daily',   priority: 0.6 },
    { url: `${base}/dashboard/agents`,       lastModified: now, changeFrequency: 'weekly',  priority: 0.5 },
  ]

  return staticRoutes
}
