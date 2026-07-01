import type { AiSystemRecord, ControlStatus } from "./governanceTypes";
import { frameworkDefinitions, type ComplianceFrameworkCode } from "./complianceFrameworks";

export type FrameworkCoverageSummary = {
  framework: ComplianceFrameworkCode;
  total: number;
  implemented: number;
  partial: number;
  missing: number;
  coverage_percent: number;
};

export function getFrameworkCoverage(systems: AiSystemRecord[]): FrameworkCoverageSummary[] {
  const frameworks: ComplianceFrameworkCode[] = ["NIST_AI_RMF", "NIST_800_53", "OWASP_SAMM"];
  
  return frameworks.map((fw) => {
    const fwControls = frameworkDefinitions.filter((d) => d.framework === fw);
    let implemented = 0;
    let partial = 0;
    let missing = 0;

    fwControls.forEach((def) => {
      // Find status of this control across all registered systems
      const systemStatuses: ControlStatus[] = [];
      systems.forEach((sys) => {
        const matchingCtrl = sys.controls.find((c) => c.control_id === def.control_id);
        if (matchingCtrl) {
          systemStatuses.push(matchingCtrl.status);
        }
      });

      if (systemStatuses.length === 0) {
        missing++;
      } else if (systemStatuses.every((s) => s === "implemented")) {
        implemented++;
      } else if (systemStatuses.some((s) => s === "implemented" || s === "partial")) {
        partial++;
      } else {
        missing++;
      }
    });

    const total = fwControls.length;
    const coverage_percent = total > 0 
      ? Math.round(((implemented + partial * 0.5) / total) * 100)
      : 0;

    return {
      framework: fw,
      total,
      implemented,
      partial,
      missing,
      coverage_percent,
    };
  });
}
