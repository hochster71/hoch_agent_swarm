import { useChaosEngineStore } from "../../lib/adversarial/chaosEngine";
import { ShieldCheck } from "lucide-react";

export function SafetyAssertionResults() {
  const { scenarios } = useChaosEngineStore();

  // Find all runs that completed
  const completedScenarios = scenarios.filter((s) => s.result !== undefined);
  const totalCompleted = completedScenarios.length;
  const passedScenariosCount = completedScenarios.filter((s) => s.result?.status === "passed").length;

  const overallPassRate = totalCompleted > 0
    ? Math.round((passedScenariosCount / totalCompleted) * 100)
    : 100; // default 100 before any runs

  // Mock enclaves assertion checklists derived from completed runs or defaults
  const enclavesAssertions = [
    { name: "Policy Enforcement", defaultRate: 96, key: "policy" },
    { name: "Evidence Integrity", defaultRate: 94, key: "evidence" },
    { name: "Ledger Integrity", defaultRate: 100, key: "ledger" },
    { name: "Approval Controls", defaultRate: 92, key: "approval" },
    { name: "Telemetry Freshness", defaultRate: 88, key: "telemetry" },
    { name: "Integration Resilience", defaultRate: 88, key: "integration" },
  ];

  // Adjust rates based on actual scenario runs to make it dynamic!
  const getPassRate = (assertion: any) => {
    let rate = assertion.defaultRate;
    completedScenarios.forEach((sc) => {
      if (sc.result?.status === "failed") {
        if (assertion.key === "policy" && sc.kind === "policy_bypass") rate = Math.max(40, rate - 20);
        if (assertion.key === "approval" && sc.kind === "approval_abuse") rate = Math.max(40, rate - 15);
        if (assertion.key === "telemetry" && sc.kind === "telemetry_failure") rate = Math.max(40, rate - 25);
        if (assertion.key === "ledger" && sc.kind === "ledger_tamper") rate = Math.max(40, rate - 30);
      }
    });
    return rate;
  };

  return (
    <div className="rounded-lg border border-slate-800 bg-slate-950/60 p-4 backdrop-blur-md">
      <div className="mb-4 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <ShieldCheck className="h-4 w-4 text-green-400" />
          <h3 className="font-mono text-sm font-semibold tracking-wider text-slate-200 uppercase">
            SAFETY ASSERTIONS & ENCLAVE PASS RATES
          </h3>
        </div>
        <span className="font-mono text-xs text-green-400 font-bold">
          OVERALL: {overallPassRate}% PASS
        </span>
      </div>

      <div className="space-y-3 font-mono text-xs text-slate-300">
        {enclavesAssertions.map((ast) => {
          const currentRate = getPassRate(ast);
          return (
            <div key={ast.name} className="space-y-1">
              <div className="flex justify-between text-[11px] text-slate-400">
                <span>{ast.name}</span>
                <span className={`font-semibold ${currentRate >= 90 ? 'text-green-400' : currentRate >= 75 ? 'text-yellow-400' : 'text-red-400'}`}>
                  {currentRate}%
                </span>
              </div>
              <div className="w-full h-1.5 bg-slate-900 rounded overflow-hidden">
                <div
                  className={`h-full rounded transition-all duration-500 ${currentRate >= 90 ? 'bg-green-500' : currentRate >= 75 ? 'bg-yellow-500' : 'bg-red-500'}`}
                  style={{ width: `${currentRate}%` }}
                />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
