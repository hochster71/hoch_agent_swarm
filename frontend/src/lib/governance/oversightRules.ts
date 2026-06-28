import type { AiSystemRecord } from "./governanceTypes";

export type OversightViolation = {
  system_id: string;
  system_name: string;
  rule_id: string;
  rule_description: string;
  severity: "medium" | "high" | "critical";
};

export function auditOversightRules(systems: AiSystemRecord[]): OversightViolation[] {
  const violations: OversightViolation[] = [];

  systems.forEach((sys) => {
    // Rule 1: Executable autonomy without human-in-the-loop approval
    if (sys.autonomy.can_execute && !sys.autonomy.requires_human_approval) {
      violations.push({
        system_id: sys.system_id,
        system_name: sys.name,
        rule_id: "RULE-EXEC-NO-HITL",
        rule_description: "Executable autonomy is active without mandatory human approval.",
        severity: sys.risk_tier === "critical" ? "critical" : "high",
      });
    }

    // Rule 2: Critical risk systems must always require human approval
    if (sys.risk_tier === "critical" && !sys.autonomy.requires_human_approval) {
      violations.push({
        system_id: sys.system_id,
        system_name: sys.name,
        rule_id: "RULE-CRIT-NO-HITL",
        rule_description: "Critical risk system lacks mandatory human-in-the-loop verification.",
        severity: "critical",
      });
    }

    // Rule 3: High or Critical risk system accessing restricted data classification
    if (
      (sys.risk_tier === "high" || sys.risk_tier === "critical") &&
      sys.data_access.classification === "restricted" &&
      !sys.autonomy.requires_human_approval
    ) {
      violations.push({
        system_id: sys.system_id,
        system_name: sys.name,
        rule_id: "RULE-RESTRICTED-DATA-HITL",
        rule_description: "Accesses Restricted-classification data without human gatekeepers.",
        severity: "high",
      });
    }

    // Rule 4: System is active but missing critical controls
    const missingControls = sys.controls.filter((c) => c.status === "missing");
    if (sys.status === "approved" && missingControls.length > 0) {
      violations.push({
        system_id: sys.system_id,
        system_name: sys.name,
        rule_id: "RULE-APPROVED-MISSING-CONTROLS",
        rule_description: `Approved system is active with ${missingControls.length} missing framework controls.`,
        severity: sys.risk_tier === "critical" ? "critical" : sys.risk_tier === "high" ? "high" : "medium",
      });
    }
  });

  return violations;
}
