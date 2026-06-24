import type { AuditEvent } from "@/lib/audit/auditTypes";
import { ProvenanceBadge } from "./ProvenanceBadge";

type Props = {
  event: AuditEvent;
};

function formatTime(timestamp: string) {
  return new Intl.DateTimeFormat(undefined, {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  }).format(new Date(timestamp));
}

export function AuditEventCard({ event }: Props) {
  return (
    <article className="rounded-lg border border-slate-800 bg-slate-900/80 p-3">
      <div className="mb-2 flex items-start justify-between gap-3">
        <div>
          <div className="text-xs font-semibold uppercase tracking-wide text-slate-300">
            {event.action.type}
          </div>
          <div className="mt-1 text-sm text-slate-100">
            {event.action.summary}
          </div>
        </div>
        <div className="shrink-0 text-xs text-slate-500">
          {formatTime(event.timestamp)}
        </div>
      </div>
      <div className="mb-2 flex flex-wrap gap-2">
        <span className="rounded-full border border-slate-700 px-2 py-0.5 text-[11px] text-slate-300">
          {event.result}
        </span>
        <span className="rounded-full border border-slate-700 px-2 py-0.5 text-[11px] text-slate-300">
          severity: {event.severity}
        </span>
        <ProvenanceBadge
          source={event.provenance.source}
          confidence={event.provenance.confidence}
        />
        <span className="rounded-full border border-slate-700 px-2 py-0.5 text-[11px] text-slate-300">
          policy: {event.policy.result}
        </span>
      </div>
      <dl className="grid grid-cols-2 gap-x-3 gap-y-1 text-xs text-slate-400">
        <dt>Actor</dt>
        <dd className="text-slate-300">{event.actor.name}</dd>
        <dt>Target</dt>
        <dd className="text-slate-300">
          {event.target.name ?? event.target.id}
        </dd>
        <dt>Correlation</dt>
        <dd className="truncate text-slate-500">{event.correlation_id}</dd>
        <dt>Evidence</dt>
        <dd className="text-slate-300">
          {event.provenance.evidence_refs.length}
        </dd>
      </dl>
    </article>
  );
}
