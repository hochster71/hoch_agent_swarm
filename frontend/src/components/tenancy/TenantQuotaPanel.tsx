import type { TenantRecord } from "../../lib/tenancy/tenantTypes";
import { useTenantStore } from "../../lib/tenancy/tenantRegistry";
import { ShieldCheck, Settings } from "lucide-react";

type Props = {
  tenant: TenantRecord;
};

export function TenantQuotaPanel({ tenant }: Props) {
  const { updateTenantQuotas } = useTenantStore();

  const handleChange = (key: keyof TenantRecord["quotas"], val: number) => {
    updateTenantQuotas(tenant.tenant_id, {
      ...tenant.quotas,
      [key]: val,
    });
  };

  const items = [
    { key: "max_users" as const, label: "Max User Accounts", max: 300, min: 10, step: 5, unit: "users" },
    { key: "max_agents" as const, label: "Max Swarm Agents", max: 100, min: 2, step: 2, unit: "agents" },
    { key: "max_events_per_day" as const, label: "Max Daily Events Logged", max: 5000000, min: 100000, step: 100000, unit: "events" },
    { key: "max_storage_gb" as const, label: "Max Isolated Storage Cap", max: 2000, min: 50, step: 50, unit: "GB" },
  ];

  return (
    <div className="rounded-lg border border-slate-800 bg-slate-950/60 p-4 font-mono text-[11px] space-y-4">
      <h3 className="text-xs font-bold tracking-wider text-slate-400 border-b border-slate-900 pb-2 uppercase flex items-center gap-1.5">
        <Settings className="h-4 w-4 text-cyan-400" />
        Tenant Allocation & Quotas
      </h3>

      <div className="space-y-4">
        {items.map((item) => {
          const val = tenant.quotas[item.key];
          // Calculate usage percent if possible
          let usageVal = 0;
          if (item.key === "max_users") usageVal = tenant.usage.users;
          else if (item.key === "max_agents") usageVal = tenant.usage.agents;
          else if (item.key === "max_events_per_day") usageVal = tenant.usage.events_today;
          else if (item.key === "max_storage_gb") usageVal = tenant.usage.storage_gb;

          const pct = Math.round((usageVal / val) * 100);

          return (
            <div key={item.key} className="space-y-2">
              <div className="flex justify-between items-center text-[10px]">
                <span className="text-slate-400">{item.label}</span>
                <span className="text-slate-200 font-bold">
                  {usageVal >= 1000000 ? `${(usageVal/1000000).toFixed(1)}M` : usageVal} / {val >= 1000000 ? `${(val/1000000).toFixed(1)}M` : val} {item.unit} ({pct}%)
                </span>
              </div>

              {/* Slider */}
              <div className="flex items-center gap-3">
                <input
                  type="range"
                  min={item.min}
                  max={item.max}
                  step={item.step}
                  value={val}
                  onChange={(e) => handleChange(item.key, parseInt(e.target.value))}
                  className="w-full h-1 bg-slate-900 rounded-lg appearance-none cursor-pointer accent-cyan-500"
                />
              </div>

              {/* Progress visual bar */}
              <div className="w-full bg-slate-900 rounded-full h-1">
                <div
                  className={`h-1 rounded-full ${pct >= 85 ? "bg-red-500" : pct >= 60 ? "bg-yellow-500" : "bg-cyan-500"}`}
                  style={{ width: `${Math.min(100, pct)}%` }}
                />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
