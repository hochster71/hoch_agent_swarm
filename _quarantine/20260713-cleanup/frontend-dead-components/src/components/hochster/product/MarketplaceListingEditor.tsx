import React from "react";
import { CheckCircle2 } from "lucide-react";

export const MarketplaceListingEditor: React.FC = () => {
  return (
    <div className="glass-panel p-4 rounded-xl border border-white/10 bg-white/2 space-y-4 text-left">
      <div className="flex items-center justify-between">
        <h4 className="text-xs font-bold text-slate-300 uppercase tracking-wider">Marketplace Listing</h4>
        <span className="text-[10px] px-1.5 py-0.5 rounded bg-green-500/10 text-green-400 font-bold">PUBLISHED</span>
      </div>

      <div className="grid grid-cols-2 gap-3 text-xs">
        <div className="p-3 rounded-lg bg-white/5 border border-white/5 space-y-1">
          <span className="text-[9px] text-slate-400 font-bold block uppercase">Capability Name</span>
          <span className="font-semibold text-white">HOCHSTER</span>
        </div>
        <div className="p-3 rounded-lg bg-white/5 border border-white/5 space-y-1">
          <span className="text-[9px] text-slate-400 font-bold block uppercase">Pricing Model</span>
          <span className="font-semibold text-white">Usage Based</span>
        </div>
      </div>

      <div className="flex gap-2">
        <button className="flex-1 bg-white/5 border border-white/10 hover:bg-white/10 text-slate-300 hover:text-white rounded-lg py-1.5 text-xs font-semibold transition text-center">
          Edit Listing
        </button>
        <button className="flex-1 bg-blue-600 hover:bg-blue-500 text-white rounded-lg py-1.5 text-xs font-bold transition text-center">
          View Marketplace
        </button>
      </div>
    </div>
  );
};
