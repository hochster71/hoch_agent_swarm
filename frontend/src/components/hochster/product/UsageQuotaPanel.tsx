import React from "react";

interface QuotaItem {
  tier: string;
  tenants: number;
  limit: string;
  used: string;
  utilization: string;
}

interface UsageQuotaPanelProps {
  quotas: QuotaItem[];
}

export const UsageQuotaPanel: React.FC<UsageQuotaPanelProps> = ({ quotas }) => {
  return (
    <div className="space-y-4 text-left">
      <div className="flex items-center justify-between">
        <h4 className="text-xs font-bold text-slate-300 uppercase tracking-wider">Usage & Quotas (By Tenant Tier)</h4>
        <span className="text-[10px] text-blue-400 cursor-pointer hover:underline">View All Usage</span>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="border-b border-white/5 text-[9px] uppercase text-slate-400 font-bold">
              <th className="py-2">Tier</th>
              <th className="py-2">Tenants</th>
              <th className="py-2">Daily Limit</th>
              <th className="py-2">Used (24h)</th>
              <th className="py-2 text-right">Utilization</th>
            </tr>
          </thead>
          <tbody>
            {quotas.map((u, idx) => (
              <tr key={idx} className="border-b border-white/5 hover:bg-white/5 transition text-xs">
                <td className="py-2.5 font-semibold text-white">{u.tier}</td>
                <td className="py-2.5 font-mono text-slate-300">{u.tenants}</td>
                <td className="py-2.5 font-mono text-slate-300">{u.limit}</td>
                <td className="py-2.5 font-mono text-slate-300">{u.used}</td>
                <td className="py-2.5 text-right font-bold text-blue-400">{u.utilization}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};
