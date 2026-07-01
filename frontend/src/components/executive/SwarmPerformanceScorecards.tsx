import { CheckSquare, BarChart, Users, AlertCircle } from "lucide-react";

export function SwarmPerformanceScorecards() {
  const swarmsData = [
    { name: "Coder Swarm (Alpha)", score: 85, active: 4, tasks: 12, blocked: 2, color: "text-cyan-400" },
    { name: "Audit Swarm", score: 92, active: 3, tasks: 18, blocked: 0, color: "text-green-400" },
    { name: "Guardrail Swarm (Beta)", score: 78, active: 5, tasks: 9, blocked: 3, color: "text-yellow-400" },
    { name: "Intel Swarm", score: 88, active: 2, tasks: 14, blocked: 1, color: "text-cyan-400" }
  ];

  return (
    <div className="rounded-lg border border-slate-800 bg-slate-950/60 p-4 backdrop-blur-md">
      <div className="mb-4 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <BarChart className="h-4 w-4 text-cyan-400" />
          <h3 className="font-mono text-sm font-semibold tracking-wider text-slate-200 uppercase">
            SWARM PERFORMANCE SCORECARDS
          </h3>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 font-mono text-xs">
        {swarmsData.map((sw) => (
          <div key={sw.name} className="rounded border border-slate-900 bg-slate-950/40 p-3 hover:border-slate-800 transition-colors">
            <div className="flex items-center justify-between mb-2">
              <span className="font-bold text-slate-200">{sw.name}</span>
              <span className={`font-bold ${sw.color}`}>{sw.score}/100</span>
            </div>
            
            <div className="grid grid-cols-3 gap-2 text-center text-[10px]">
              <div className="rounded bg-slate-900/60 p-1.5 border border-slate-950">
                <div className="font-bold text-slate-300 flex items-center justify-center gap-1">
                  <Users className="h-3 w-3 text-slate-500" /> {sw.active}
                </div>
                <div className="text-[8px] text-slate-500">ACTIVE</div>
              </div>
              <div className="rounded bg-slate-900/60 p-1.5 border border-slate-950">
                <div className="font-bold text-slate-300 flex items-center justify-center gap-1">
                  <CheckSquare className="h-3 w-3 text-slate-500" /> {sw.tasks}
                </div>
                <div className="text-[8px] text-slate-500">TASKS</div>
              </div>
              <div className="rounded bg-slate-900/60 p-1.5 border border-slate-950">
                <div className={`font-bold flex items-center justify-center gap-1 ${sw.blocked > 0 ? 'text-red-400 font-bold' : 'text-slate-300'}`}>
                  <AlertCircle className="h-3 w-3 text-slate-500" /> {sw.blocked}
                </div>
                <div className="text-[8px] text-slate-500">BLOCKED</div>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
