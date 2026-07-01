import type { AuditEvent } from "./auditTypes";
import { buildAuditReport } from "./auditExport";
import { auditEventsToCsv } from "./auditCsv";
import { auditReportToMarkdown } from "./auditMarkdown";

export type EvidencePack = {
  pack_id: string;
  created_at: string;
  report_json: string;
  report_csv: string;
  report_md: string;
  manifest: {
    files: string[];
    event_count: number;
    integrity_score: number;
  };
};

export function generateEvidencePack(events: AuditEvent[]): EvidencePack {
  const report = buildAuditReport({ events });
  const csvContent = auditEventsToCsv(events);
  const mdContent = auditReportToMarkdown(report);
  
  const totalChecks = events.length * 4;
  let passedChecks = totalChecks;
  for (const event of events) {
    if (!event.policy) passedChecks--;
    if (!event.provenance.evidence_refs || event.provenance.evidence_refs.length === 0) passedChecks--;
    if (["inferred", "predicted"].includes(event.provenance.source) && event.provenance.confidence === undefined) passedChecks--;
  }
  const score = totalChecks > 0 ? Math.round((passedChecks / totalChecks) * 100) : 100;

  const packId = `pack_${Date.now()}`;
  return {
    pack_id: packId,
    created_at: new Date().toISOString(),
    report_json: JSON.stringify(report, null, 2),
    report_csv: csvContent,
    report_md: mdContent,
    manifest: {
      files: [`${packId}.json`, `${packId}.csv`, `${packId}.md`],
      event_count: events.length,
      integrity_score: score,
    },
  };
}
