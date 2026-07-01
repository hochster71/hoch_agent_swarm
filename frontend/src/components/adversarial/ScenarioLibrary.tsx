import { useChaosEngineStore } from "../../lib/adversarial/chaosEngine";
import { Play, CheckCircle, AlertOctagon } from "lucide-react";

export function ScenarioLibrary() {
  const { scenarios, runScenario } = useChaosEngineStore();

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "passed":
        return <span className="status-badge success flex items-center gap-1"><CheckCircle className="h-3 w-3" /> PASSED</span>;
      case "failed":
        return <span className="status-badge fail flex items-center gap-1"><AlertOctagon className="h-3 w-3" /> FAILED</span>;
      case "warning":
        return <span className="status-badge warn flex items-center gap-1"><AlertOctagon className="h-3 w-3" /> WARNING</span>;
      default:
        return <span className="status-badge blocked">NOT RUN</span>;
    }
  };

  const getSeverityStyle = (severity: string) => {
    switch (severity) {
      case "critical":
        return "text-red-500 font-bold border-red-500/20 bg-red-500/10";
      case "high":
        return "text-orange-500 font-bold border-orange-500/20 bg-orange-500/10";
      case "medium":
        return "text-yellow-500 font-bold border-yellow-500/20 bg-yellow-500/10";
      default:
        return "text-green-500 font-bold border-green-500/20 bg-green-500/10";
    }
  };

  return (
    <div className="rounded-lg border border-slate-800 bg-slate-950/60 p-4 backdrop-blur-md">
      <div className="mb-4 flex items-center justify-between">
        <h3 className="font-mono text-sm font-semibold tracking-wider text-slate-200 uppercase">
          RED-TEAM SCENARIO LIBRARY
        </h3>
      </div>

      <div className="space-y-4 max-h-[480px] overflow-y-auto pr-1">
        {scenarios.map((sc) => (
          <div
            key={sc.scenario_id}
            className="rounded border border-slate-900 bg-slate-950/40 p-4 hover:border-slate-800 transition-all flex flex-col justify-between"
          >
            <div>
              <div className="flex items-start justify-between mb-2">
                <div>
                  <h4 className="font-bold text-slate-200 text-sm leading-tight">{sc.name}</h4>
                  <span className="text-[10px] text-slate-500 font-mono">ID: {sc.scenario_id} &bull; Type: {sc.kind.replace(/_/g, " ")}</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className={`rounded border px-2 py-0.5 text-[9px] font-bold uppercase ${getSeverityStyle(sc.severity)}`}>
                    {sc.severity}
                  </span>
                  {getStatusBadge(sc.result?.status || "not_run")}
                </div>
              </div>

              <p className="text-[11px] text-slate-400 font-mono mb-3 leading-relaxed">
                {sc.description}
              </p>

              {sc.setup.input_payload && (
                <div className="mb-3 rounded bg-slate-900/60 p-2 border border-slate-900 font-mono text-[10px] text-slate-400">
                  <span className="text-cyan-500 font-semibold">Payload:</span>{" "}
                  <code className="text-slate-200">{sc.setup.input_payload}</code>
                </div>
              )}

              {/* Assertions check */}
              <div className="space-y-1 mb-3">
                <span className="text-[9px] text-slate-500 font-semibold uppercase tracking-wider">Expected Safety Assertions:</span>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-1.5 font-mono text-[10px]">
                  {sc.assertions.map((ast) => {
                    const isFailed = sc.result?.failed_assertions.includes(ast.assertion_id);
                    const isRun = sc.result !== undefined;

                    return (
                      <div
                        key={ast.assertion_id}
                        className={`rounded px-2 py-1 flex items-center justify-between border ${isRun ? (isFailed ? 'border-red-500/20 bg-red-500/5 text-red-400' : 'border-green-500/20 bg-green-500/5 text-green-400') : 'border-slate-900 bg-slate-950/20 text-slate-500'}`}
                      >
                        <span className="truncate">{ast.description}</span>
                        <span className="font-bold font-mono text-[9px] tracking-wider uppercase ml-2 flex-shrink-0">
                          {isRun ? (isFailed ? "FAIL" : "PASS") : "PENDING"}
                        </span>
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>

            {sc.result?.findings && (
              <div className="mt-2 border-t border-slate-900 pt-2 font-mono text-[10px]">
                <span className="text-slate-500 font-semibold block mb-1">DRILL FINDINGS:</span>
                <ul className="list-disc list-inside space-y-1 text-slate-400 pl-1">
                  {sc.result.findings.map((f, idx) => (
                    <li key={idx}>{f}</li>
                  ))}
                </ul>
              </div>
            )}

            <div className="flex justify-end pt-3 border-t border-slate-900/60 mt-3">
              <button
                onClick={() => runScenario(sc.scenario_id)}
                className="flex items-center gap-1 rounded bg-cyan-500 hover:bg-cyan-600 px-3 py-1 text-xs font-semibold font-mono text-slate-950 transition-colors"
              >
                <Play className="h-3 w-3 fill-current" />
                EXECUTE DRILL
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
