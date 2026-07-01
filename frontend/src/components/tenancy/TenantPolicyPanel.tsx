import type { TenantRecord } from "../../lib/tenancy/tenantTypes";
import { useTenantStore } from "../../lib/tenancy/tenantRegistry";
import { ShieldAlert, Globe, Settings } from "lucide-react";

type Props = {
  tenant: TenantRecord;
};

export function TenantPolicyPanel({ tenant }: Props) {
  const { updateTenantPolicy } = useTenantStore();

  const handleEnvToggle = (env: "LOCAL" | "DEV" | "STAGING" | "PROD") => {
    const nextEnvs = tenant.policy.allowed_environments.includes(env)
      ? tenant.policy.allowed_environments.filter((e) => e !== env)
      : [...tenant.policy.allowed_environments, env];
    
    updateTenantPolicy(tenant.tenant_id, {
      ...tenant.policy,
      allowed_environments: nextEnvs,
    });
  };

  const handleIntegrationToggle = (integration: string) => {
    const nextIntegrations = tenant.policy.allowed_integrations.includes(integration)
      ? tenant.policy.allowed_integrations.filter((i) => i !== integration)
      : [...tenant.policy.allowed_integrations, integration];

    updateTenantPolicy(tenant.tenant_id, {
      ...tenant.policy,
      allowed_integrations: nextIntegrations,
    });
  };

  const handleResidencyChange = (region: string) => {
    updateTenantPolicy(tenant.tenant_id, {
      ...tenant.policy,
      data_residency_region: region || undefined,
    });
  };

  const handleApprovalToggle = () => {
    updateTenantPolicy(tenant.tenant_id, {
      ...tenant.policy,
      approval_required_for_high_risk: !tenant.policy.approval_required_for_high_risk,
    });
  };

  const envs: ("LOCAL" | "DEV" | "STAGING" | "PROD")[] = ["LOCAL", "DEV", "STAGING", "PROD"];
  const integrations = ["slack", "github", "jira", "teams", "pagerduty"];
  const regions = ["US-East", "US-West", "EU-West", "AP-Southeast", "Other"];

  return (
    <div className="rounded-lg border border-slate-800 bg-slate-950/60 p-4 font-mono text-[11px] space-y-4">
      <h3 className="text-xs font-bold tracking-wider text-slate-400 border-b border-slate-900 pb-2 uppercase flex items-center gap-1.5">
        <ShieldAlert className="h-4 w-4 text-cyan-400" />
        Tenant Security Policy Overrides
      </h3>

      {/* Environments */}
      <div>
        <div className="text-[9px] text-slate-500 uppercase font-bold mb-1.5">Allowed Environments</div>
        <div className="flex gap-2">
          {envs.map((env) => {
            const active = tenant.policy.allowed_environments.includes(env);
            return (
              <button
                key={env}
                type="button"
                onClick={() => handleEnvToggle(env)}
                className={`px-2.5 py-1 rounded text-[10px] font-bold border transition-all ${
                  active
                    ? "bg-cyan-950/20 border-cyan-800/40 text-cyan-400"
                    : "bg-slate-900/30 border-slate-800/60 text-slate-600 hover:border-slate-700/60"
                }`}
              >
                {env}
              </button>
            );
          })}
        </div>
      </div>

      {/* Integrations */}
      <div>
        <div className="text-[9px] text-slate-500 uppercase font-bold mb-1.5 font-mono">Permitted Swarm Integrations</div>
        <div className="flex flex-wrap gap-2">
          {integrations.map((i) => {
            const active = tenant.policy.allowed_integrations.includes(i);
            return (
              <button
                key={i}
                type="button"
                onClick={() => handleIntegrationToggle(i)}
                className={`px-2 py-1 rounded text-[10px] font-bold border capitalize transition-all ${
                  active
                    ? "bg-cyan-950/20 border-cyan-800/40 text-cyan-400"
                    : "bg-slate-900/30 border-slate-800/60 text-slate-600 hover:border-slate-700/60"
                }`}
              >
                {i}
              </button>
            );
          })}
        </div>
      </div>

      {/* Residency */}
      <div>
        <div className="text-[9px] text-slate-500 uppercase font-bold mb-1.5">Data Residency Regulation</div>
        <select
          value={tenant.policy.data_residency_region || ""}
          onChange={e => handleResidencyChange(e.target.value)}
          className="bg-slate-900 border border-slate-800 rounded px-2 py-1.5 outline-none text-slate-300 focus:border-cyan-500 w-full"
        >
          <option value="">No Residency Constraint</option>
          {regions.map((r) => (
            <option key={r} value={r}>{r}</option>
          ))}
        </select>
      </div>

      {/* Dual approvals */}
      <div className="flex items-center justify-between p-2.5 rounded bg-slate-900/30 border border-slate-900">
        <div>
          <div className="font-bold text-slate-200">Require High-Risk Approvals</div>
          <div className="text-[9px] text-slate-500 mt-0.5 font-mono">Forces manual dual-authorization gates.</div>
        </div>
        <input
          type="checkbox"
          checked={tenant.policy.approval_required_for_high_risk}
          onChange={handleApprovalToggle}
          className="h-4 w-4 rounded accent-cyan-500 bg-slate-900 border-slate-800 cursor-pointer"
        />
      </div>

    </div>
  );
}
