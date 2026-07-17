# EPIC FURY Dashboard

> **OPERATION EPIC FURY – DAY 20** | Tactical Intelligence Dashboard

A dark-mode, military HUD-style Next.js 15 (App Router) webapp with Supabase realtime intel feed, animated DMO simulation, and AI agent roster.

---

## Tech Stack

| Layer | Tech |
|---|---|
| Framework | Next.js 15 (App Router, RSC, Server Actions) |
| Language | TypeScript (strict) |
| Styling | Tailwind CSS + custom tactical theme |
| UI primitives | shadcn/ui (Radix under the hood) |
| Backend/DB | Supabase (Postgres + Realtime) |
| Icons | lucide-react |
| Canvas Sim | HTML5 Canvas (no extra dependency) |

---

## Folder Structure

```
epic-fury-dashboard/
├── app/
│   ├── layout.tsx          # Root layout with scanline overlay
│   ├── page.tsx            # Redirects → /dashboard/feed
│   ├── globals.css         # Tailwind base + HUD CSS utilities
│   └── dashboard/
│       ├── layout.tsx      # Sidebar + TopBar shell
│       ├── feed/page.tsx   # Live intel feed (Realtime)
│       ├── agents/page.tsx # AI agent roster grid
│       ├── dmo/page.tsx    # DMO canvas simulation
│       └── settings/page.tsx
├── components/
│   ├── ScanlineOverlay.tsx # Fixed CSS HUD effects
│   ├── Sidebar.tsx         # Nav sidebar (mobile-responsive)
│   ├── TopBar.tsx          # Operation title + live clock
│   ├── IntelCard.tsx       # Intel report card
│   ├── AgentCard.tsx       # Agent card (expandable log)
│   ├── FeedRealtimeWrapper.tsx  # Client realtime subscription
│   └── DmoCanvas.tsx       # Animated canvas simulation
├── lib/
│   ├── supabase.ts         # Server + browser Supabase clients
│   ├── types.ts            # Domain types + DB type map
│   └── utils.ts            # cn() Tailwind helper
├── supabase/
│   └── migrations/
│       └── 20260101000000_init.sql
├── next.config.mjs
├── tailwind.config.ts
├── tsconfig.json
├── components.json
└── .env.example
```

---

## Quick Start

### 1. Install dependencies

```bash
cd epic-fury-dashboard
npm install
```

### 2. Configure environment

```bash
cp .env.example .env.local
# Fill in your Supabase project URL and anon key
```

For paid web checkout, also configure Stripe variables in your deployment environment:

- `STRIPE_SECRET_KEY`
- `STRIPE_PRICE_MONTHLY`
- `STRIPE_PRICE_ANNUAL`
- `STRIPE_PRICE_LIFETIME`
- `STRIPE_WEBHOOK_SECRET`

### 3. Set up the database

**Option A – Supabase Cloud (recommended for first run)**

1. Create a project at [supabase.com](https://supabase.com)
2. Open the SQL editor and paste the contents of `supabase/migrations/20260101000000_init.sql`
3. Copy your project URL + anon key into `.env.local`

**Option B – Supabase CLI**

```bash
npx supabase login
npx supabase db push
```

**Option C – Self-hosted Docker Compose**

See [Supabase self-hosting docs](https://supabase.com/docs/guides/self-hosting/docker).  
Set `NEXT_PUBLIC_SUPABASE_URL=http://kong:8000` in your environment and add `HOSTNAME=0.0.0.0` to the `nextjs` service.

### 4. Run the dev server

```bash
npm run dev
# → http://localhost:3000
```

---

## Pages

| Route | Description |
|---|---|
| `/dashboard/feed` | Live intel feed with Supabase Realtime |
| `/dashboard/agents` | 9 AI agent cards with reasoning logs |
| `/dashboard/dmo` | Animated Hormuz Strait DMO simulation |
| `/dashboard/settings` | Config overview |

---

## Adding Intel Reports

Insert rows into the `intel` table to populate the live feed:

```sql
insert into public.intel (title, summary, theater, confidence)
values ('Test Report', 'Summary here.', 'Hormuz', 85);
```

The feed will update **in real-time** without a page refresh.

---

## Common Fixes

| Symptom | Fix |
|---|---|
| Dashboard not loading in Docker | Add `HOSTNAME=0.0.0.0` to nextjs environment |
| Supabase connection refused | Set `NEXT_PUBLIC_SUPABASE_URL=http://kong:8000` (not localhost) inside Docker |
| CSP errors in browser console | Edit `connect-src` in `next.config.mjs` headers |
| Font not loading offline | Embed JetBrains Mono locally via `public/fonts/` |

---

## Production Build

```bash
npm run build
npm start
```

## Deployment Scripts

Use the repo-root helper scripts for production rollout:

```bash
# One-command release runner (preflight checks + deploy)
./run-production-release.sh

# One-time setup helper for missing paid-access production vars
# (auto-finds/creates STRIPE_PRICE_LIFETIME + generates REVENUECAT_WEBHOOK_SECRET)
./configure-billing-env.sh

# Optional: set explicit lifetime amount in USD when auto-creating (default: 149)
./configure-billing-env.sh auto 149

# Interactive flow (will prompt for Vercel login/setup/approvals when needed)
./go-production.sh

# Non-interactive CI flow (requires linked project + VERCEL_TOKEN)
VERCEL_TOKEN=your_token_here ./go-production-ci.sh
```

`run-production-release.sh` checks required production billing variables in Vercel first:

- `STRIPE_SECRET_KEY`
- `STRIPE_PRICE_MONTHLY`
- `STRIPE_PRICE_ANNUAL`
- `STRIPE_PRICE_LIFETIME`
- `STRIPE_WEBHOOK_SECRET`
- `REVENUECAT_WEBHOOK_SECRET`

Release gate additions:

- Environment readiness gate: `node scripts/ci/env-readiness.mjs --mode enforce`
- Truth gate enforcement: `npm run truth:gate -- --mode enforce`

Operational monitoring endpoint:

- `GET /api/platform/agent-runs?limit=25`
	- Requires signed-in subscriber/admin session
	- Returns recent autonomous agent/cron run logs and success-rate summary

Google OAuth safety switch:

- `NEXT_PUBLIC_ENABLE_GOOGLE_OAUTH=true` to show/enable Google login button
- If unset/false, login page uses magic-link only (prevents provider-disabled OAuth 400s)

---

*UNCLASSIFIED // DEMONSTRATION ONLY*
