import React, { useState } from "react";
import {
  TrendingUp,
  DollarSign,
  Users,
  Compass,
  Award,
  Sliders,
  ChevronRight,
  Plus,
  Edit2,
  ListTodo,
  CheckCircle,
  FileCheck,
  Percent
} from "lucide-react";
import {
  initialPartners,
  initialPlans,
  initialSnapshot,
  initialStrategicPriorities
} from "../../lib/revenue-ops/revenueFixtures";
import { PartnerRecord, PricingPlan, RevenueSnapshot } from "../../lib/revenue-ops/revenueTypes";

export const RevenueOpsDashboard: React.FC = () => {
  const [snapshot, setSnapshot] = useState<RevenueSnapshot>(initialSnapshot);
  const [partners, setPartners] = useState<PartnerRecord[]>(initialPartners);
  const [plans, setPlans] = useState<PricingPlan[]>(initialPlans);
  const [priorities, setPriorities] = useState(initialStrategicPriorities);

  // Growth rate simulator
  const [monthlyGrowthRate, setMonthlyGrowthRate] = useState<number>(12); // in percent

  // Edit pricing plan state
  const [editingPlanId, setEditingPlanId] = useState<string | null>(null);
  const [planBasePrice, setPlanBasePrice] = useState<number>(0);
  const [planExtraPrice, setPlanExtraPrice] = useState<number>(0);

  // New partner state
  const [newPartnerName, setNewPartnerName] = useState("");
  const [newPartnerTier, setNewPartnerTier] = useState<any>("strategic");

  // Calculations for growth projection
  const currentARR = snapshot.arr_usd;
  const projectARR = (months: number) => {
    const rate = 1 + monthlyGrowthRate / 100;
    return Math.round(currentARR * Math.pow(rate, months / 12));
  };

  const handleUpdatePlan = (planId: string) => {
    setPlans(prevPlans =>
      prevPlans.map(p => {
        if (p.plan_id === planId) {
          // Trigger audit event
          if (window.addAuditEvent) {
            window.addAuditEvent({
              actor: { id: "op-mh-99", name: "Michael Hoch", type: "human", role: "Revenue Operations Director" },
              action: { type: "REVENUE_PRICING_PLAN_UPDATED", summary: `Updated plan pricing for ${p.name}` },
              target: { type: "system", id: planId, name: p.name },
              result: "success",
              severity: "info",
              provenance: { source: "manual", evidence_refs: [] },
              policy: { required: false, result: "passed" }
            });
          }

          return {
            ...p,
            base_price_monthly_usd: planBasePrice,
            extra_agent_price_monthly_usd: planExtraPrice
          };
        }
        return p;
      })
    );
    setEditingPlanId(null);
  };

  const startEditPlan = (plan: PricingPlan) => {
    setEditingPlanId(plan.plan_id);
    setPlanBasePrice(plan.base_price_monthly_usd);
    setPlanExtraPrice(plan.extra_agent_price_monthly_usd);
  };

  const handleRegisterPartner = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newPartnerName) return;

    const newPartner: PartnerRecord = {
      partner_id: `part-${Math.floor(Math.random() * 1000)}`,
      name: newPartnerName,
      tier: newPartnerTier,
      referred_customers_count: 0,
      influenced_arr_usd: 0,
      certification_status: "pending",
      joined_at: new Date().toISOString()
    };

    setPartners(prev => [...prev, newPartner]);

    // Audit Event
    if (window.addAuditEvent) {
      window.addAuditEvent({
        actor: { id: "op-mh-99", name: "Michael Hoch", type: "human", role: "Channel Partner Lead" },
        action: { type: "REVENUE_PARTNER_REGISTERED", summary: `Registered channel partner "${newPartnerName}"` },
        target: { type: "swarm", id: newPartner.partner_id, name: newPartnerName },
        result: "success",
        severity: "info",
        provenance: { source: "manual", evidence_refs: [] },
        policy: { required: false, result: "passed" }
      });
    }

    setNewPartnerName("");
  };

  const toggleCertification = (partnerId: string) => {
    setPartners(prev =>
      prev.map(p => {
        if (p.partner_id === partnerId) {
          const nextStatus = p.certification_status === "certified" ? "expired" : "certified";

          // Audit Event
          if (window.addAuditEvent) {
            window.addAuditEvent({
              actor: { id: "op-mh-99", name: "Michael Hoch", type: "human", role: "Channel Partner Lead" },
              action: { type: "REVENUE_PARTNER_CERTIFIED", summary: `Changed partner certification status to ${nextStatus} for ${p.name}` },
              target: { type: "swarm", id: partnerId, name: p.name },
              result: "success",
              severity: "info",
              provenance: { source: "manual", evidence_refs: [] },
              policy: { required: false, result: "passed" }
            });
          }

          return { ...p, certification_status: nextStatus };
        }
        return p;
      })
    );
  };

  const handleUpdatePriorityProgress = (priorityId: string, nextProgress: number) => {
    setPriorities(prev =>
      prev.map(p => {
        if (p.priority_id === priorityId) {
          return { ...p, progress: nextProgress };
        }
        return p;
      })
    );
  };

  const savePriorityChange = (priorityId: string, finalVal: number) => {
    const priObj = priorities.find(p => p.priority_id === priorityId);
    if (!priObj) return;

    if (window.addAuditEvent) {
      window.addAuditEvent({
        actor: { id: "op-mh-99", name: "Michael Hoch", type: "human", role: "Revenue Operations Director" },
        action: { type: "REVENUE_STRATEGIC_PRIORITY_UPDATED", summary: `Updated strategic priority "${priObj.title}" progress to ${finalVal}%` },
        target: { type: "task", id: priorityId, name: priObj.title },
        result: "success",
        severity: "info",
        provenance: { source: "manual", evidence_refs: [] },
        policy: { required: false, result: "passed" }
      });
    }
  };

  const triggerForecastAudit = (val: number) => {
    setMonthlyGrowthRate(val);
    if (window.addAuditEvent) {
      window.addAuditEvent({
        actor: { id: "op-mh-99", name: "Michael Hoch", type: "human", role: "Revenue Operations Director" },
        action: { type: "REVENUE_FORECAST_UPDATED", summary: `Recalculated MRR/ARR growth projections at ${val}% annual growth target.` },
        target: { type: "system", id: "revenue-forecast", name: "Strategic Scale Projections Engine" },
        result: "success",
        severity: "info",
        provenance: { source: "inferred", evidence_refs: [] },
        policy: { required: false, result: "passed" }
      });
    }
  };

  return (
    <div className="glass-panel p-6 rounded-2xl border border-white/10 text-white space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center border-b border-white/10 pb-5">
        <div>
          <div className="flex items-center gap-2">
            <Compass className="w-8 h-8 text-indigo-400" />
            <h2 className="text-2xl font-bold tracking-tight">Strategic Scale &amp; Revenue Operations</h2>
          </div>
          <p className="text-slate-400 text-sm mt-1">
            Simulate target growth forecasts, configure tenancy plan models, and verify certified channel partners.
          </p>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-5 gap-4">
        <div className="glass-panel p-4 rounded-xl border border-white/5 bg-white/2 space-y-1">
          <span className="text-xs font-bold text-slate-400 uppercase tracking-wider block">ARR Total</span>
          <div className="text-2xl font-bold">${snapshot.arr_usd.toLocaleString()}</div>
          <p className="text-[10px] text-slate-500">Annualized Run Rate</p>
        </div>
        <div className="glass-panel p-4 rounded-xl border border-white/5 bg-white/2 space-y-1">
          <span className="text-xs font-bold text-slate-400 uppercase tracking-wider block">MRR Total</span>
          <div className="text-2xl font-bold">${snapshot.mrr_usd.toLocaleString()}</div>
          <p className="text-[10px] text-slate-500">Monthly Recurring Revenue</p>
        </div>
        <div className="glass-panel p-4 rounded-xl border border-white/5 bg-white/2 space-y-1">
          <span className="text-xs font-bold text-slate-400 uppercase tracking-wider block">Active Contracts</span>
          <div className="text-2xl font-bold text-indigo-400">{snapshot.customers_count}</div>
          <p className="text-[10px] text-slate-500">Platform Swarms</p>
        </div>
        <div className="glass-panel p-4 rounded-xl border border-white/5 bg-white/2 space-y-1">
          <span className="text-xs font-bold text-slate-400 uppercase tracking-wider block">ACV Average</span>
          <div className="text-2xl font-bold">${snapshot.average_contract_value_usd.toLocaleString()}</div>
          <p className="text-[10px] text-slate-500">Contract Unit margins</p>
        </div>
        <div className="glass-panel p-4 rounded-xl border border-white/5 bg-white/2 space-y-1">
          <span className="text-xs font-bold text-slate-400 uppercase tracking-wider block">NPS Score</span>
          <div className="text-2xl font-bold text-emerald-400">{snapshot.nps_score}</div>
          <p className="text-[10px] text-slate-500">Customer NPS Sentiment</p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Growth Forecast Simulator */}
        <div className="glass-panel p-5 rounded-xl border border-white/10 bg-white/2 space-y-4">
          <h3 className="text-lg font-bold flex items-center gap-2">
            <Sliders className="w-5 h-5 text-indigo-400" /> Revenue Growth Projections
          </h3>
          <p className="text-xs text-slate-400">
            Slide to adjust the target annual growth rate and simulate ARR and MRR trends over the next year.
          </p>

          <div className="space-y-2 py-2">
            <div className="flex justify-between text-sm">
              <span>Annual Growth Target:</span>
              <span className="font-bold text-indigo-400">{monthlyGrowthRate}%</span>
            </div>
            <input
              type="range"
              min="5"
              max="60"
              value={monthlyGrowthRate}
              onChange={e => triggerForecastAudit(Number(e.target.value))}
              className="w-full h-1.5 bg-white/10 rounded-lg appearance-none cursor-pointer accent-indigo-500"
            />
          </div>

          <div className="space-y-3 mt-4">
            <div className="flex justify-between items-center text-xs text-slate-400 font-bold border-b border-white/5 pb-2">
              <span>Timeline</span>
              <span>Projected ARR</span>
              <span className="text-right">Estimated MRR</span>
            </div>
            {/* Timeline projected values */}
            {[3, 6, 12].map(months => {
              const projectedArrVal = projectARR(months);
              const projectedMrrVal = Math.round(projectedArrVal / 12);
              return (
                <div key={months} className="flex justify-between items-center text-sm">
                  <span className="font-semibold">{months} Months Projection</span>
                  <span className="font-bold text-white">${projectedArrVal.toLocaleString()}</span>
                  <span className="text-slate-300 text-right">${projectedMrrVal.toLocaleString()}</span>
                </div>
              );
            })}
          </div>
        </div>

        {/* Pricing Plan Editor */}
        <div className="glass-panel p-5 rounded-xl border border-white/10 bg-white/2 space-y-4">
          <h3 className="text-lg font-bold flex items-center gap-2">
            <DollarSign className="w-5 h-5 text-emerald-400" /> Subscription Plan Configurator
          </h3>
          <div className="space-y-3">
            {plans.map(p => (
              <div
                key={p.plan_id}
                className="p-3.5 bg-white/5 rounded-lg border border-white/5 flex justify-between items-center"
              >
                <div>
                  <div className="font-bold text-sm">{p.name}</div>
                  <div className="text-xs text-slate-400 mt-1">
                    Base: ${p.base_price_monthly_usd}/mo | Includes: {p.included_agents} agents
                  </div>
                  <div className="text-[10px] text-slate-500 mt-0.5">
                    Extra Agent fee: ${p.extra_agent_price_monthly_usd}/mo
                  </div>
                </div>

                <div>
                  {editingPlanId === p.plan_id ? (
                    <div className="flex flex-col gap-2 bg-slate-900 p-2.5 rounded border border-white/10">
                      <div>
                        <label className="block text-[9px] text-slate-400 uppercase font-bold">Base Price</label>
                        <input
                          type="number"
                          value={planBasePrice}
                          onChange={e => setPlanBasePrice(Number(e.target.value))}
                          className="bg-white/10 text-white text-xs px-2 py-0.5 rounded focus:outline-none w-20"
                        />
                      </div>
                      <div>
                        <label className="block text-[9px] text-slate-400 uppercase font-bold">Extra Agent</label>
                        <input
                          type="number"
                          value={planExtraPrice}
                          onChange={e => setPlanExtraPrice(Number(e.target.value))}
                          className="bg-white/10 text-white text-xs px-2 py-0.5 rounded focus:outline-none w-20"
                        />
                      </div>
                      <button
                        onClick={() => handleUpdatePlan(p.plan_id)}
                        className="bg-indigo-600 hover:bg-indigo-500 text-[10px] py-1 rounded font-bold uppercase"
                      >
                        Save
                      </button>
                    </div>
                  ) : (
                    <button
                      onClick={() => startEditPlan(p)}
                      className="p-1.5 hover:bg-white/10 rounded transition text-slate-400 hover:text-white"
                    >
                      <Edit2 className="w-4 h-4" />
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Partners Table */}
        <div className="glass-panel p-5 rounded-xl border border-white/10 bg-white/2 space-y-4">
          <div className="flex justify-between items-center">
            <h3 className="text-lg font-bold flex items-center gap-2">
              <Award className="w-5 h-5 text-yellow-400" /> Channel Partners Directory
            </h3>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="border-b border-white/10 text-slate-400 uppercase font-bold">
                  <th className="pb-2">Partner Name</th>
                  <th className="pb-2">Tier</th>
                  <th className="pb-2">Referred</th>
                  <th className="pb-2">Influenced</th>
                  <th className="pb-2 text-right">Certification</th>
                </tr>
              </thead>
              <tbody>
                {partners.map(p => (
                  <tr key={p.partner_id} className="border-b border-white/5 hover:bg-white/1">
                    <td className="py-2.5 font-bold">{p.name}</td>
                    <td className="py-2.5 capitalize text-slate-400">{p.tier}</td>
                    <td className="py-2.5">{p.referred_customers_count}</td>
                    <td className="py-2.5 text-slate-300">${p.influenced_arr_usd.toLocaleString()}</td>
                    <td className="py-2.5 text-right">
                      <button
                        onClick={() => toggleCertification(p.partner_id)}
                        className={`text-[9px] px-2 py-0.5 rounded-full font-bold uppercase border transition ${
                          p.certification_status === "certified"
                            ? "bg-green-500/10 text-green-400 border-green-500/20"
                            : p.certification_status === "pending"
                            ? "bg-yellow-500/10 text-yellow-400 border-yellow-500/20"
                            : "bg-red-500/10 text-red-400 border-red-500/20"
                        }`}
                      >
                        {p.certification_status}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <form onSubmit={handleRegisterPartner} className="flex gap-2 pt-2 border-t border-white/5">
            <input
              type="text"
              required
              placeholder="Partner Company Name..."
              value={newPartnerName}
              onChange={e => setNewPartnerName(e.target.value)}
              className="flex-1 bg-white/5 border border-white/10 rounded px-2.5 py-1 text-xs text-white focus:outline-none focus:border-indigo-500"
            />
            <select
              value={newPartnerTier}
              onChange={e => setNewPartnerTier(e.target.value)}
              className="bg-white/5 border border-white/10 rounded px-2 text-xs text-white focus:outline-none focus:border-indigo-500"
            >
              <option value="strategic">Strategic</option>
              <option value="consulting">Consulting</option>
              <option value="technology">Technology</option>
              <option value="reseller">Reseller</option>
            </select>
            <button
              type="submit"
              className="px-3 bg-indigo-600 hover:bg-indigo-500 rounded text-xs font-bold uppercase transition flex items-center gap-1 active:scale-95"
            >
              <Plus className="w-3.5 h-3.5" /> Register
            </button>
          </form>
        </div>

        {/* Strategic Priorities */}
        <div className="glass-panel p-5 rounded-xl border border-white/10 bg-white/2 space-y-4">
          <h3 className="text-lg font-bold flex items-center gap-2">
            <ListTodo className="w-5 h-5 text-indigo-400" /> strategic scale checklist
          </h3>
          <div className="space-y-4">
            {priorities.map(p => (
              <div key={p.priority_id} className="space-y-1.5">
                <div className="flex justify-between items-center text-xs">
                  <span className="font-semibold">{p.title}</span>
                  <span className="text-[10px] font-bold tracking-widest uppercase text-slate-500 px-1 bg-white/5 rounded">
                    Weight: {p.weight}
                  </span>
                </div>
                <div className="flex items-center gap-3">
                  <input
                    type="range"
                    min="0"
                    max="100"
                    value={p.progress}
                    onChange={e => handleUpdatePriorityProgress(p.priority_id, Number(e.target.value))}
                    onMouseUp={e =>
                      savePriorityChange(p.priority_id, Number((e.target as HTMLInputElement).value))
                    }
                    onTouchEnd={e =>
                      savePriorityChange(p.priority_id, Number((e.target as HTMLInputElement).value))
                    }
                    className="flex-1 h-1 bg-white/10 rounded-lg appearance-none cursor-pointer accent-indigo-400"
                  />
                  <span className="text-xs font-mono font-bold text-indigo-400 w-8 text-right">
                    {p.progress}%
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};
