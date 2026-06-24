import type { TenantRecord } from "../../lib/tenancy/tenantTypes";
import { Info, Ban, ShieldCheck, RefreshCcw } from "lucide-react";
import { useTenantStore } from "../../lib/tenancy/tenantRegistry";

type Props = {
  tenant: TenantRecord;
};

export function TenantDetailPanel({ tenant }: Props) {
  const { updateTenantStatus } = useTenantStore();

  const handleToggleStatus = () => {
    const nextStatus = tenant.status === "active" ? "suspended" : "active";
    updateTenantStatus(tenant.tenant_id, nextStatus);
  };

  const getStatusBadge = () => {
    switch (tenant.status) {
      case "active": return "bg-green-950 border-green-800/40 text-green-400";
      case "suspended": return "bg-red-950 border-red-800/40 text-red-400 animate-pulse";
      case "trial": return "bg-blue-950 border-blue-800/40 text-blue-400";
      default: return "bg-slate-900 border-slate-800 text-slate-500";
    }
  };

  return (
    <div className="rounded-lg border border-slate-800 bg-slate-950/60 p-4 font-mono text-[11px] space-y-4">
      <div className="flex items-center justify-between border-b border-slate-900 pb-2">
        <div>
          <div className="flex items-center gap-2">
            <span className={`text-[8px] font-bold px-1.5 py-0.5 rounded uppercase ${getStatusBadge()}`}>
              {tenant.status}
            </span>
            <span className="text-[10px] text-slate-500 font-bold uppercase">{tenant.plan} plan</span>
          </div>
          <h3 className="font-bold text-slate-100 mt-1">{tenant.name}</h3>
        </div>
        <button
          onClick={handleToggleStatus}
          className={`px-2.5 py-1 rounded text-[10px] font-bold border transition-all ${
            tenant.status === "active"
              ? "bg-red-950/20 border-red-800/40 text-red-400 hover:bg-red-900/30"
              : "bg-green-950/20 border-green-800/40 text-green-400 hover:bg-green-900/30"
          }`}
        >
          {tenant.status === "active" ? "Suspend Tenant" : "Activate Tenant"}
        </button>
      </div>

      <div className="grid grid-cols-2 gap-3 text-slate-400">
        <div className="p-2 rounded bg-slate-900/30 border border-slate-900/60">
          <span className="text-slate-500 text-[8px] block uppercase font-bold">Isolated Namespace</span>
          <span className="text-slate-200 mt-0.5 block">{tenant.isolation.namespace}</span>
        </div>
        <div className="p-2 rounded bg-slate-900/30 border border-slate-900/60">
          <span className="text-slate-500 text-[8px] block uppercase font-bold">Partition Key</span>
          <span className="text-slate-200 mt-0.5 block">{tenant.isolation.data_partition_key}</span>
        </div>
        <div className="p-2 rounded bg-slate-900/30 border border-slate-900/60">
          <span className="text-slate-500 text-[8px] block uppercase font-bold">Dedicated Cryptographic Keys</span>
          <span className="text-slate-200 mt-0.5 block">{tenant.isolation.dedicated_key_material ? "ENABLED" : "DISABLED"}</span>
        </div>
        <div className="p-2 rounded bg-slate-900/30 border border-slate-900/60">
          <span className="text-slate-500 text-[8px] block uppercase font-bold">Onboarded At</span>
          <span className="text-slate-200 mt-0.5 block">{new Date(tenant.lifecycle.created_at).toLocaleDateString()}</span>
        </div>
      </div>
    </div>
  );
}
