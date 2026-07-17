import VisualFeed from '@/components/VisualFeed'
import { Film, Shield } from 'lucide-react'

export const revalidate = 0
export const metadata = { title: 'Visual Storytelling | EPIC FURY 2026' }

export default function VisualsPage() {
  return (
    <div className="space-y-6 p-4 lg:p-6">
      {/* Page header */}
      <div className="flex flex-col gap-1">
        <div className="flex items-center gap-2">
          <Film className="w-5 h-5 text-violet-400" />
          <h1 className="text-sm font-bold tracking-widest text-violet-300 uppercase">
            Visual Epic Storytelling
          </h1>
          <span className="ml-auto text-[9px] font-mono text-zinc-600">GOVERNOR LAYER 4</span>
        </div>
        <p className="text-[10px] text-zinc-500 max-w-prose leading-relaxed">
          AI-generated cinematic visuals for every verified intel item. DALL-E 3 images, Kling/Runway video,
          and Grok Imagine assets — post LLM-as-Judge verification only. All content labelled
          &ldquo;EPIC FURY AI Visual – Fact-Checked&rdquo;.
        </p>
      </div>

      {/* Ethics notice */}
      <div className="rounded border border-amber-800/30 bg-amber-950/10 p-3 flex items-start gap-2">
        <Shield className="w-3.5 h-3.5 text-amber-500 flex-shrink-0 mt-0.5" />
        <div className="text-[9px] text-amber-400/80 leading-relaxed">
          <strong>Ethical AI Visual Policy:</strong> No generated content is presented as real footage.
          Every visual is generated <em>only after</em> full symbolic KG verification and LLM-as-Judge gate (Layer 2).
          All assets carry a &ldquo;EPIC FURY AI Visual – Fact-Checked&rdquo; watermark and AI-generated provenance metadata.
          Video assets (Kling, Runway) are queued until provider API keys are configured.
        </div>
      </div>

      {/* Visual feed */}
      <VisualFeed compact={false} />
    </div>
  )
}
