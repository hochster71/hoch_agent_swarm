import React, { useState } from "react";
import {
  Users,
  Activity,
  Heart,
  AlertOctagon,
  TrendingUp,
  DollarSign,
  Ticket,
  Calendar,
  CheckCircle,
  HelpCircle,
  BarChart,
  ClipboardList,
  Sparkles,
  Download
} from "lucide-react";
import { initialCustomers } from "../../lib/customer-success/customerFixtures";
import { CustomerRecord, OnboardingTask } from "../../lib/customer-success/customerTypes";

export const CustomerSuccessDashboard: React.FC = () => {
  const [customers, setCustomers] = useState<CustomerRecord[]>(initialCustomers);
  const [selectedCustomerId, setSelectedCustomerId] = useState<string>("cust-02");

  // Scheduling states
  const [checkInDate, setCheckInDate] = useState("");
  const [checkInObjective, setCheckInObjective] = useState("");
  const [scheduledAlert, setScheduledAlert] = useState<string | null>(null);

  const currentCustomer = customers.find(c => c.customer_id === selectedCustomerId) || customers[0];

  const handleToggleTask = (taskId: string) => {
    setCustomers(prevCustomers =>
      prevCustomers.map(cust => {
        if (cust.customer_id === selectedCustomerId) {
          const updatedChecklist = cust.onboarding_checklist.map(t => {
            if (t.task_id === taskId) {
              return {
                ...t,
                completed: !t.completed,
                completed_at: !t.completed ? new Date().toISOString() : undefined
              };
            }
            return t;
          });

          const completedCount = updatedChecklist.filter(t => t.completed).length;
          const progressPercent = Math.round((completedCount / updatedChecklist.length) * 100);

          // If onboarding progress changes, recalculate risk score
          let riskScore = cust.churn_risk_score;
          let riskReasons = [...cust.churn_risk_reasons];

          if (progressPercent >= 75) {
            riskReasons = riskReasons.filter(r => r !== "Incomplete onboarding integration");
            if (riskReasons.length === 0) riskScore = Math.max(10, riskScore - 20);
          } else {
            if (!riskReasons.includes("Incomplete onboarding integration")) {
              riskReasons.push("Incomplete onboarding integration");
              riskScore = Math.min(95, riskScore + 20);
            }
          }

          // Trigger audit
          if (window.addAuditEvent) {
            window.addAuditEvent({
              actor: { id: "op-mh-99", name: "Michael Hoch", type: "human", role: "Customer Success Manager" },
              action: { type: "CUSTOMER_ONBOARDING_TASK_COMPLETED", summary: `Toggled onboarding task for ${cust.company_name}` },
              target: { type: "task", id: taskId, name: `Task: ${taskId}` },
              result: "success",
              severity: "info",
              provenance: { source: "manual", evidence_refs: [] },
              policy: { required: false, result: "passed" }
            });
          }

          return {
            ...cust,
            onboarding_checklist: updatedChecklist,
            onboarding_progress_percent: progressPercent,
            churn_risk_score: riskScore,
            churn_risk_reasons: riskReasons
          };
        }
        return cust;
      })
    );
  };

  const handleScheduleCheckIn = (e: React.FormEvent) => {
    e.preventDefault();
    if (!checkInDate || !checkInObjective) return;

    setScheduledAlert(`Successfully scheduled check-in for ${currentCustomer.company_name} on ${checkInDate}`);

    if (window.addAuditEvent) {
      window.addAuditEvent({
        actor: { id: "op-mh-99", name: "Michael Hoch", type: "human", role: "Customer Success Manager" },
        action: { type: "CUSTOMER_CHECKIN_SCHEDULED", summary: `Scheduled customer check-in on ${checkInDate} - Obj: ${checkInObjective}` },
        target: { type: "swarm", id: selectedCustomerId, name: currentCustomer.company_name },
        result: "success",
        severity: "info",
        provenance: { source: "manual", evidence_refs: [] },
        policy: { required: false, result: "passed" }
      });
    }

    setCheckInDate("");
    setCheckInObjective("");
    setTimeout(() => setScheduledAlert(null), 5000);
  };

  const handleExportCSReport = () => {
    const report = {
      customer: currentCustomer,
      timestamp: new Date().toISOString(),
      generated_by: "Michael Hoch (CS Manager)"
    };

    const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(report, null, 2));
    const dlAnchor = document.createElement("a");
    dlAnchor.setAttribute("href", dataStr);
    dlAnchor.setAttribute("download", `${currentCustomer.company_name.replace(/\s+/g, "_")}_success_metrics.json`);
    document.body.appendChild(dlAnchor);
    dlAnchor.click();
    dlAnchor.remove();

    if (window.addAuditEvent) {
      window.addAuditEvent({
        actor: { id: "op-mh-99", name: "Michael Hoch", type: "human", role: "Customer Success Manager" },
        action: { type: "CUSTOMER_REPORT_EXPORTED", summary: `Customer success & outcomes report exported for ${currentCustomer.company_name}` },
        target: { type: "swarm", id: selectedCustomerId, name: currentCustomer.company_name },
        result: "success",
        severity: "info",
        provenance: { source: "manual", evidence_refs: [] },
        policy: { required: false, result: "passed" }
      });
    }
  };

  return (
    <div className="glass-panel p-6 rounded-2xl border border-white/10 text-white space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 border-b border-white/10 pb-5">
        <div>
          <div className="flex items-center gap-2">
            <Users className="w-8 h-8 text-emerald-400" />
            <h2 className="text-2xl font-bold tracking-tight">Customer Success &amp; Adoption Hub</h2>
          </div>
          <p className="text-slate-400 text-sm mt-1">
            Track customer onboarding completion checklists, active adoption telemetry, support metrics, and churn risk scoring.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <select
            value={selectedCustomerId}
            onChange={e => setSelectedCustomerId(e.target.value)}
            className="bg-white/5 border border-white/10 text-white rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-emerald-500"
          >
            {customers.map(c => (
              <option key={c.customer_id} value={c.customer_id} className="bg-slate-900 text-white">
                {c.company_name} ({c.lifecycle_stage.replace("_", " ")})
              </option>
            ))}
          </select>
          <button
            onClick={handleExportCSReport}
            className="flex items-center gap-2 px-4 py-2 bg-emerald-600 hover:bg-emerald-500 transition rounded-lg text-sm font-medium active:scale-95"
          >
            <Download className="w-4 h-4" /> Export success profile
          </button>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-4">
        {/* Active users */}
        <div className="glass-panel p-4 rounded-xl border border-white/5 bg-white/2 space-y-1">
          <div className="flex justify-between items-center text-slate-400">
            <span className="text-xs uppercase font-bold tracking-wider">Active Users</span>
            <Users className="w-4 h-4 text-blue-400" />
          </div>
          <div className="text-2xl font-bold">{currentCustomer.active_users}</div>
          <p className="text-[10px] text-slate-400">Across {currentCustomer.agent_pools_count} active agent pools</p>
        </div>

        {/* SLA health */}
        <div className="glass-panel p-4 rounded-xl border border-white/5 bg-white/2 space-y-1">
          <div className="flex justify-between items-center text-slate-400">
            <span className="text-xs uppercase font-bold tracking-wider">SLA Performance</span>
            <Activity className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="text-2xl font-bold">{currentCustomer.sla_actual_percent}%</div>
          <p className="text-[10px] text-slate-400">Target: {currentCustomer.sla_target_percent}%</p>
        </div>

        {/* Automations triggered */}
        <div className="glass-panel p-4 rounded-xl border border-white/5 bg-white/2 space-y-1">
          <div className="flex justify-between items-center text-slate-400">
            <span className="text-xs uppercase font-bold tracking-wider">Automations (24h)</span>
            <Sparkles className="w-4 h-4 text-yellow-400" />
          </div>
          <div className="text-2xl font-bold">{currentCustomer.automations_triggered_24h}</div>
          <p className="text-[10px] text-slate-400">Runs executed inside sandbox</p>
        </div>

        {/* Deployment health */}
        <div className="glass-panel p-4 rounded-xl border border-white/5 bg-white/2 space-y-1">
          <div className="flex justify-between items-center text-slate-400">
            <span className="text-xs uppercase font-bold tracking-wider">Deployment Health</span>
            <Heart className="w-4 h-4 text-red-400" />
          </div>
          <div className="flex items-center gap-1.5 mt-1">
            <span
              className={`w-2.5 h-2.5 rounded-full ${
                currentCustomer.deployment_health === "healthy"
                  ? "bg-green-400 animate-pulse"
                  : currentCustomer.deployment_health === "degraded"
                  ? "bg-yellow-400"
                  : "bg-red-500 animate-ping"
              }`}
            ></span>
            <span className="text-lg font-bold capitalize">{currentCustomer.deployment_health}</span>
          </div>
          <p className="text-[10px] text-slate-400">Tenant: {currentCustomer.tenant_id}</p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Onboarding Checklist */}
        <div className="glass-panel p-5 rounded-xl border border-white/10 bg-white/2 space-y-4">
          <div className="flex justify-between items-center">
            <h3 className="text-lg font-bold flex items-center gap-2">
              <ClipboardList className="w-5 h-5 text-emerald-400" /> Onboarding Checklist
            </h3>
            <span className="text-sm font-semibold text-emerald-400">
              {currentCustomer.onboarding_progress_percent}% Complete
            </span>
          </div>

          <div className="w-full bg-white/10 h-2 rounded-full overflow-hidden">
            <div
              className="bg-emerald-400 h-full transition-all duration-500"
              style={{ width: `${currentCustomer.onboarding_progress_percent}%` }}
            ></div>
          </div>

          <div className="space-y-2 mt-4">
            {currentCustomer.onboarding_checklist.map(task => (
              <div
                key={task.task_id}
                onClick={() => handleToggleTask(task.task_id)}
                className="flex items-center justify-between p-3 rounded-lg bg-white/5 border border-white/5 hover:bg-white/10 cursor-pointer transition"
              >
                <div className="flex items-center gap-3">
                  <input
                    type="checkbox"
                    checked={task.completed}
                    onChange={() => {}} // handled by div click
                    className="rounded border-white/20 text-emerald-500 focus:ring-0 cursor-pointer"
                  />
                  <span className={`text-sm ${task.completed ? "line-through text-slate-500" : "text-white"}`}>
                    {task.title}
                  </span>
                </div>
                {task.completed && task.completed_at && (
                  <span className="text-[10px] text-slate-400">
                    Done: {new Date(task.completed_at).toLocaleDateString()}
                  </span>
                )}
              </div>
            ))}
          </div>
        </div>

        {/* Churn Risk & Outcomes */}
        <div className="space-y-6">
          <div className="glass-panel p-5 rounded-xl border border-white/10 bg-white/2 space-y-4">
            <h3 className="text-lg font-bold flex items-center gap-2">
              <AlertOctagon className="w-5 h-5 text-yellow-400" /> Churn Risk Assessment
            </h3>

            <div className="flex justify-between items-center">
              <span className="text-sm text-slate-400">Calculated Risk Index:</span>
              <span
                className={`text-lg font-bold px-3 py-1 rounded-full ${
                  currentCustomer.churn_risk_score >= 70
                    ? "bg-red-500/20 text-red-400"
                    : currentCustomer.churn_risk_score >= 30
                    ? "bg-yellow-500/20 text-yellow-400"
                    : "bg-green-500/20 text-green-400"
                }`}
              >
                {currentCustomer.churn_risk_score} / 100
              </span>
            </div>

            <div className="w-full bg-white/10 h-2 rounded-full overflow-hidden">
              <div
                className={`h-full transition-all duration-500 ${
                  currentCustomer.churn_risk_score >= 70
                    ? "bg-red-500"
                    : currentCustomer.churn_risk_score >= 30
                    ? "bg-yellow-500"
                    : "bg-green-500"
                }`}
                style={{ width: `${currentCustomer.churn_risk_score}%` }}
              ></div>
            </div>

            {currentCustomer.churn_risk_reasons.length > 0 ? (
              <div className="space-y-2 mt-2">
                <span className="text-xs font-semibold text-slate-400 uppercase">Risk Flag Reasons:</span>
                <ul className="list-disc pl-5 text-xs text-red-300 space-y-1">
                  {currentCustomer.churn_risk_reasons.map((reason, index) => (
                    <li key={index}>{reason}</li>
                  ))}
                </ul>
              </div>
            ) : (
              <p className="text-xs text-green-400">Customer exhibits optimal usage signals. Minimal churn risk detected.</p>
            )}
          </div>

          <div className="grid grid-cols-2 gap-4">
            {/* Efficiency improvement */}
            <div className="glass-panel p-4 rounded-xl border border-white/5 bg-white/2 space-y-1">
              <div className="flex justify-between items-center text-slate-400">
                <span className="text-xs uppercase font-bold tracking-wider">Swarm ROI</span>
                <TrendingUp className="w-4 h-4 text-emerald-400" />
              </div>
              <div className="text-2xl font-bold">+{currentCustomer.efficiency_improved_percent}%</div>
              <p className="text-[10px] text-slate-400">Task speed improvement</p>
            </div>

            {/* Cost saved */}
            <div className="glass-panel p-4 rounded-xl border border-white/5 bg-white/2 space-y-1">
              <div className="flex justify-between items-center text-slate-400">
                <span className="text-xs uppercase font-bold tracking-wider">Costs Saved</span>
                <DollarSign className="w-4 h-4 text-blue-400" />
              </div>
              <div className="text-2xl font-bold">${currentCustomer.cost_saved_usd.toLocaleString()}</div>
              <p className="text-[10px] text-slate-400">Net platform margins saved</p>
            </div>
          </div>
        </div>
      </div>

      {/* Support and Scheduler Section */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Open tickets */}
        <div className="glass-panel p-5 rounded-xl border border-white/10 bg-white/2 space-y-4">
          <h3 className="text-lg font-bold flex items-center gap-2">
            <Ticket className="w-5 h-5 text-blue-400" /> Support Desk Telemetry
          </h3>

          <div className="grid grid-cols-2 gap-4 border-b border-white/5 pb-4">
            <div>
              <div className="text-xs text-slate-400">Open Tickets</div>
              <div className="text-2xl font-bold text-red-400">{currentCustomer.support_tickets_open}</div>
            </div>
            <div>
              <div className="text-xs text-slate-400">Avg Response Time</div>
              <div className="text-2xl font-bold text-white">{currentCustomer.avg_ticket_response_minutes} min</div>
            </div>
          </div>

          <div className="text-xs text-slate-400 space-y-2">
            <span className="font-bold uppercase tracking-wider text-[10px]">Active Customer Desk Log:</span>
            <div className="p-3 bg-white/2 rounded border border-white/5">
              <div className="flex justify-between">
                <span className="font-semibold text-white">#TICKET-4481: Degraded node cluster lag</span>
                <span className="text-red-400 text-[10px] font-bold">CRITICAL</span>
              </div>
              <p className="text-[11px] text-slate-300 mt-1">
                "We are seeing latency spikes when deploying worker agent nodes in us-east region."
              </p>
            </div>
          </div>
        </div>

        {/* Schedule Check-In form */}
        <div className="glass-panel p-5 rounded-xl border border-white/10 bg-white/2 space-y-4">
          <h3 className="text-lg font-bold flex items-center gap-2">
            <Calendar className="w-5 h-5 text-emerald-400" /> Schedule Client Review Meeting
          </h3>

          <form onSubmit={handleScheduleCheckIn} className="space-y-3">
            <div>
              <label className="block text-xs text-slate-400 font-bold mb-1">Target Check-In Date</label>
              <input
                type="date"
                required
                value={checkInDate}
                onChange={e => setCheckInDate(e.target.value)}
                className="w-full bg-white/5 border border-white/10 rounded px-3 py-1.5 text-sm text-white focus:outline-none focus:border-emerald-500"
              />
            </div>
            <div>
              <label className="block text-xs text-slate-400 font-bold mb-1">Meeting Objective</label>
              <input
                type="text"
                required
                placeholder="e.g. Conduct Q2 Onboarding SLA Review & Churn Risk Mitigation"
                value={checkInObjective}
                onChange={e => setCheckInObjective(e.target.value)}
                className="w-full bg-white/5 border border-white/10 rounded px-3 py-1.5 text-sm text-white focus:outline-none focus:border-emerald-500"
              />
            </div>
            <button
              type="submit"
              className="w-full py-2 bg-emerald-600 hover:bg-emerald-500 rounded text-xs font-semibold tracking-wider uppercase transition active:scale-95"
            >
              Confirm and Schedule Check-In
            </button>
          </form>

          {scheduledAlert && (
            <div className="p-2.5 bg-emerald-500/20 text-emerald-400 rounded text-xs text-center font-medium border border-emerald-500/20">
              {scheduledAlert}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
