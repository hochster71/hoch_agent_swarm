import type { TenantRecord } from "../../lib/tenancy/tenantTypes";
import { Activity, Database, Users, ShieldAlert } from "lucide-react";

type Props = {
  tenant: TenantRecord;
};

export function TenantUsageDashboard({ tenant }: Props) {
  // Mock usage calculations
  const dailyEventCap = tenant.quotas.max_events_per_day;
  const currentEvents = tenant.usage.events_today;
  const eventPct = Math.round((currentEvents / dailyEventCap) * 100);

  const storageCap = tenant.quotas.max_storage_gb;
  const currentStorage = tenant.usage.storage_gb;
  const storagePct = Math.round((currentStorage / storageCap) * 100);

  return (
    <div className="rounded-lg border border-slate-800 bg-slate-950/60 p-4 font-mono text-[11px] space-y-4">
      <h3 className="text-xs font-bold tracking-wider text-slate-400 border-b border-slate-900 pb-2 uppercase flex items-center gap-1.5">
        <Activity className="h-4 w-4 text-cyan-400" />
        Tenant Real-Time Usage Dashboard
      </h3>

      <div className="grid grid-cols-2 gap-4 text-center">
        {/* Daily events gauge */}
        <div className="p-3 bg-slate-900/20 border border-slate-900 rounded space-y-2 flex flex-col justify-between">
          <div>
            <span className="text-slate-500 text-[8px] uppercase block">Daily Events Utilization</span>
            <span className="text-xl font-bold text-slate-200 mt-1 block">
              {currentEvents >= 1000000 ? `${(currentEvents/1000000).toFixed(1)}M` : currentEvents}
            </span>
          </div>
          <div className="w-full bg-slate-900 rounded-full h-1">
            <div className="h-1 rounded-full bg-cyan-500" style={{ width: `${eventPct}%` }} />
          </div>
          <span className="text-[8px] text-slate-600 block mt-0.5">{eventPct}% of limit reached</span>
        </div>

        {/* Database size gauge */}
        <div className="p-3 bg-slate-900/20 border border-slate-900 rounded space-y-2 flex flex-col justify-between">
          <div>
            <span className="text-slate-500 text-[8px] uppercase block">Database Storage Size</span>
            <span className="text-xl font-bold text-slate-200 mt-1 block">{currentStorage} GB</span>
          </div>
          <div className="w-full bg-slate-900 rounded-full h-1">
            <div className="h-1 rounded-full bg-cyan-500" style={{ width: `${storagePct}%` }} />
          </div>
          <span className="text-[8px] text-slate-600 block mt-0.5">{storagePct}% of storage capacity</span>
        </div>
      </div>

      <div className="space-y-2">
        <div className="flex justify-between items-center text-[10px] text-slate-400">
          <span className="flex items-center gap-1.5">
            <Users className="h-3.5 w-3.5 text-slate-500" />
            Active User Seats
          </span>
          <span className="font-bold text-slate-200">{tenant.usage.users} / {tenant.quotas.max_users}</span>
        </div>

        <div className="flex justify-between items-center text-[10px] text-slate-400">
          <span className="flex items-center gap-1.5">
            <Database className="h-3.5 w-3.5 text-slate-500" />
            Active Swarm Agents
          </span>
          <span className="font-bold text-slate-200">{tenant.usage.agents} / {tenant.quotas.max_agents}</span>
        </div>
      </div>

    </div>
  );
}
