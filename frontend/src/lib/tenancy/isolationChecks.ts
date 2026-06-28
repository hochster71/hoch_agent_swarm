import type { TenantRecord } from "./tenantTypes";

export function evaluateTenantIsolation(tenant: TenantRecord): {
  passed: boolean;
  findings: string[];
} {
  const findings: string[] = [];
  if (tenant.isolation.cross_tenant_access_allowed) {
    findings.push("Cross-tenant access is enabled.");
  }
  if (!tenant.isolation.namespace) {
    findings.push("Tenant namespace is missing.");
  }
  if (!tenant.isolation.data_partition_key) {
    findings.push("Tenant data partition key is missing.");
  }
  if (
    tenant.plan === "regulated" &&
    !tenant.isolation.dedicated_key_material
  ) {
    findings.push("Regulated tenants require dedicated key material.");
  }
  return {
    passed: findings.length === 0,
    findings,
  };
}
