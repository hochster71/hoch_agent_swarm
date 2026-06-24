import React from "react";
import { Terminal, Shield, Play } from "lucide-react";

interface Job {
  job_id: string;
  role: string;
  objective: string;
  tools: string[];
  mutation: string;
  severity: "critical" | "high" | "medium";
  status: "idle" | "running" | "success" | "failed";
}

const initialJobs: Job[] = [
  { job_id: "RT-001", role: "hochster-ui-static-01", objective: "Detect mock/static frontend state", tools: ["filesystem", "tests", "diff_patch"], mutation: "No", severity: "critical", status: "success" },
  { job_id: "RT-002", role: "hochster-api-live-01", objective: "Verify live timestamp contract on API payloads", tools: ["filesystem", "observability", "tests"], mutation: "No", severity: "critical", status: "success" },
  { job_id: "RT-003", role: "hochster-stream-01", objective: "Verify WebSocket/SSE freshness and heartbeat", tools: ["observability", "tests"], mutation: "No", severity: "critical", status: "success" },
  { job_id: "RT-004", role: "hochster-docker-01", objective: "Reconcile Docker health vs UI health", tools: ["docker", "observability"], mutation: "No", severity: "high", status: "success" },
  { job_id: "RT-005", role: "hochster-policy-01", objective: "Prove server-side policy enforcement", tools: ["filesystem", "tests"], mutation: "No", severity: "critical", status: "success" },
  { job_id: "RT-006", role: "hochster-audit-01", objective: "Validate audit schema and evidence refs", tools: ["filesystem", "tests"], mutation: "No", severity: "high", status: "success" },
  { job_id: "RT-007", role: "hochster-stale-01", objective: "Inject stale telemetry scenarios", tools: ["tests", "observability"], mutation: "No", severity: "critical", status: "success" },
  { job_id: "RT-008", role: "hochster-patch-01", objective: "Generate candidate patches for P0 blockers", tools: ["filesystem", "diff_patch", "tests"], mutation: "No direct apply", severity: "high", status: "success" },
  { job_id: "RT-009", role: "hochster-release-01", objective: "Verify release/supply-chain lock metadata", tools: ["filesystem", "security"], mutation: "No", severity: "high", status: "success" }
];

export const HochsterJobQueuePanel: React.FC = () => {
  return (
    <div className="glass-panel p-4 rounded-xl border border-white/10 bg-slate-900/40 backdrop-blur-md space-y-4 text-left">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Terminal className="w-4 h-4 text-blue-400" />
          <h4 className="text-xs font-bold text-slate-300 uppercase tracking-wider font-semibold">HOCHSTER Cluster Job Queue</h4>
        </div>
        <span className="text-[10px] px-2 py-0.5 rounded bg-blue-500/10 text-blue-400 font-bold font-mono">RT-Active Queue</span>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="border-b border-white/5 text-[9px] uppercase text-slate-400 font-bold">
              <th className="py-2 pr-2">Job ID</th>
              <th className="py-2 pr-2">HOCHSTER Role</th>
              <th className="py-2 pr-2">Objective</th>
              <th className="py-2 pr-2">Mutation</th>
              <th className="py-2 pr-2">Severity</th>
              <th className="py-2 text-right">Status</th>
            </tr>
          </thead>
          <tbody>
            {initialJobs.map((job) => (
              <tr key={job.job_id} className="border-b border-white/5 hover:bg-white/5 transition text-[11px]">
                <td className="py-2 pr-2 font-mono font-bold text-blue-400">{job.job_id}</td>
                <td className="py-2 pr-2 font-mono text-slate-300 text-[10px]">{job.role}</td>
                <td className="py-2 pr-2 text-slate-200 max-w-[180px] truncate" title={job.objective}>
                  {job.objective}
                </td>
                <td className="py-2 pr-2 text-slate-400">{job.mutation}</td>
                <td className="py-2 pr-2">
                  <span className={`px-1.5 py-0.5 rounded text-[8px] font-bold uppercase ${
                    job.severity === "critical" 
                      ? "bg-red-500/10 text-red-400" 
                      : "bg-yellow-500/10 text-yellow-400"
                  }`}>
                    {job.severity}
                  </span>
                </td>
                <td className="py-2 text-right">
                  <span className="text-green-400 font-bold uppercase text-[9px] flex items-center gap-1 justify-end">
                    <span className="w-1.5 h-1.5 rounded-full bg-green-400"></span>
                    {job.status}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};
