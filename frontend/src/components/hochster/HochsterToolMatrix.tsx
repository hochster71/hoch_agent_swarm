import React from "react";
import { Hammer, CheckCircle2, ShieldAlert } from "lucide-react";
import { HochsterTool } from "../../lib/hochster/hochsterTypes";

interface Props {
  allowedTools: HochsterTool[];
}

export const HochsterToolMatrix: React.FC<Props> = ({ allowedTools }) => {
  const allTools: { name: string; description: string; policy: string; isAllowed: boolean }[] = [
    { name: "File System", description: "Read / Write (Controlled)", policy: "Allowlist enforced per request", isAllowed: allowedTools.includes("filesystem") },
    { name: "Shell / CLI", description: "Bash, PowerShell, CMD", policy: "Disabled by default in worker", isAllowed: allowedTools.includes("shell") },
    { name: "Docker", description: "Inspect, Logs, Exec (RO)", policy: "No socket mounting allowed", isAllowed: allowedTools.includes("docker") },
    { name: "Kubernetes", description: "Logs, Describe, Events", policy: "Audited requests via token", isAllowed: allowedTools.includes("kubernetes") },
    { name: "Tests", description: "Unit, Integration, E2E", policy: "Mock or sandboxed test runs", isAllowed: allowedTools.includes("tests") },
    { name: "Security", description: "SAST, DAST, Secrets, SBOM", policy: "Auto secrets redact checks", isAllowed: allowedTools.includes("security") },
    { name: "Database", description: "Query, Schema (RO)", policy: "Read-only connection bounds", isAllowed: allowedTools.includes("database") },
    { name: "Web / API", description: "HTTP, GraphQL, REST", policy: "Restricted to allowlist proxy", isAllowed: allowedTools.includes("web") },
    { name: "Diff / Patch", description: "Generate, Apply, Validate", policy: "Apply requires operator approval", isAllowed: allowedTools.includes("diff_patch") },
    { name: "Observability", description: "Logs, Metrics, Traces", policy: "OpenTelemetry instrumentation", isAllowed: allowedTools.includes("observability") },
    { name: "MCP Tools", description: "Discovery & Execution", policy: "Require manifest signature", isAllowed: allowedTools.includes("mcp") },
    { name: "Custom Tools", description: "User / Swarm Tools", policy: "Restricted sandbox sandbox execution", isAllowed: allowedTools.includes("custom" as any) }
  ];

  return (
    <div className="glass-panel p-5 rounded-xl border border-white/10 bg-white/2 space-y-4">
      <div className="flex justify-between items-center">
        <h3 className="text-lg font-bold flex items-center gap-2">
          <Hammer className="w-5 h-5 text-blue-400" /> Tool Capabilities
        </h3>
        <span className="text-xs text-slate-500 font-semibold cursor-pointer hover:underline">Manage Tools</span>
      </div>

      <div className="space-y-2.5">
        {allTools.map(t => (
          <div
            key={t.name}
            className={`p-2.5 rounded-lg border flex items-center justify-between gap-4 transition-all ${
              t.isAllowed
                ? "bg-blue-500/5 border-blue-500/20"
                : "bg-white/1 border-white/5 opacity-55"
            }`}
          >
            <div className="flex-1">
              <div className="flex items-center gap-2">
                <span className="font-bold text-xs text-white">{t.name}</span>
                <span className="text-[9px] text-slate-400 font-mono">({t.description})</span>
              </div>
              <p className="text-[10px] text-slate-500 font-medium mt-0.5">{t.policy}</p>
            </div>

            {t.isAllowed ? (
              <CheckCircle2 className="w-4 h-4 text-emerald-400 flex-shrink-0" />
            ) : (
              <ShieldAlert className="w-4 h-4 text-red-400 flex-shrink-0" />
            )}
          </div>
        ))}
      </div>
      
      <p className="text-[9px] text-slate-500 font-mono text-center pt-1">
        Tool Policy: Allowlist enforced per request
      </p>
    </div>
  );
};
