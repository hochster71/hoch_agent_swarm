import React from "react";

export const SbomViewer: React.FC = () => {
  return (
    <div className="glass-panel p-4 rounded-xl border border-white/10 bg-white/2 text-left space-y-2">
      <h4 className="text-xs font-bold text-slate-300 uppercase tracking-wider">SBOM CycloneDX Manifest</h4>
      <div className="bg-black/40 rounded p-3 font-mono text-[10px] text-slate-300 space-y-1">
        <div>"bomFormat": "CycloneDX"</div>
        <div>"specVersion": "1.5"</div>
        <div>"serialNumber": "urn:uuid:f182c40e-2921-4f11-9a99-b137a1c0d20d"</div>
        <div>"version": 1</div>
        <div>"metadata": {"{"} "timestamp": "2026-06-24T12:00:00Z" {"}"}</div>
      </div>
    </div>
  );
};
