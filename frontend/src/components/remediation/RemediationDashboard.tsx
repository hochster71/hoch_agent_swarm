import { useState } from "react";
import { useRemediationStore } from "../../lib/remediation/remediationEngine";
import type { Runbook } from "../../lib/remediation/runbookTypes";
import { RunbookRegistry } from "./RunbookRegistry";
import { RunbookDetailPanel } from "./RunbookDetailPanel";
import { RemediationRecommendationList } from "./RemediationRecommendationList";
import { RunbookSimulationPanel } from "./RunbookSimulationPanel";
import { RunbookExecutionTimeline } from "./RunbookExecutionTimeline";
import { RollbackPlanPanel } from "./RollbackPlanPanel";
import { OutcomeVerificationPanel } from "./OutcomeVerificationPanel";
import { RemediationEvidenceExport } from "./RemediationEvidenceExport";
import { useAuditStore } from "../../lib/audit/auditStore";
import {
  Wrench,
  AlertTriangle,
  PlayCircle,
  Clock,
  CheckCircle,
  FileText,
  Activity,
  History
} from "lucide-react";

export function RemediationDashboard() {
  const { runbooks, executions } = useRemediationStore();
  const { events } = useAuditStore();
  
  const [selectedRb, setSelectedRb] = useState<Runbook | null>(runbooks[0] || null);
  const [simulatingRb, setSimulatingRb] = useState<Runbook | null>(null);

  // Statistics summaries
  const totalExecs = executions.length;
  const activeIncidentsCount = 14; 
  const pendingActionsCount = 24;
  const successfulRunsCount = 186;
  const mttrValue = "2.4h";

  // Filter audit events
  const remediationEvents = events.filter((e) => 
    e.action.type.startsWith("RUNBOOK_") || e.action.type === "REMEDIATION_VERIFIED"
  ).slice(0, 5);

  return (
    <div className="p-6 space-y-6 max-h-[calc(100vh-120px)] overflow-y-auto w-full text-slate-200">
      
      {/* View Header */}
      <div className="flex items-center justify-between border-b border-slate-900 pb-3">
        <div>
          <div className="flex items-center gap-2">
            <span className="bg-purple-950 border border-purple-800 text-purple-400 text-[10px] font-bold px-2 py-0.5 rounded font-mono">PHASE 17</span>
            <h1 className="text-xl font-bold tracking-wider font-mono text-slate-100 flex items-center gap-2">
              <Wrench className="h-5 w-5 text-cyan-400" />
              Autonomous Remediation, Runbooks & Closed-Loop Recovery
            </h1>
          </div>
          <p className="text-xs text-slate-500 font-mono mt-1">
            From detection to recovery: simulate, approve, execute, verify, and learn.
          </p>
        </div>
        <div>
          <span className="bg-emerald-950/40 border border-emerald-800/40 text-emerald-400 text-[10px] font-mono px-2 py-1 rounded font-bold uppercase animate-pulse">
            Remediation Engine: Active
          </span>
        </div>
      </div>

      {/* Remediation Overview Cards Grid */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 font-mono text-xs">
        <div className="rounded-lg border border-slate-800 bg-slate-950/40 p-4">
          <div className="flex items-center justify-between text-slate-500">
            <span>ACTIVE INCIDENTS</span>
            <AlertTriangle className="h-4 w-4 text-red-500" />
          </div>
          <div className="text-2xl font-bold text-slate-200 mt-2">{activeIncidentsCount}</div>
          <div className="text-[9px] text-red-400 mt-1">▲ +3 this week</div>
        </div>

        <div className="rounded-lg border border-slate-800 bg-slate-950/40 p-4">
          <div className="flex items-center justify-between text-slate-500">
            <span>PENDING ACTIONS</span>
            <Clock className="h-4 w-4 text-yellow-500" />
          </div>
          <div className="text-2xl font-bold text-slate-200 mt-2">{pendingActionsCount}</div>
          <div className="text-[9px] text-yellow-400 mt-1">◈ +5 this week</div>
        </div>

        <div className="rounded-lg border border-slate-800 bg-slate-950/40 p-4">
          <div className="flex items-center justify-between text-slate-500">
            <span>SUCCESSFUL RUNS (30d)</span>
            <CheckCircle className="h-4 w-4 text-green-500" />
          </div>
          <div className="text-2xl font-bold text-green-400 mt-2">{successfulRunsCount}</div>
          <div className="text-[9px] text-slate-600 mt-1">92% success rate</div>
        </div>

        <div className="rounded-lg border border-slate-800 bg-slate-950/40 p-4">
          <div className="flex items-center justify-between text-slate-500">
            <span>MTTR (30d)</span>
            <Activity className="h-4 w-4 text-cyan-500" />
          </div>
          <div className="text-2xl font-bold text-cyan-400 mt-2">{mttrValue}</div>
          <div className="text-[9px] text-green-400 mt-1">▼ -18% average time</div>
        </div>
      </div>

      {/* Main Column Grid */}
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
        
        {/* Left Column: Recommendations + Library */}
        <div className="space-y-6">
          <RemediationRecommendationList onSimulate={(rb) => { setSimulatingRb(rb); setSelectedRb(rb); }} />
          <RunbookRegistry onSelect={(rb) => setSelectedRb(rb)} selectedId={selectedRb?.runbook_id} />
        </div>

        {/* Center Column: Details, Simulation, Timeline */}
        <div className="space-y-6">
          
          {selectedRb && (
            <RunbookDetailPanel runbook={selectedRb} onSimulate={() => setSimulatingRb(selectedRb)} />
          )}

          {simulatingRb && (
            <RunbookSimulationPanel runbook={simulatingRb} onClose={() => setSimulatingRb(null)} />
          )}

          <RunbookExecutionTimeline />
          <RollbackPlanPanel />
        </div>

        {/* Right Column: Outcomes, Metrics, Audits, Evidences */}
        <div className="space-y-6">
          <OutcomeVerificationPanel />
          <RemediationEvidenceExport />

          {/* Recent Remediation Events Audit log */}
          <div className="rounded-lg border border-slate-800 bg-slate-950/40 p-4 font-mono text-[11px] space-y-3">
            <h3 className="text-xs font-bold tracking-wider text-slate-400 uppercase border-b border-slate-900 pb-2 flex items-center gap-1.5">
              <History className="h-4 w-4 text-cyan-400" />
              Recent Remediation Events
            </h3>
            <div className="space-y-2 max-h-[180px] overflow-y-auto pr-1">
              {remediationEvents.length === 0 ? (
                <div className="text-slate-600 italic">No remediation events logged.</div>
              ) : (
                remediationEvents.map((evt, idx) => (
                  <div key={idx} className="p-2 bg-slate-900/20 border border-slate-900/40 rounded flex flex-col gap-1">
                    <div className="flex justify-between items-center text-[9px]">
                      <span className="text-cyan-400 font-bold uppercase">{evt.action.type.replace("RUNBOOK_", "")}</span>
                      <span className="text-slate-500">{new Date(evt.timestamp).toLocaleTimeString()}</span>
                    </div>
                    <span className="text-slate-300 text-[10px]">{evt.action.summary}</span>
                  </div>
                ))
              )}
            </div>
          </div>

          {/* Implementation plan markdown notes */}
          <div className="rounded-lg border border-slate-800 bg-slate-950/40 p-4 font-mono text-[11px] space-y-2">
            <h3 className="text-xs font-bold tracking-wider text-slate-400 uppercase border-b border-slate-900 pb-2 flex items-center gap-1">
              <FileText className="h-4 w-4 text-cyan-400" />
              Remediation Swarm Notes
            </h3>
            <div className="text-slate-500 space-y-2 leading-relaxed">
              <div>
                <span className="font-bold text-slate-400">Doctrine:</span> Autonomous remediation must be simulated, approved, executed through runbooks, verified, reversible, and logged.
              </div>
              <div>
                <span className="font-bold text-slate-400">Security Gate:</span> Dual-operator approval is strictly triggered on critical risk configurations.
              </div>
            </div>
          </div>

        </div>

      </div>

    </div>
  );
}
