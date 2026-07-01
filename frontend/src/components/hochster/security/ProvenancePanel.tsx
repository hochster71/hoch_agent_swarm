import React from "react";
import { CheckCircle2 } from "lucide-react";

export const ProvenancePanel: React.FC = () => {
  return (
    <div className="glass-panel p-4 rounded-xl border border-white/10 bg-white/2 text-left space-y-3">
      <h4 className="text-xs font-bold text-slate-300 uppercase tracking-wider">Provenance Attestation (SLSA)</h4>
      <div className="space-y-2 text-xs">
        <div className="flex justify-between border-b border-white/5 pb-1">
          <span className="text-slate-400">Builder</span>
          <span className="text-white">GitHub Actions Runner</span>
        </div>
        <div className="flex justify-between border-b border-white/5 pb-1">
          <span className="text-slate-400">SLSA Level</span>
          <span className="text-green-400 font-bold">Level 3</span>
        </div>
        <div className="flex justify-between border-b border-white/5 pb-1">
          <span className="text-slate-400">Build Config Source</span>
          <span className="font-mono text-slate-300">.github/workflows/build.yml</span>
        </div>
      </div>
    </div>
  );
};
