/**
 * app/dashboard/command/page.tsx — Epic Fury Command Center
 *
 * Operator-only remote console tracking ALL autonomous platform operations:
 * Governor 10-layer cycles, Platform Health, AEC, Revenue Engine,
 * Workflow Engine, Neural Truth, GEA Foresight, Visual Engine, ORACLE-9.
 *
 * NOT a public page — internal command & control for platform operators.
 */

import type { Metadata } from 'next'
import CommandCenterDashboard from '@/components/CommandCenterDashboard'
import { Terminal, Zap } from 'lucide-react'

export const metadata: Metadata = {
  title: 'Command Center — EPIC FURY OPS REMOTE',
  description: 'Full-platform autonomous operations command center — all 10 governor layers, health, AEC, revenue, foresight, and ORACLE-9.',
}

export const dynamic    = 'force-dynamic'
export const revalidate = 0

export default function CommandPage() {
  return (
    <div className="space-y-4">
      {/* Page header — military-style op banner */}
      <div className="rounded-lg border border-red-900/50 bg-red-950/10 px-4 py-3">
        <div className="flex items-center justify-between flex-wrap gap-3">
          <div className="flex items-center gap-3">
            <Terminal className="w-5 h-5 text-red-400 flex-shrink-0" />
            <div>
              <p className="text-[8px] tracking-[0.3em] text-zinc-500 uppercase">
                UNCLASSIFIED // AI LIVE // OPERATOR ACCESS
              </p>
              <h1 className="text-base font-bold font-mono tracking-widest text-red-300 uppercase">
                EPIC FURY — Autonomous Operations Command Center
              </h1>
              <p className="text-[10px] text-zinc-500 mt-0.5">
                Real-time telemetry of all 10 Governor layers · platform health · AEC cycles ·
                revenue autonomy · foresight · neural truth · cron schedule
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Zap className="w-3 h-3 text-emerald-400 animate-pulse" />
            <span className="text-[9px] text-emerald-400 font-mono tracking-widest uppercase">
              All Systems Autonomous
            </span>
          </div>
        </div>
      </div>

      {/* Full Command Center dashboard */}
      <CommandCenterDashboard />
    </div>
  )
}
