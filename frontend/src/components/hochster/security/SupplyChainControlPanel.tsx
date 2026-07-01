import React from "react";
import { CheckCircle2, ShieldCheck, FileCheck, Layers } from "lucide-react";

export const SupplyChainControlPanel: React.FC = () => {
  return (
    <div className="glass-panel p-4 rounded-xl border border-white/10 bg-white/2 space-y-4 text-left">
      <div>
        <h4 className="text-xs font-bold text-slate-300 uppercase tracking-wider">Supply-Chain & Integrity</h4>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
        <div className="p-3 rounded-xl bg-white/5 border border-white/5 space-y-1">
          <span className="text-[9px] text-slate-400 font-bold block uppercase">SBOM</span>
          <div className="flex items-center gap-1">
            <CheckCircle2 className="w-3.5 h-3.5 text-green-400" />
            <span className="text-[10px] text-green-400 font-bold">Generated</span>
          </div>
          <span className="text-[8px] text-slate-400 block">Components: 1,248</span>
        </div>

        <div className="p-3 rounded-xl bg-white/5 border border-white/5 space-y-1">
          <span className="text-[9px] text-slate-400 font-bold block uppercase">Provenance (SLSA Level)</span>
          <div className="flex items-center gap-1">
            <CheckCircle2 className="w-3.5 h-3.5 text-green-400" />
            <span className="text-[10px] text-green-400 font-bold">Level 3</span>
          </div>
          <span className="text-[8px] text-slate-400 block">Build Provenance</span>
        </div>

        <div className="p-3 rounded-xl bg-white/5 border border-white/5 space-y-1">
          <span className="text-[9px] text-slate-400 font-bold block uppercase">Image Signing</span>
          <div className="flex items-center gap-1">
            <CheckCircle2 className="w-3.5 h-3.5 text-green-400" />
            <span className="text-[10px] text-green-400 font-bold">Signed</span>
          </div>
          <span className="text-[8px] text-slate-400 block">Cosign Verified</span>
        </div>

        <div className="p-3 rounded-xl bg-white/5 border border-white/5 space-y-1">
          <span className="text-[9px] text-slate-400 font-bold block uppercase">Dependency Scan</span>
          <div className="flex items-center gap-1">
            <CheckCircle2 className="w-3.5 h-3.5 text-green-400" />
            <span className="text-[10px] text-green-400 font-bold">No Critical</span>
          </div>
          <span className="text-[8px] text-slate-400 block">High: 2 | Medium: 6</span>
        </div>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-2 pt-2">
        <button className="bg-white/5 border border-white/10 hover:bg-white/10 text-slate-300 hover:text-white rounded-lg py-1.5 text-[10px] font-semibold transition text-center">
          View SBOM
        </button>
        <button className="bg-white/5 border border-white/10 hover:bg-white/10 text-slate-300 hover:text-white rounded-lg py-1.5 text-[10px] font-semibold transition text-center">
          View Attestation
        </button>
        <button className="bg-white/5 border border-white/10 hover:bg-white/10 text-slate-300 hover:text-white rounded-lg py-1.5 text-[10px] font-semibold transition text-center">
          View Signatures
        </button>
        <button className="bg-white/5 border border-white/10 hover:bg-white/10 text-slate-300 hover:text-white rounded-lg py-1.5 text-[10px] font-semibold transition text-center">
          View Report
        </button>
      </div>
    </div>
  );
};
