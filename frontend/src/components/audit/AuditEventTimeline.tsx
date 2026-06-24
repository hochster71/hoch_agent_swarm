import type { AuditEvent } from "@/lib/audit/auditTypes";
import { AuditEventCard } from "./AuditEventCard";

type Props = {
  events: AuditEvent[];
};

export function AuditEventTimeline({ events }: Props) {
  if (!events.length) {
    return (
      <div className="rounded-lg border border-slate-800 p-4 text-sm text-slate-400">
        No audit events recorded yet.
      </div>
    );
  }
  return (
    <div className="space-y-3">
      {events.map((event) => (
        <AuditEventCard key={event.event_id} event={event} />
      ))}
    </div>
  );
}
