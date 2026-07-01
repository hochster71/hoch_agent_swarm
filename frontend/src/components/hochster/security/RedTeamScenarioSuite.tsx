import React from "react";
import { CheckCircle2, ShieldAlert } from "lucide-react";

export const RedTeamScenarioSuite: React.FC = () => {
  const scenarios = [
    { id: "sc-001", name: "Sandbox Escape Attempts", attempts: 14, blocked: 14, score: 0, status: "Passed" },
    { id: "sc-002", name: "Prompt Injection Attacks", attempts: 21, blocked: 19, score: 2, status: "Passed" },
    { id: "sc-003", name: "Tool Poisoning Tests", attempts: 18, blocked: 16, score: 2, status: "Passed" },
    { id: "sc-004", name: "Secret Leakage Tests", attempts: 16, blocked: 16, score: 0, status: "Passed" },
    { id: "sc-005", name: "MCP Manifest Abuse", attempts: 15, blocked: 14, score: 1, status: "Passed" },
    { id: "sc-006", name: "Policy Bypass Attempts", attempts: 17, blocked: 16, score: 1, status: "Passed" },
    { id: "sc-007", name: "Resource Exhaustion", attempts: 10, blocked: 10, score: 0, status: "Passed" },
    { id: "sc-008", name: "Data Exfiltration Attempts", attempts: 15, blocked: 15, score: 0, status: "Passed" }
  ];

  return (
    <div className="glass-panel p-4 rounded-xl border border-white/10 bg-white/2 space-y-4 text-left">
      <div className="flex items-center justify-between">
        <h4 className="text-xs font-bold text-slate-300 uppercase tracking-wider">Red-Team Scenario Suite</h4>
        <span className="text-[10px] text-blue-400 cursor-pointer hover:underline">View All Scenarios</span>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="border-b border-white/5 text-[9px] uppercase text-slate-400 font-bold">
              <th className="py-2">Scenario</th>
              <th className="py-2">Attempts</th>
              <th className="py-2">Blocked</th>
              <th className="py-2">Score</th>
              <th className="py-2 text-right">Status</th>
            </tr>
          </thead>
          <tbody>
            {scenarios.map((s) => (
              <tr key={s.id} className="border-b border-white/5 hover:bg-white/5 transition text-xs">
                <td className="py-2 font-semibold text-white">{s.name}</td>
                <td className="py-2 font-mono text-slate-300">{s.attempts}</td>
                <td className="py-2 font-mono text-slate-300">{s.blocked}</td>
                <td className="py-2 font-mono text-yellow-400">{s.score}</td>
                <td className="py-2 text-right">
                  <span className="text-[10px] px-1.5 py-0.5 rounded bg-green-500/10 text-green-400 font-semibold flex items-center justify-end gap-1">
                    <CheckCircle2 className="w-3 h-3 text-green-400" />
                    Passed
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
