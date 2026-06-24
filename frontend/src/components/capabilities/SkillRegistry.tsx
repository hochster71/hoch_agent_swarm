import { useCapabilityRegistryStore } from "../../lib/capabilities/capabilityRegistry";
import type { CapabilityRecord } from "../../lib/capabilities/capabilityTypes";
import { Hammer, Settings } from "lucide-react";

type Props = {
  onSelect: (cap: CapabilityRecord) => void;
  selectedId?: string;
};

export function SkillRegistry({ onSelect, selectedId }: Props) {
  const { capabilities } = useCapabilityRegistryStore();

  const skills = capabilities.filter((c) => c.kind === "skill");

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

  return (
    <div className="rounded-lg border border-slate-800 bg-slate-950/40 p-4 font-mono text-[11px]">
      <h3 className="text-xs font-bold tracking-wider text-slate-400 mb-3 uppercase flex items-center gap-2 border-b border-slate-900 pb-2">
        <Hammer className="h-4 w-4 text-cyan-400" />
        Swarm Skill Registry
      </h3>

      <div className="overflow-x-auto">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="border-b border-slate-900 text-[10px] text-slate-500 uppercase font-bold">
              <th className="py-2">Skill Name</th>
              <th className="py-2">Version</th>
              <th className="py-2">Owner</th>
              <th className="py-2 text-center">Status</th>
              <th className="py-2 text-center">Risk Level</th>
              <th className="py-2 text-right">Executions</th>
            </tr>
          </thead>
          <tbody>
            {skills.map((skill) => {
              const active = selectedId === skill.capability_id;
              return (
                <tr
                  key={skill.capability_id}
                  onClick={() => onSelect(skill)}
                  className={`border-b border-slate-900/50 cursor-pointer hover:bg-slate-900/30 transition-all ${
                    active ? "bg-cyan-950/20 text-cyan-200 border-l-2 border-l-cyan-500" : "text-slate-300"
                  }`}
                >
                  <td className="py-2.5 font-bold flex items-center gap-1.5 pl-1">
                    <span>{skill.name}</span>
                  </td>
                  <td className="py-2.5 text-slate-500">{skill.version}</td>
                  <td className="py-2.5 text-slate-400">{skill.owner}</td>
                  <td className={`py-2.5 text-center uppercase font-bold ${getStatusColor(skill.status)}`}>
                    {skill.status}
                  </td>
                  <td className={`py-2.5 text-center uppercase font-bold ${getRiskColor(skill.risk)}`}>
                    {skill.risk}
                  </td>
                  <td className="py-2.5 text-right font-bold text-slate-400">{skill.telemetry.executions_30d}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
