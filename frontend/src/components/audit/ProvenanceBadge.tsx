import type { ProvenanceSource } from "@/lib/audit/auditTypes";

type Props = {
  source: ProvenanceSource;
  confidence?: number;
};

export function ProvenanceBadge({ source, confidence }: Props) {
  const label =
    confidence === undefined
      ? source
      : `${source} ${Math.round(confidence)}%`;
  return (
    <span className="rounded-full border border-slate-700 px-2 py-0.5 text-[11px] text-slate-300">
      {label}
    </span>
  );
}
