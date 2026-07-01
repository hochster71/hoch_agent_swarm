import type { AiSystemRecord } from "./governanceTypes";

export function generateGovernanceEvidenceReport(systems: AiSystemRecord[]): string {
  let md = `# AI Governance, Risk & Compliance Evidence Report\n`;
  md += `Generated At: ${new Date().toISOString()}\n\n`;

  md += `## 1. System Registry Summary\n\n`;
  md += `| System ID | Name | Type | Risk Tier | Status | Next Review Due |\n`;
  md += `|-----------|------|------|-----------|--------|-----------------|\n`;
  systems.forEach((sys) => {
    md += `| \`${sys.system_id}\` | ${sys.name} | ${sys.type} | **${sys.risk_tier.toUpperCase()}** | \`${sys.status}\` | ${sys.review.next_review_due || "N/A"} |\n`;
  });
  md += `\n`;

  md += `## 2. Controls Mapping Status\n\n`;
  md += `| System | Control ID | Framework | Status | Evidence References |\n`;
  md += `|--------|------------|-----------|--------|---------------------|\n`;
  systems.forEach((sys) => {
    sys.controls.forEach((ctrl) => {
      md += `| ${sys.name} | \`${ctrl.control_id}\` | ${ctrl.framework} | **${ctrl.status.toUpperCase()}** | ${ctrl.evidence_refs.join(", ") || "*None*"} |\n`;
    });
  });
  md += `\n`;

  md += `## 3. Risk Assessment Explanations\n\n`;
  systems.forEach((sys) => {
    md += `### ${sys.name} (${sys.risk_tier.toUpperCase()} Risk)\n`;
    md += `* **Owner:** ${sys.owner}\n`;
    md += `* **Description:** ${sys.description}\n`;
    md += `* **Capabilities:** ${sys.capabilities.join(", ")}\n`;
    md += `* **Autonomy:** execution ${sys.autonomy.can_execute ? "ENABLED" : "DISABLED"}, approval required: ${sys.autonomy.requires_human_approval ? "YES" : "NO"}\n`;
    md += `* **Data Access:** classification: \`${sys.data_access.classification}\`, PII: ${sys.data_access.pii_access ? "YES" : "NO"}, secrets: ${sys.data_access.secret_access ? "YES" : "NO"}\n\n`;
  });

  return md;
}

export function downloadGovernanceEvidenceFile(systems: AiSystemRecord[]) {
  const content = generateGovernanceEvidenceReport(systems);
  const blob = new Blob([content], { type: "text/markdown;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.setAttribute("download", `governance-evidence-${new Date().toISOString().split("T")[0]}.md`);
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);

  if (typeof window !== "undefined" && window.addAuditEvent) {
    window.addAuditEvent({
      action: {
        type: "GOVERNANCE_EVIDENCE_EXPORTED",
        summary: `Governance evidence report exported as Markdown`,
      },
      actor: {
        id: "operator",
        name: "Michael Hoch",
        type: "human",
        role: "Operator",
      },
      target: {
        type: "system",
        id: "governance-plane",
        name: "AI Governance Control Plane",
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
