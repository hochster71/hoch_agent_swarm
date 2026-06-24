import { History, Calendar, CheckCircle } from "lucide-react";
import type { CapabilityRecord, CapabilityStatus } from "../../lib/capabilities/capabilityTypes";

type Props = {
  capability: CapabilityRecord;
};

export function CapabilityLifecycleTimeline({ capability }: Props) {
  const steps: { key: CapabilityStatus; label: string; date?: string; desc: string }[] = [
    { key: "draft", label: "Draft", date: capability.lifecycle.created_at, desc: "Created and registered in Swarm Sandbox registry." },
    { key: "testing", label: "Testing", date: capability.lifecycle.created_at, desc: "Run validation scripts and security checks." },
    { key: "approved", label: "Approved", date: capability.lifecycle.approved_at, desc: "Passed verification, eligible for live cluster orchestration." },
    { key: "restricted", label: "Restricted", desc: "Flagged by security scans. Temporarily locked." },
    { key: "deprecated", label: "Deprecated", date: capability.lifecycle.deprecated_at, desc: "Scheduled for retirement. Active but not recommended." },
    { key: "retired", label: "Retired", date: capability.lifecycle.retired_at, desc: "Decommissioned. Completely blocked from cluster execution." },
  ];

  const currentIdx = steps.findIndex((s) => s.key === capability.status);

  return (
    <div className="rounded-lg border border-slate-800 bg-slate-950/60 p-4 font-mono text-[11px]">
      <h3 className="text-xs font-bold tracking-wider text-slate-400 mb-3 uppercase flex items-center gap-2">
        <History className="h-4 w-4 text-cyan-400" />
        Capability Lifecycle Timeline
      </h3>

      <div className="relative border-l border-slate-800 pl-4 space-y-4">
        {steps.map((step, idx) => {
          const isActive = capability.status === step.key;
          const isPast = steps.findIndex((s) => s.key === capability.status) >= idx;
          const isRestrictedState = capability.status === "restricted" && step.key === "restricted";

          if (step.key === "restricted" && capability.status !== "restricted") {
            return null; // Skip rendering restricted node unless we are in restricted state
          }

          return (
            <div key={step.key} className="relative">
              {/* Dot */}
              <div
                className={`absolute -left-[21px] top-1 h-2.5 w-2.5 rounded-full border transition-all ${
                  isActive
                    ? step.key === "restricted"
                      ? "bg-red-500 border-red-400 animate-pulse scale-125"
                      : "bg-cyan-500 border-cyan-400 animate-pulse scale-125"
                    : isPast
                    ? "bg-slate-400 border-slate-300"
                    : "bg-slate-950 border-slate-800"
                }`}
              />

              <div className="flex flex-col gap-0.5">
                <div className="flex items-center gap-2">
                  <span className={`font-bold ${isActive ? "text-cyan-400" : isPast ? "text-slate-300" : "text-slate-600"}`}>
                    {step.label}
                  </span>
                  {step.date && (
                    <span className="text-[9px] text-slate-500 flex items-center gap-1">
                      <Calendar className="h-3 w-3" />
                      {new Date(step.date).toLocaleDateString()}
                    </span>
                  )}
                  {isActive && (
                    <span className="text-[9px] bg-cyan-950 border border-cyan-800/40 text-cyan-400 px-1.5 py-0.5 rounded font-bold uppercase animate-pulse">
                      Active State
                    </span>
                  )}
                </div>
                <span className="text-[9px] text-slate-500">{step.desc}</span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
