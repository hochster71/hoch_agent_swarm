import { useCapabilityRegistryStore } from "../../lib/capabilities/capabilityRegistry";
import type { CapabilityRecord } from "../../lib/capabilities/capabilityTypes";
import { Wrench, Globe, GitFork, Network } from "lucide-react";

type Props = {
  onSelect: (cap: CapabilityRecord) => void;
  selectedId?: string;
};

export function ToolRegistry({ onSelect, selectedId }: Props) {
  const { capabilities } = useCapabilityRegistryStore();

  const tools = capabilities.filter((c) => c.kind !== "agent" && c.kind !== "skill");

  const getStatusColor = (status: CapabilityRecord["status"]) => {
    switch (status) {
      case "approved":
        return "text-green-400";
      case "restricted":
        return "text-red-400";
      case "testing":
        return "text-blue-400";
      case "deprecated":
        return "text-orange-400";
      default:
        return "text-slate-400";
    }
  };

  const getRiskColor = (risk: CapabilityRecord["risk"]) => {
    switch (risk) {
      case "critical":
        return "text-red-500 font-bold";
      case "high":
        return "text-orange-500";
      case "medium":
        return "text-yellow-500";
      default:
        return "text-green-500";
    }
  };

  const getKindIcon = (kind: CapabilityRecord["kind"]) => {
    switch (kind) {
      case "connector":
        return Globe;
      case "workflow":
        return GitFork;
      case "swarm":
        return Network;
      default:
        return Wrench;
    }
  };

  return (
    <div className="rounded-lg border border-slate-800 bg-slate-950/40 p-4 font-mono text-[11px]">
      <h3 className="text-xs font-bold tracking-wider text-slate-400 mb-3 uppercase flex items-center gap-2 border-b border-slate-900 pb-2">
        <Wrench className="h-4 w-4 text-cyan-400" />
        Tools & Connectors Catalog
      </h3>

      <div className="overflow-x-auto">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="border-b border-slate-900 text-[10px] text-slate-500 uppercase font-bold">
              <th className="py-2">Tool Name</th>
              <th className="py-2">Kind</th>
              <th className="py-2">Version</th>
              <th className="py-2">Owner</th>
              <th className="py-2 text-center">Status</th>
              <th className="py-2 text-center">Risk Level</th>
              <th className="py-2 text-right">Executions</th>
            </tr>
          </thead>
          <tbody>
            {tools.map((tool) => {
              const active = selectedId === tool.capability_id;
              const Icon = getKindIcon(tool.kind);
              return (
                <tr
                  key={tool.capability_id}
                  onClick={() => onSelect(tool)}
                  className={`border-b border-slate-900/50 cursor-pointer hover:bg-slate-900/30 transition-all ${
                    active ? "bg-cyan-950/20 text-cyan-200 border-l-2 border-l-cyan-500" : "text-slate-300"
                  }`}
                >
                  <td className="py-2.5 font-bold flex items-center gap-1.5 pl-1">
                    <span>{tool.name}</span>
                  </td>
                  <td className="py-2.5 text-slate-400 flex items-center gap-1 mt-0.5">
                    <Icon className="h-3.5 w-3.5 text-slate-500" />
                    <span className="capitalize">{tool.kind}</span>
                  </td>
                  <td className="py-2.5 text-slate-500">{tool.version}</td>
                  <td className="py-2.5 text-slate-400">{tool.owner}</td>
                  <td className={`py-2.5 text-center uppercase font-bold ${getStatusColor(tool.status)}`}>
                    {tool.status}
                  </td>
                  <td className={`py-2.5 text-center uppercase font-bold ${getRiskColor(tool.risk)}`}>
                    {tool.risk}
                  </td>
                  <td className="py-2.5 text-right font-bold text-slate-400">{tool.telemetry.executions_30d}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
