import ForesightPanel from '@/components/ForesightPanel'

export const metadata = {
  title: 'Layer 9 Foresight — EPIC FURY 2026',
  description: 'Predictive Intelligence, TRiSM Governance, GEA Memory, Ethical AI Constitution',
}

export default function ForesightPage() {
  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="border-b border-gray-800 pb-4">
        <h1 className="text-xl font-bold font-mono text-purple-400 tracking-wider">
          ⚡ LAYER 9 — PREDICTIVE FORESIGHT
        </h1>
        <p className="text-sm text-gray-500 mt-1 font-mono">
          MC-Search foresight · TRiSM governance · GEA experience pool · multi-agent memory · Ethical AI Constitution
        </p>
      </div>

      {/* Full foresight panel */}
      <ForesightPanel />
    </div>
  )
}
