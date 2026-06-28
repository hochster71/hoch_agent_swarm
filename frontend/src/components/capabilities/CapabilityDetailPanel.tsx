import { X, Play, ShieldAlert, CheckCircle, Ban, RefreshCcw, History } from "lucide-react";
import type { CapabilityRecord } from "../../lib/capabilities/capabilityTypes";
import { useCapabilityRegistryStore } from "../../lib/capabilities/capabilityRegistry";
import { PermissionManifest } from "./PermissionManifest";
import { CapabilityRiskPanel } from "./CapabilityRiskPanel";
import { CapabilityLifecycleTimeline } from "./CapabilityLifecycleTimeline";
import { CapabilityTestResults } from "./CapabilityTestResults";

type Props = {
  capability: CapabilityRecord;
  onClose: () => void;
};

export function CapabilityDetailPanel({ capability, onClose }: Props) {
  const { transitionLifecycle, executeCapability } = useCapabilityRegistryStore();

  const handleStatusChange = (status: typeof capability.status) => {
    transitionLifecycle(capability.capability_id, status);
  };

  const handleExecute = () => {
    const success = executeCapability(capability.capability_id);
    if (success) {
      alert(`Successfully triggered dry-run execution for: ${capability.name}`);
    } else {
      alert(`FAILED: Execution is restricted or retired for this capability.`);
    }
  };

  const getStatusBadge = () => {
    switch (capability.status) {
      case "approved":
        return "bg-green-950 border-green-800/40 text-green-400";
      case "restricted":
        return "bg-red-950 border-red-800/40 text-red-400";
      case "testing":
        return "bg-blue-950 border-blue-800/40 text-blue-400 animate-pulse";
      case "deprecated":
        return "bg-orange-950 border-orange-800/40 text-orange-400";
      case "retired":
        return "bg-slate-900 border-slate-800 text-slate-500";
      default:
        return "bg-slate-950 border-slate-800 text-slate-400";
    }
  };

  return (
    <div className="rounded-lg border border-slate-800 bg-slate-950/80 backdrop-blur-md p-6 font-mono space-y-6 max-h-[calc(100vh-140px)] overflow-y-auto w-full relative">
      {/* Top Header */}
      <div className="flex items-start justify-between border-b border-slate-900 pb-4">
        <div>
          <div className="flex items-center gap-2">
            <span className={`text-[9px] border px-2 py-0.5 rounded font-bold uppercase ${getStatusBadge()}`}>
              {capability.status}
            </span>
            <span className="text-[10px] text-slate-500 font-bold uppercase">{capability.kind}</span>
          </div>
          <h2 className="text-lg font-bold text-slate-100 mt-1">{capability.name}</h2>
          <p className="text-[10px] text-slate-500 mt-0.5">
            Owner: <span className="text-slate-300 font-bold">{capability.owner}</span> | Version: <span className="text-cyan-400">{capability.version}</span>
          </p>
        </div>
        <button
          onClick={onClose}
          className="p-1 rounded bg-slate-900/60 border border-slate-800 text-slate-500 hover:text-slate-200"
        >
          <X className="h-4 w-4" />
        </button>
      </div>

      {/* Description */}
      <div className="text-[11px] text-slate-400 bg-slate-900/30 p-3 rounded border border-slate-900/60 leading-relaxed">
        {capability.description}
      </div>

      {/* Action Toolbar */}
      <div className="flex flex-wrap gap-2 p-3 rounded-lg bg-slate-900/40 border border-slate-900/60">
        <button
          onClick={handleExecute}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded text-[10px] font-bold bg-cyan-500 text-slate-950 hover:bg-cyan-400 transition-all"
        >
          <Play className="h-3.5 w-3.5 fill-slate-950" />
          Test Run
        </button>

        {capability.status !== "approved" && (
          <button
            onClick={() => handleStatusChange("approved")}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded text-[10px] font-bold bg-green-950 border border-green-800 text-green-400 hover:bg-green-900/40 transition-all"
          >
            <CheckCircle className="h-3.5 w-3.5" />
            Approve
          </button>
        )}

        {capability.status !== "restricted" && (
          <button
            onClick={() => handleStatusChange("restricted")}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded text-[10px] font-bold bg-red-950 border border-red-800 text-red-400 hover:bg-red-900/40 transition-all"
          >
            <ShieldAlert className="h-3.5 w-3.5" />
            Restrict
          </button>
        )}

        {capability.status !== "deprecated" && capability.status !== "retired" && (
          <button
            onClick={() => handleStatusChange("deprecated")}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded text-[10px] font-bold bg-orange-950 border border-orange-800 text-orange-400 hover:bg-orange-900/40 transition-all"
          >
            <Ban className="h-3.5 w-3.5" />
            Deprecate
          </button>
        )}

        {capability.status !== "retired" && (
          <button
            onClick={() => handleStatusChange("retired")}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded text-[10px] font-bold bg-slate-900 border border-slate-800 text-slate-400 hover:bg-slate-800 transition-all"
          >
            <Ban className="h-3.5 w-3.5" />
            Retire
          </button>
        )}
      </div>

      {/* Grid Layout of Detailed Panels */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="space-y-6">
          <CapabilityRiskPanel capability={capability} />
          <CapabilityLifecycleTimeline capability={capability} />
        </div>
        <div className="space-y-6">
          <PermissionManifest capability={capability} />
          <CapabilityTestResults capability={capability} />
        </div>
      </div>
    </div>
  );
}
