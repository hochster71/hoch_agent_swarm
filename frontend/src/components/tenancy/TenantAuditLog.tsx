import type { TenantRecord } from "../../lib/tenancy/tenantTypes";
import { useAuditStore } from "../../lib/audit/auditStore";
import type { AuditEvent } from "../../lib/audit/auditTypes";
import { History, ShieldAlert } from "lucide-react";

type Props = {
  tenant: TenantRecord;
};

export function TenantAuditLog({ tenant }: Props) {
  const { events } = useAuditStore();

  const tenantEvents = events.filter((e: AuditEvent) => {
    // Isolated audit check: match tenant_id in metadata or target ID if target is tenant
    const metaTenantId = e.metadata?.tenant_id as string | undefined;
    const targetId = e.target.id;
    return metaTenantId === tenant.tenant_id || targetId === tenant.tenant_id;
  }).slice(0, 10);

  return (
    <div className="rounded-lg border border-slate-800 bg-slate-950/60 p-4 font-mono text-[11px] space-y-3">
      <div className="flex items-center justify-between border-b border-slate-900 pb-2">
        <h3 className="text-xs font-bold tracking-wider text-slate-400 uppercase flex items-center gap-1.5">
          <History className="h-4 w-4 text-cyan-400" />
          Isolated Audit History ({tenantEvents.length})
        </h3>
        <span className="text-[9px] text-red-400 font-bold uppercase flex items-center gap-1">
          <ShieldAlert className="h-3 w-3 animate-pulse" /> Domain Boundary
        </span>
      </div>

      <div className="space-y-2 max-h-[220px] overflow-y-auto pr-1">
        {tenantEvents.length === 0 ? (
          <div className="text-slate-600 italic py-4 text-center">No audit trail logged within this tenant domain.</div>
        ) : (
          tenantEvents.map((evt: AuditEvent, idx: number) => {
            const getResultColor = (res: string) => {
              switch (res) {
                case "success": return "text-green-400";
                case "failed": return "text-red-400";
                case "blocked": return "text-slate-500";
                default: return "text-yellow-400";
              }
            };
            return (
              <div key={idx} className="p-2.5 rounded bg-slate-900/30 border border-slate-900/60 flex flex-col gap-1.5">
                <div className="flex justify-between items-center text-[9px]">
                  <span className="text-cyan-400 font-bold uppercase">{evt.action.type}</span>
                  <span className="text-slate-500">{new Date(evt.timestamp).toLocaleTimeString()}</span>
                </div>
                <span className="text-slate-200">{evt.action.summary}</span>
                <div className="flex justify-between items-center text-[9px] border-t border-slate-900/40 pt-1 text-slate-500">
                  <span>Actor: {evt.actor.name}</span>
                  <span className={`font-bold uppercase ${getResultColor(evt.result)}`}>{evt.result}</span>
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
