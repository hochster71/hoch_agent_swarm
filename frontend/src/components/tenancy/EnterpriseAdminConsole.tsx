import { useState } from "react";
import { useTenantStore } from "../../lib/tenancy/tenantRegistry";
import type { TenantRecord, TenantStatus, TenantPlan } from "../../lib/tenancy/tenantTypes";
import { TenantRegistry } from "./TenantRegistry";
import { TenantDetailPanel } from "./TenantDetailPanel";
import { TenantUserManagement } from "./TenantUserManagement";
import { TenantPolicyPanel } from "./TenantPolicyPanel";
import { TenantAuditLog } from "./TenantAuditLog";
import { TenantQuotaPanel } from "./TenantQuotaPanel";
import { TenantUsageDashboard } from "./TenantUsageDashboard";
import { TenantIsolationStatus } from "./TenantIsolationStatus";
import { useAuditStore } from "../../lib/audit/auditStore";
import {
  Globe,
  Users,
  ShieldCheck,
  Server,
  Lock,
  Layers,
  Activity,
  History,
  FileText,
  MapPin,
  TrendingUp,
  Sliders,
  CheckCircle2,
  AlertTriangle,
  Plus
} from "lucide-react";

export function EnterpriseAdminConsole() {
  const { tenants, activeTenant, selectTenant, registerTenant } = useTenantStore();
  const { events } = useAuditStore();
  
  const [showOnboardForm, setShowOnboardForm] = useState(false);
  const [newName, setNewName] = useState("");
  const [newId, setNewId] = useState("");
  const [newPlan, setNewPlan] = useState<TenantPlan>("enterprise");
  
  const handleOnboard = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newName || !newId) {
      alert("Name and Tenant ID are required.");
      return;
    }
    
    registerTenant({
      tenant_id: newId.toLowerCase().trim().replace(/\s+/g, "-"),
      name: newName,
      plan: newPlan,
      admins: [
        { user_id: `usr-${newId}-admin`, name: "System Admin", email: `admin@${newId}.com` }
      ],
      isolation: {
        namespace: `${newId}-namespace`,
        data_partition_key: `part-${newId}-key`,
        dedicated_runtime: true,
        dedicated_key_material: newPlan === "regulated",
        cross_tenant_access_allowed: false
      },
      quotas: {
        max_users: 100,
        max_agents: 20,
        max_events_per_day: 1000000,
        max_integrations: 10,
        max_storage_gb: 500
      },
      policy: {
        allowed_environments: ["DEV", "STAGING"],
        allowed_integrations: ["slack"],
        approval_required_for_high_risk: true
      }
    });

    setNewName("");
    setNewId("");
    setShowOnboardForm(false);
  };

  // Filter audit events
  const tenantEvents = events.filter((e) => 
    e.action.type.startsWith("TENANT_")
  ).slice(0, 5);

  // Platform metrics
  const totalTenantsCount = tenants.length;
  const activeTenantsCount = tenants.filter(t => t.status === "active").length;
  const totalUsersCount = tenants.reduce((acc, t) => acc + t.usage.users, 0);
  const totalEnvironmentsCount = 96; 
  const platformHealth = "Healthy";

  return (
    <div className="p-6 space-y-6 max-h-[calc(100vh-120px)] overflow-y-auto w-full text-slate-200">
      
      {/* View Header */}
      <div className="flex items-center justify-between border-b border-slate-900 pb-3">
        <div>
          <div className="flex items-center gap-2">
            <span className="bg-purple-950 border border-purple-800 text-purple-400 text-[10px] font-bold px-2 py-0.5 rounded font-mono">PHASE 18</span>
            <h1 className="text-xl font-bold tracking-wider font-mono text-slate-100 flex items-center gap-2">
              <Globe className="h-5 w-5 text-cyan-400" />
              Multi-Tenant Enterprise Deployment & Customer Admin Console
            </h1>
          </div>
          <p className="text-xs text-slate-500 font-mono mt-1">
            Isolate, govern, and operate at scale across tenants, teams, environments, and regions.
          </p>
        </div>
        <div>
          <span className="bg-emerald-950/40 border border-emerald-800/40 text-emerald-400 text-[10px] font-mono px-2 py-1 rounded font-bold uppercase animate-pulse">
            Enterprise Mode: Active
          </span>
        </div>
      </div>

      {/* Platform Overview Cards Grid */}
      <div className="grid grid-cols-2 lg:grid-cols-5 gap-4 font-mono text-xs">
        <div className="rounded-lg border border-slate-800 bg-slate-950/40 p-4">
          <div className="flex items-center justify-between text-slate-500">
            <span>TOTAL TENANTS</span>
            <Layers className="h-4 w-4 text-cyan-500" />
          </div>
          <div className="text-2xl font-bold text-slate-200 mt-2">{totalTenantsCount}</div>
          <div className="text-[9px] text-green-400 mt-1">▲ +3 this month</div>
        </div>

        <div className="rounded-lg border border-slate-800 bg-slate-950/40 p-4">
          <div className="flex items-center justify-between text-slate-500">
            <span>ACTIVE TENANTS</span>
            <CheckCircle2 className="h-4 w-4 text-green-500" />
          </div>
          <div className="text-2xl font-bold text-green-500 mt-2">{activeTenantsCount}</div>
          <div className="text-[9px] text-slate-600 mt-1">87% Active state</div>
        </div>

        <div className="rounded-lg border border-slate-800 bg-slate-950/40 p-4">
          <div className="flex items-center justify-between text-slate-500">
            <span>TOTAL USERS</span>
            <Users className="h-4 w-4 text-purple-500" />
          </div>
          <div className="text-2xl font-bold text-slate-200 mt-2">{totalUsersCount}</div>
          <div className="text-[9px] text-green-400 mt-1">▲ +42 this month</div>
        </div>

        <div className="rounded-lg border border-slate-800 bg-slate-950/40 p-4">
          <div className="flex items-center justify-between text-slate-500">
            <span>ENVIRONMENTS</span>
            <Server className="h-4 w-4 text-orange-500" />
          </div>
          <div className="text-2xl font-bold text-slate-200 mt-2">{totalEnvironmentsCount}</div>
          <div className="text-[9px] text-slate-600 mt-1">Across all tenants</div>
        </div>

        <div className="rounded-lg border border-slate-800 bg-slate-950/40 p-4">
          <div className="flex items-center justify-between text-slate-500">
            <span>HEALTH STATUS</span>
            <Activity className="h-4 w-4 text-emerald-400" />
          </div>
          <div className="text-2xl font-bold text-emerald-400 mt-2">{platformHealth}</div>
          <div className="text-[9px] text-slate-600 mt-1">All Systems Operational</div>
        </div>
      </div>

      {/* Toolbar */}
      <div className="flex justify-end p-2.5 rounded-lg bg-slate-900/20 border border-slate-800">
        <button
          onClick={() => setShowOnboardForm(!showOnboardForm)}
          className="flex items-center gap-1.5 px-4 py-2 rounded text-[11px] font-mono font-bold bg-cyan-500 text-slate-950 hover:bg-cyan-400 transition-all"
        >
          <Plus className="h-4 w-4" />
          Onboard New Tenant
        </button>
      </div>

      {/* Onboard Form (Toggleable) */}
      {showOnboardForm && (
        <form onSubmit={handleOnboard} className="p-4 rounded-lg border border-slate-800 bg-slate-950/60 font-mono text-[11px] space-y-4 max-w-lg">
          <h3 className="text-xs font-bold text-cyan-400 uppercase flex items-center gap-1">
            <Plus className="h-4 w-4" /> Onboard Enterprise Tenant
          </h3>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-slate-500 mb-1">Company Name</label>
              <input
                type="text"
                placeholder="e.g. Stark Industries"
                value={newName}
                onChange={e => setNewName(e.target.value)}
                className="w-full bg-slate-900 border border-slate-800 rounded px-2 py-1.5 outline-none focus:border-cyan-500 text-slate-200"
              />
            </div>
            <div>
              <label className="block text-slate-500 mb-1">Tenant Unique ID</label>
              <input
                type="text"
                placeholder="e.g. stark-ind"
                value={newId}
                onChange={e => setNewId(e.target.value)}
                className="w-full bg-slate-900 border border-slate-800 rounded px-2 py-1.5 outline-none focus:border-cyan-500 text-slate-200"
              />
            </div>
          </div>
          <div>
            <label className="block text-slate-500 mb-1">Plan</label>
            <select
              value={newPlan}
              onChange={e => setNewPlan(e.target.value as TenantPlan)}
              className="w-full bg-slate-900 border border-slate-800 rounded px-2 py-1.5 outline-none focus:border-cyan-500 text-slate-200 animate-none"
            >
              <option value="pilot">Pilot Plan</option>
              <option value="enterprise">Enterprise Plan</option>
              <option value="regulated">Regulated (Dedicated HSM Keys)</option>
            </select>
          </div>
          <div className="flex justify-end gap-2 pt-2 border-t border-slate-900">
            <button
              type="button"
              onClick={() => setShowOnboardForm(false)}
              className="px-3 py-1.5 rounded border border-slate-800 text-slate-400 hover:text-slate-200"
            >
              Cancel
            </button>
            <button
              type="submit"
              className="px-4 py-1.5 rounded bg-cyan-500 text-slate-950 font-bold hover:bg-cyan-400"
            >
              Initialize Tenant
            </button>
          </div>
        </form>
      )}

      {/* Main Grid Layout */}
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
        
        {/* Left Column: Tenant Registry + Health Map */}
        <div className="space-y-6">
          <TenantRegistry onSelect={(t) => selectTenant(t.tenant_id)} selectedId={activeTenant?.tenant_id} />
          
          {/* Tenant Health Map placeholder card */}
          <div className="rounded-lg border border-slate-800 bg-slate-950/40 p-4 font-mono text-[11px] space-y-2">
            <h3 className="text-xs font-bold tracking-wider text-slate-400 uppercase border-b border-slate-900 pb-2 flex items-center gap-1.5">
              <MapPin className="h-4 w-4 text-cyan-400" />
              Tenant Geolocation Health Map
            </h3>
            <div className="h-44 bg-slate-900/30 rounded border border-slate-900/80 flex flex-col justify-center items-center text-slate-600 relative overflow-hidden">
              <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,rgba(59,130,246,0.06),transparent_70%)]" />
              <Globe className="h-10 w-10 text-slate-700 animate-spin-slow mb-2" />
              <span className="text-[10px] text-slate-500 font-bold">Active Regional Nodes</span>
              <div className="flex gap-4 mt-3 text-[9px] font-bold">
                <span className="text-green-500">● US-East: Active</span>
                <span className="text-green-500">● EU-West: Active</span>
                <span className="text-green-500">● AP-Southeast: Active</span>
              </div>
            </div>
          </div>
        </div>

        {/* Center Column: Tenant Details, Quotas, Policies */}
        <div className="space-y-6">
          {activeTenant ? (
            <>
              <TenantDetailPanel tenant={activeTenant} />
              <TenantQuotaPanel tenant={activeTenant} />
              <TenantPolicyPanel tenant={activeTenant} />
            </>
          ) : (
            <div className="rounded-lg border border-slate-800 bg-slate-950/40 p-6 text-center text-slate-500 font-mono text-[11px]">
              Select a tenant to view details, quotas, and policies.
            </div>
          )}
        </div>

        {/* Right Column: User Management, Isolation, Events */}
        <div className="space-y-6">
          {activeTenant && (
            <>
              <TenantUsageDashboard tenant={activeTenant} />
              <TenantIsolationStatus tenant={activeTenant} />
              <TenantUserManagement tenant={activeTenant} />
              <TenantAuditLog tenant={activeTenant} />
            </>
          )}

          {/* Compliance Checklist */}
          <div className="rounded-lg border border-slate-800 bg-slate-950/40 p-4 font-mono text-[11px] space-y-3">
            <h3 className="text-xs font-bold tracking-wider text-slate-400 uppercase border-b border-slate-900 pb-2">
              Compliance Standard Matrices
            </h3>
            <div className="space-y-2">
              {[
                { name: "NIST SP 800-53 Rev. 5", pct: 78, status: "Compliant" },
                { name: "NIST AI Risk Management Framework", pct: 72, status: "Compliant" },
                { name: "SOC 2 Type II Security Trust", pct: 81, status: "Compliant" },
                { name: "ISO/IEC 27001 ISMS standard", pct: 74, status: "Compliant" },
                { name: "GDPR Data Isolation regulation", pct: 69, status: "Compliant" }
              ].map((c, idx) => (
                <div key={idx} className="space-y-1">
                  <div className="flex justify-between items-center text-[10px]">
                    <span className="text-slate-300 font-bold">{c.name}</span>
                    <span className="text-green-400 font-bold">{c.pct}% Passed</span>
                  </div>
                  <div className="w-full bg-slate-900 rounded-full h-1">
                    <div className="h-1 rounded-full bg-green-500" style={{ width: `${c.pct}%` }} />
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Recent Tenant Events log */}
          <div className="rounded-lg border border-slate-800 bg-slate-950/40 p-4 font-mono text-[11px] space-y-3">
            <h3 className="text-xs font-bold tracking-wider text-slate-400 uppercase border-b border-slate-900 pb-2 flex items-center gap-1.5">
              <History className="h-4 w-4 text-cyan-400" />
              Platform Tenant Lifecycle Log
            </h3>
            <div className="space-y-2 max-h-[160px] overflow-y-auto pr-1">
              {tenantEvents.length === 0 ? (
                <div className="text-slate-600 italic">No tenant lifecycle events logged.</div>
              ) : (
                tenantEvents.map((evt, idx) => (
                  <div key={idx} className="p-2 bg-slate-900/20 border border-slate-900/40 rounded flex flex-col gap-1">
                    <div className="flex justify-between items-center text-[9px]">
                      <span className="text-cyan-400 font-bold uppercase">{evt.action.type.replace("TENANT_", "")}</span>
                      <span className="text-slate-500">{new Date(evt.timestamp).toLocaleTimeString()}</span>
                    </div>
                    <span className="text-slate-300 text-[10px]">{evt.action.summary}</span>
                  </div>
                ))
              )}
            </div>
          </div>

        </div>

      </div>

    </div>
  );
}
