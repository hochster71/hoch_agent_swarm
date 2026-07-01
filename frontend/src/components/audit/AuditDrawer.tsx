import { useAuditStore } from "@/lib/audit/auditStore";
import { AuditEventTimeline } from "./AuditEventTimeline";
import { AuditExportButton } from "./AuditExportButton";

export function AuditDrawer() {
  const { events, isDrawerOpen, closeDrawer } = useAuditStore();
  if (!isDrawerOpen) return null;
  return (
    <aside className="fixed right-0 top-0 z-50 h-screen w-[440px] border-l border-slate-700 bg-slate-950 text-slate-100 shadow-2xl flex flex-col">
      <div className="flex items-center justify-between border-b border-slate-800 px-4 py-3 shrink-0">
        <div>
          <h2 className="text-sm font-semibold uppercase tracking-wide">
            Operational Audit Trail
          </h2>
          <p className="text-xs text-slate-400">
            {events.length} recorded events
          </p>
        </div>
        <button
          onClick={closeDrawer}
          className="rounded-md border border-slate-700 px-2 py-1 text-xs text-slate-300 hover:bg-slate-800"
        >
          Close
        </button>
      </div>
      <div className="flex items-center justify-between border-b border-slate-800 px-4 py-3 shrink-0">
        <span className="text-xs text-slate-400">
          Audit recording active
        </span>
        <AuditExportButton events={events} />
      </div>
      <div className="flex-grow overflow-y-auto px-4 py-3">
        <AuditEventTimeline events={events} />
      </div>
    </aside>
  );
}
