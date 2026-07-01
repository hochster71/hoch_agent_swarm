import React from "react";

interface BillingMetrics {
  totalRequests: number;
  billableRequests: number;
  estChargeback: number;
  costPerRequest: number;
}

interface BillingMetricsPanelProps {
  billing: BillingMetrics;
}

export const BillingMetricsPanel: React.FC<BillingMetricsPanelProps> = ({ billing }) => {
  return (
    <div className="space-y-4 text-left">
      <div className="flex items-center justify-between">
        <h4 className="text-xs font-bold text-slate-300 uppercase tracking-wider">Billing / Chargeback (30d)</h4>
        <span className="text-[10px] text-blue-400 cursor-pointer hover:underline">View Full Report</span>
      </div>

      <div className="space-y-2 text-xs">
        <div className="flex justify-between border-b border-white/5 pb-1">
          <span className="text-slate-400">Total Requests</span>
          <span className="text-white font-mono font-semibold">
            {billing.totalRequests.toLocaleString()}{" "}
            <span className="text-[9px] text-green-400 font-semibold">+16.7%</span>
          </span>
        </div>
        <div className="flex justify-between border-b border-white/5 pb-1">
          <span className="text-slate-400">Billable Requests</span>
          <span className="text-white font-mono font-semibold">
            {billing.billableRequests.toLocaleString()}{" "}
            <span className="text-[9px] text-green-400 font-semibold">+16.3%</span>
          </span>
        </div>
        <div className="flex justify-between border-b border-white/5 pb-1">
          <span className="text-slate-400">Est. Chargeback</span>
          <span className="text-green-400 font-bold font-mono">
            ${billing.estChargeback.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}{" "}
            <span className="text-[9px] text-green-400 font-semibold">+14.2%</span>
          </span>
        </div>
        <div className="flex justify-between border-b border-white/5 pb-1">
          <span className="text-slate-400">Cost / Request</span>
          <span className="text-white font-mono">
            ${billing.costPerRequest.toFixed(5)}{" "}
            <span className="text-[9px] text-green-400 font-semibold">-0.8%</span>
          </span>
        </div>
      </div>
    </div>
  );
};
