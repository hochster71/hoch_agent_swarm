import { Sidebar } from '@/components/Sidebar'
import { TopBar, StatusRibbon } from '@/components/TopBar'
import { VerseOfDay } from '@/components/VerseOfDay'
import { LiveRefresher } from '@/components/LiveRefresher'
import { BreakingIntelAlert } from '@/components/BreakingIntelAlert'
import { WelcomeBanner } from '@/components/WelcomeBanner'
import { FreshnessGuard } from '@/components/FreshnessGuard'
import { SubscriberGate } from '@/components/SubscriberGate'
import { WatchfloorProvider } from '@/components/WatchfloorMode'
import ProvenanceBanner from '@/components/ProvenanceBanner'

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <WatchfloorProvider>
    <div className="flex h-screen overflow-hidden bg-zinc-950">
      {/* First-visit explainer modal — dismissed to localStorage */}
      <WelcomeBanner />

      {/* Left navigation sidebar */}
      <Sidebar />

      {/* Main content column */}
      <div className="flex flex-1 flex-col overflow-hidden">
        <TopBar />

        {/* Persistent theater-status ribbon — key operational metrics on every page */}
        <StatusRibbon />

        {/* PROVENANCE — is this the real world, or the Epic Fury scenario? Rendered
            here in the LAYOUT so no dashboard can ever ship without declaring itself. */}
        <ProvenanceBanner />

        {/* Breaking intel alert — auto-surfaces high-confidence items < 45 min old */}
        <BreakingIntelAlert />

        {/* Daily Scripture strip — subtle faith anchor below command header */}
        <VerseOfDay />

        {/* Scrollable page content */}
        <main className="flex-1 overflow-y-auto p-4 md:p-6 scroll-smooth" aria-label="Dashboard content" id="main-content">
          <SubscriberGate>
            {children}

            {/* Silent background poller — re-fetches server state every 120 s + tab-focus + Supabase Realtime push */}
            <LiveRefresher intervalMs={120_000} showIndicator={true} />

            {/* Content freshness monitor — probes APIs every 60s, shows FRESH/AGING/STALE badge */}
            <FreshnessGuard />
          </SubscriberGate>
        </main>

        {/* Classification footer */}
        <footer className="classification-strip shrink-0 flex items-center justify-between px-4 backdrop-blur-sm">
          <span>Unclassified // AI-Synthesized Open-Source Intelligence // Live Analysis</span>
          <span className="text-zinc-700 hidden sm:block">Operation Epic Fury — C2 Dashboard</span>
          <span className="text-zinc-700">God is Great ✝</span>
        </footer>
      </div>

    </div>
    </WatchfloorProvider>
  )
}

