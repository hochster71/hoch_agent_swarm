import type { ExecutiveReport, ExecutivePostureStatus } from "./executiveTypes";
import { getDynamicRecommendations } from "./recommendationEngine";
import { useGovernanceRegistryStore } from "../governance/aiSystemRegistry";
import { useChaosEngineStore } from "../adversarial/chaosEngine";
import { calculateExecutivePosture } from "./postureScoring";

export function generateBoardReportMarkdown(report: ExecutiveReport): string {
  let md = `# Executive Mission Posture & Board Report\n`;
  md += `Report ID: \`${report.report_id}\` &bull; Generated At: ${report.generated_at}\n\n`;

  md += `## 1. Posture Dashboard\n\n`;
  md += `* **Overall Posture Status:** **${report.posture.overall_status.toUpperCase()}**\n`;
  md += `* **Risk Posture Score:** \`${report.posture.risk_score}/100\`\n`;
  md += `* **Operational Readiness Score:** \`${report.posture.readiness_score}/100\`\n`;
  md += `* **Governance Framework Score:** \`${report.posture.governance_score}/100\`\n`;
  md += `* **Compliance Coverage Percentage:** \`${report.posture.compliance_coverage_percent}%\`\n\n`;

  md += `## 2. Key Portfolio Metrics\n\n`;
  md += `| Metric | Current Status | Trend | Description |\n`;
  md += `|--------|----------------|-------|-------------|\n`;
  report.metrics.forEach((m) => {
    md += `| **${m.label}**: ${m.value} | \`${m.status.toUpperCase()}\` | ${m.trend.toUpperCase()} | ${m.summary} |\n`;
  });
  md += `\n`;

  md += `## 3. Strategic Action Recommendations\n\n`;
  report.recommendations.forEach((rec, idx) => {
    md += `### [${idx + 1}] ${rec.title} (Priority: **${rec.priority.toUpperCase()}**)\n`;
    md += `* **Summary:** ${rec.summary}\n`;
    md += `* **Rationale:** ${rec.rationale}\n`;
    md += `* **Expected Impact:** ${rec.expected_impact}\n`;
    md += `* **Proposed Resolution Action:** \`${rec.proposed_action}\`\n`;
    md += `* **Evidence Links:** ${rec.evidence_refs.join(", ") || "*None*"}\n\n`;
  });

  md += `## 4. Backing Audit Evidence Links\n\n`;
  md += report.evidence_refs.map(ref => `* \`${ref}\``).join("\n") + "\n\n";

  md += `\n---\n*CONFIDENTIAL &bull; FOR INTERNAL BOARD REVIEW ONLY*\n`;
  return md;
}

export function buildExecutiveReport(): ExecutiveReport {
  const { systems } = useGovernanceRegistryStore.getState();
  const { scenarios, remediations } = useChaosEngineStore.getState();

  // Compute count variables
  const unresolvedCriticalRisks = systems.filter(s => s.risk_tier === "critical" && s.status !== "approved").length;
  const failedReleaseGates = scenarios.filter(s => s.result?.status === "failed").length;
  const missingGovernanceControls = systems.reduce((acc, s) => acc + s.controls.filter(c => c.status === "missing").length, 0);
  const openPolicyViolations = remediations.filter(r => r.status === "open").length;

  const scoreStats = calculateExecutivePosture({
    unresolvedCriticalRisks,
    failedReleaseGates,
    missingGovernanceControls,
    openPolicyViolations,
    ledgerVerified: true,
    sloHealthy: true,
  });

  // Calculate compliance coverage percentage
  let totalControlsCount = 0;
  let implementedControlsCount = 0;
  systems.forEach((s) => {
    s.controls.forEach((c) => {
      totalControlsCount++;
      if (c.status === "implemented") implementedControlsCount++;
    });
  });
  const compliance_coverage_percent = totalControlsCount > 0 
    ? Math.round((implementedControlsCount / totalControlsCount) * 100) 
    : 0;

  // Aggregate metrics
  const metrics = [
    {
      metric_id: "em-risk",
      label: "Portfolio Risk Level",
      value: `${systems.filter(s => s.risk_tier === "high" || s.risk_tier === "critical").length} High Risks`,
      status: (unresolvedCriticalRisks > 0 ? "critical" : "stable") as ExecutivePostureStatus,
      trend: "flat" as const,
      summary: "Evaluated from registered AI capabilities and open vulnerabilities.",
    },
    {
      metric_id: "em-readiness",
      label: "Release Gate Readiness",
      value: `${failedReleaseGates} Blocked Gates`,
      status: (failedReleaseGates > 0 ? "watch" : "strong") as ExecutivePostureStatus,
      trend: "up" as const,
      summary: "Reflects safety assertion pass rates across red-team simulation suites.",
    },
    {
      metric_id: "em-gov",
      label: "Governance Control Mapping",
      value: `${compliance_coverage_percent}% Implemented`,
      status: (scoreStats.governance_score >= 80 ? "strong" : "watch") as ExecutivePostureStatus,
      trend: "up" as const,
      summary: "Mapped compliance percentage against standard frameworks.",
    }
  ];

  const recommendations = getDynamicRecommendations();

  // Capture backing evidence refs
  const evidence_refs = [
    ...systems.flatMap(s => s.controls.filter(c => c.status === "implemented").map(c => `evidence.${s.system_id}.${c.control_id.toLowerCase()}`)),
    ...scenarios.filter(s => s.result !== undefined).map(s => `scenario.${s.scenario_id}.run.latest`),
  ];

  return {
    report_id: `rep-${Date.now().toString().slice(-6)}`,
    generated_at: new Date().toISOString(),
    time_range: {
      start: new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString(),
      end: new Date().toISOString(),
    },
    posture: {
      overall_status: scoreStats.overall_status,
      risk_score: scoreStats.risk_score,
      readiness_score: scoreStats.readiness_score,
      governance_score: scoreStats.governance_score,
      compliance_coverage_percent,
    },
    metrics,
    recommendations,
    open_risks: systems.filter(s => s.risk_tier === "critical" || s.risk_tier === "high").map(s => s.system_id),
    blocked_decisions: scenarios.filter(s => s.result?.status === "failed").map(s => s.scenario_id),
    evidence_refs: evidence_refs.slice(0, 10), // cap at 10 items
  };
}

export function downloadBoardReportFile(report: ExecutiveReport) {
  const content = generateBoardReportMarkdown(report);
  const blob = new Blob([content], { type: "text/markdown;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.setAttribute("download", `board-posture-report-${report.report_id}.md`);
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);

  if (typeof window !== "undefined" && window.addAuditEvent) {
    window.addAuditEvent({
      action: {
        type: "BOARD_REPORT_EXPORTED",
        summary: `Executive board report ${report.report_id} exported as Markdown`,
      },
      actor: {
        id: "operator",
        name: "Michael Hoch",
        type: "human",
        role: "Operator",
      },
      target: {
        type: "system",
        id: report.report_id,
        name: "Executive Posture Dashboard",
      },
      result: "success",
      severity: "info",
      provenance: {
        source: "manual",
        evidence_refs: [],
      },
      policy: {
        required: false,
        result: "not_required",
      },
    });
  }
}
