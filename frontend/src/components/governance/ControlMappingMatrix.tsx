import { useState } from "react";
import { useGovernanceRegistryStore } from "../../lib/governance/aiSystemRegistry";
import { frameworkDefinitions } from "../../lib/governance/complianceFrameworks";
import type { ControlStatus } from "../../lib/governance/governanceTypes";
import { CheckCircle, AlertTriangle, XCircle, HelpCircle, Layers } from "lucide-react";

export function ControlMappingMatrix() {
  const { systems, updateControlStatus } = useGovernanceRegistryStore();
  const [selectedSystemId, setSelectedSystemId] = useState(systems[0]?.system_id || "");

  const activeSystem = systems.find((s) => s.system_id === selectedSystemId);

  const getStatusIcon = (status: ControlStatus) => {
    switch (status) {
      case "implemented":
        return <CheckCircle className="h-4 w-4 text-green-500" />;
      case "partial":
        return <AlertTriangle className="h-4 w-4 text-yellow-500" />;
      case "missing":
        return <XCircle className="h-4 w-4 text-red-500" />;
      case "not_applicable":
        return <HelpCircle className="h-4 w-4 text-slate-500" />;
    }
  };

  const handleStatusChange = (controlId: string, status: ControlStatus) => {
    if (!activeSystem) return;
    const evidenceRef = status === "implemented" ? `evidence.${activeSystem.system_id}.${controlId.toLowerCase().replace(/-/g, "_")}` : undefined;
    updateControlStatus(activeSystem.system_id, controlId, status, evidenceRef);
  };

  return (
    <div className="rounded-lg border border-slate-800 bg-slate-950/60 p-4 backdrop-blur-md">
      <div className="mb-4 flex flex-col md:flex-row md:items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <Layers className="h-4 w-4 text-cyan-400" />
          <h3 className="font-mono text-sm font-semibold tracking-wider text-slate-200">
            COMPLIANCE CONTROL MAPPING MATRIX
          </h3>
        </div>

        {/* System Selector */}
        <div className="flex items-center gap-2 font-mono text-xs">
          <span className="text-slate-400">Target System:</span>
          <select
            value={selectedSystemId}
            onChange={(e) => setSelectedSystemId(e.target.value)}
            className="rounded border border-slate-800 bg-slate-900 px-3 py-1 text-slate-200 focus:outline-none focus:border-cyan-500"
          >
            {systems.map((s) => (
              <option key={s.system_id} value={s.system_id}>
                {s.name} ({s.risk_tier.toUpperCase()})
              </option>
            ))}
          </select>
        </div>
      </div>

      {activeSystem ? (
        <div className="overflow-x-auto">
          <table className="w-full border-collapse font-mono text-[11px] text-slate-300">
            <thead>
              <tr className="border-b border-slate-800 text-left text-slate-400 uppercase font-semibold tracking-wider">
                <th className="py-2 px-3">Control Code</th>
                <th className="py-2 px-3">Framework</th>
                <th className="py-2 px-3">Control Name & Description</th>
                <th className="py-2 px-3">Mapping Evidence</th>
                <th className="py-2 px-3 text-center">Implementation Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-900">
              {frameworkDefinitions.map((def) => {
                const systemMapping = activeSystem.controls.find((c) => c.control_id === def.control_id) || {
                  status: "missing" as ControlStatus,
                  evidence_refs: [] as string[],
                };

                return (
                  <tr key={def.control_id} className="hover:bg-slate-900/20 transition-colors">
                    <td className="py-3 px-3 font-bold text-slate-200">{def.control_id}</td>
                    <td className="py-3 px-3 uppercase text-[10px] text-slate-500">{def.framework.replace(/_/g, " ")}</td>
                    <td className="py-3 px-3">
                      <div className="font-semibold text-slate-300">{def.name}</div>
                      <div className="text-[10px] text-slate-500 mt-0.5">{def.description}</div>
                    </td>
                    <td className="py-3 px-3">
                      {systemMapping.evidence_refs.length > 0 ? (
                        <div className="space-y-1">
                          {systemMapping.evidence_refs.map((ref) => (
                            <div key={ref} className="text-[10px] text-cyan-400 underline">
                              {ref}
                            </div>
                          ))}
                        </div>
                      ) : (
                        <span className="text-slate-600 italic">No evidence uploaded</span>
                      )}
                    </td>
                    <td className="py-3 px-3">
                      <div className="flex items-center justify-center gap-2">
                        {getStatusIcon(systemMapping.status)}
                        <select
                          value={systemMapping.status}
                          onChange={(e) => handleStatusChange(def.control_id, e.target.value as ControlStatus)}
                          className="rounded border border-slate-900 bg-slate-950 px-1.5 py-0.5 text-[10px] text-slate-300 focus:outline-none focus:border-cyan-500/50"
                        >
                          <option value="implemented">Implemented</option>
                          <option value="partial">Partial</option>
                          <option value="missing">Missing</option>
                          <option value="not_applicable">Not Applicable</option>
                        </select>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="text-center py-6 font-mono text-xs text-slate-500 italic">
          No registered systems selected or available.
        </div>
      )}
    </div>
  );
}
