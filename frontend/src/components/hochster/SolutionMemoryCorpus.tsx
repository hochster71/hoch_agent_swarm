import React, { useState } from "react";
import { Search } from "lucide-react";
import type { SolutionMemoryRecord } from "../../lib/hochster/hochsterTypes";

interface SolutionMemoryCorpusProps {
  records: SolutionMemoryRecord[];
}

export const SolutionMemoryCorpus: React.FC<SolutionMemoryCorpusProps> = ({ records }) => {
  const [query, setQuery] = useState("");

  const filtered = records.filter(r =>
    r.solution.root_cause.toLowerCase().includes(query.toLowerCase()) ||
    r.solution.patch_summary.toLowerCase().includes(query.toLowerCase()) ||
    r.problem_signature.problem_type.toLowerCase().includes(query.toLowerCase())
  );

  return (
    <div className="glass-panel p-4 rounded-xl border border-white/10 bg-white/2 space-y-4 text-left">
      <div className="flex items-center justify-between">
        <h4 className="text-xs font-bold text-slate-300 uppercase tracking-wider">Solution Memory Corpus</h4>
        <span className="text-[9px] text-blue-400 cursor-pointer hover:underline">View Full Corpus</span>
      </div>

      {/* Search Input */}
      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-slate-400" />
        <input
          type="text"
          placeholder="Search prior solution patterns..."
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          className="w-full bg-white/5 border border-white/10 rounded-lg pl-9 pr-4 py-1.5 text-xs text-white focus:outline-none focus:border-blue-500"
        />
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="border-b border-white/5 text-[9px] uppercase text-slate-400 font-bold">
              <th className="py-2">Match</th>
              <th className="py-2">Problem Signature</th>
              <th className="py-2">Solution Summary</th>
              <th className="py-2">Confidence</th>
              <th className="py-2 text-right">Age</th>
            </tr>
          </thead>
          <tbody>
            {filtered.map((r, idx) => (
              <tr key={r.memory_id} className="border-b border-white/5 hover:bg-white/5 transition text-xs">
                <td className="py-2 text-green-400 font-bold">{98 - idx * 6}%</td>
                <td className="py-2">
                  <div className="font-semibold text-white capitalize">{r.problem_signature.problem_type.replace(/_/g, " ")}</div>
                  <div className="text-[10px] text-slate-400 font-mono">{r.scope.repository}</div>
                </td>
                <td className="py-2 text-slate-300 max-w-[150px] truncate">{r.solution.root_cause}</td>
                <td className="py-2 font-semibold text-slate-200">{(r.solution.confidence).toFixed(2)}</td>
                <td className="py-2 text-right text-slate-400 text-[10px]">2 days ago</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};
