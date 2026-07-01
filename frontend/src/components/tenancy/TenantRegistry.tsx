import { useTenantStore } from "../../lib/tenancy/tenantRegistry";
import type { TenantRecord } from "../../lib/tenancy/tenantTypes";
import { Users, ShieldAlert, CheckCircle, Ban } from "lucide-react";

type Props = {
  onSelect: (t: TenantRecord) => void;
  selectedId?: string;
};

export function TenantRegistry({ onSelect, selectedId }: Props) {
  const { tenants } = useTenantStore();

  const getStatusColor = (status: TenantRecord["status"]) => {
    switch (status) {
      case "active": return "text-green-400";
      case "trial": return "text-blue-400 font-bold";
      case "suspended": return "text-red-500 font-bold";
      default: return "text-slate-500";
    }
  };

  const getPlanColor = (plan: TenantRecord["plan"]) => {
    switch (plan) {
      case "regulated": return "text-purple-400 border border-purple-800/40 bg-purple-950/20";
      case "enterprise": return "text-cyan-400 border border-cyan-800/40 bg-cyan-950/20";
      default: return "text-slate-400 border border-slate-800/40 bg-slate-900/20";
    }
  };

  return (
    <div className="rounded-lg border border-slate-800 bg-slate-950/40 p-4 font-mono text-[11px]">
      <h3 className="text-xs font-bold tracking-wider text-slate-400 mb-3 uppercase flex items-center gap-2 border-b border-slate-900 pb-2">
        <Users className="h-4 w-4 text-cyan-400" />
        Tenant Registry Profiles
      </h3>
      
      <div className="overflow-x-auto">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="border-b border-slate-900 text-[10px] text-slate-500 uppercase font-bold">
              <th className="py-2">Tenant Name</th>
              <th className="py-2 text-center">Plan</th>
              <th className="py-2 text-center">Status</th>
              <th className="py-2 text-center">Users</th>
              <th className="py-2 text-right">Usage Storage</th>
            </tr>
          </thead>
          <tbody>
            {tenants.map((t) => {
              const active = selectedId === t.tenant_id;
              return (
                <tr
                  key={t.tenant_id}
                  onClick={() => onSelect(t)}
                  className={`border-b border-slate-900/50 cursor-pointer hover:bg-slate-900/30 transition-all ${
                    active ? "bg-cyan-950/20 text-cyan-200 border-l-2 border-l-cyan-500" : "text-slate-300"
                  }`}
                >
                  <td className="py-2.5 font-bold pl-1">{t.name}</td>
                  <td className="py-2.5 text-center">
                    <span className={`text-[8px] font-bold px-1.5 py-0.5 rounded uppercase ${getPlanColor(t.plan)}`}>
                      {t.plan}
                    </span>
                  </td>
                  <td className={`py-2.5 text-center uppercase font-bold ${getStatusColor(t.status)}`}>{t.status}</td>
                  <td className="py-2.5 text-center text-slate-400 font-bold">{t.usage.users}</td>
                  <td className="py-2.5 text-right font-bold text-slate-400">{t.usage.storage_gb} GB</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
