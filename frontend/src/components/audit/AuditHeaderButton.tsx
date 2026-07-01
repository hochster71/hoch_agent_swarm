import { useAuditStore } from "@/lib/audit/auditStore";

export function AuditHeaderButton() {
  const { events, openDrawer } = useAuditStore();
  return (
    <button
      onClick={openDrawer}
      className="rounded-full border border-slate-700 px-3 py-1 text-xs text-slate-300 hover:bg-slate-800"
      style={{
        background: "rgba(30, 41, 59, 0.4)",
        border: "1px solid rgba(255,255,255,0.08)",
        color: "#cbd5e1",
        fontFamily: "monospace",
        cursor: "pointer",
        padding: "4px 12px",
        borderRadius: "9999px",
        transition: "all 0.2s"
      }}
    >
      Audit: Recording · {events.length}
    </button>
  );
}
