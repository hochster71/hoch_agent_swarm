import React, { useState } from "react";
import { useGovernanceRegistryStore } from "../../lib/governance/aiSystemRegistry";
import type { AiSystemType, ControlStatus } from "../../lib/governance/governanceTypes";
import { Shield, Plus, CheckCircle, AlertTriangle, AlertCircle } from "lucide-react";
import { frameworkDefinitions } from "../../lib/governance/complianceFrameworks";

export function AiSystemRegistry() {
  const { systems, registerSystem } = useGovernanceRegistryStore();
  const [showAddForm, setShowAddForm] = useState(false);

  // Form State
  const [systemId, setSystemId] = useState("");
  const [name, setName] = useState("");
  const [type, setType] = useState<AiSystemType>("model");
  const [owner, setOwner] = useState("");
  const [description, setDescription] = useState("");
  const [classification, setClassification] = useState<"public" | "internal" | "confidential" | "restricted">("public");
  const [piiAccess, setPiiAccess] = useState(false);
  const [secretAccess, setSecretAccess] = useState(false);
  const [canRecommend, setCanRecommend] = useState(true);
  const [canExecute, setCanExecute] = useState(false);
  const [requiresHumanApproval, setRequiresHumanApproval] = useState(true);
  const [maxExecutionScope, setMaxExecutionScope] = useState("");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!systemId || !name || !owner) {
      alert("Please fill in System ID, Name, and Owner.");
      return;
    }

    // Prepare default controls mapping as missing
    const defaultControls = frameworkDefinitions.map((def) => ({
      control_id: def.control_id,
      framework: def.framework,
      status: "missing" as ControlStatus,
      evidence_refs: [],
    }));

    registerSystem({
      system_id: systemId.toLowerCase().trim().replace(/\s+/g, "-"),
      name,
      type,
      owner,
      description,
      status: "registered",
      capabilities: description ? [description.slice(0, 30)] : ["Generic AI capabilities"],
      data_access: {
        classification,
        pii_access: piiAccess,
        secret_access: secretAccess,
      },
      autonomy: {
        can_recommend: canRecommend,
        can_execute: canExecute,
        requires_human_approval: requiresHumanApproval,
        max_execution_scope: maxExecutionScope || "None",
      },
      controls: defaultControls,
    });

    // Reset Form
    setSystemId("");
    setName("");
    setOwner("");
    setDescription("");
    setMaxExecutionScope("");
    setPiiAccess(false);
    setSecretAccess(false);
    setCanExecute(false);
    setRequiresHumanApproval(true);
    setShowAddForm(false);
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "approved":
        return <span className="status-badge success">Approved</span>;
      case "under_review":
        return <span className="status-badge warn">Under Review</span>;
      case "restricted":
        return <span className="status-badge fail">Restricted</span>;
      case "registered":
        return <span className="status-badge blocked">Registered</span>;
      case "retired":
        return <span className="status-badge blocked">Retired</span>;
      default:
        return <span className="status-badge blocked">{status}</span>;
    }
  };

  const getRiskBadge = (tier: string) => {
    switch (tier) {
      case "critical":
        return <span className="flex items-center gap-1 text-[10px] font-bold text-red-500 font-mono"><AlertCircle className="h-3.5 w-3.5" /> CRITICAL</span>;
      case "high":
        return <span className="flex items-center gap-1 text-[10px] font-bold text-orange-500 font-mono"><AlertTriangle className="h-3.5 w-3.5" /> HIGH</span>;
      case "medium":
        return <span className="flex items-center gap-1 text-[10px] font-bold text-yellow-500 font-mono"><AlertTriangle className="h-3.5 w-3.5" /> MEDIUM</span>;
      case "low":
        return <span className="flex items-center gap-1 text-[10px] font-bold text-green-500 font-mono"><CheckCircle className="h-3.5 w-3.5" /> LOW</span>;
      default:
        return <span className="font-mono text-slate-400">{tier}</span>;
    }
  };

  return (
    <div className="rounded-lg border border-slate-800 bg-slate-950/60 p-4 backdrop-blur-md">
      <div className="mb-4 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Shield className="h-4 w-4 text-cyan-400" />
          <h3 className="font-mono text-sm font-semibold tracking-wider text-slate-200">
            AI CAPABILITY & SYSTEM REGISTRY
          </h3>
        </div>
        <button
          onClick={() => setShowAddForm(!showAddForm)}
          className="flex items-center gap-1 rounded bg-cyan-500/10 hover:bg-cyan-500/20 border border-cyan-500/30 px-2 py-1 text-xs font-mono font-medium text-cyan-400 transition-all"
        >
          <Plus className="h-3 w-3" />
          {showAddForm ? "CLOSE FORM" : "REGISTER SYSTEM"}
        </button>
      </div>

      {showAddForm && (
        <form onSubmit={handleSubmit} className="mb-6 rounded border border-slate-800 bg-slate-950/80 p-4 space-y-3 font-mono text-xs text-slate-300">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            <div>
              <label className="block text-slate-400 mb-1">System ID (unique string)</label>
              <input
                type="text"
                placeholder="e.g. cluster-sentinel"
                value={systemId}
                onChange={(e) => setSystemId(e.target.value)}
                className="w-full rounded border border-slate-700 bg-slate-900 px-2.5 py-1 text-slate-200 focus:outline-none focus:border-cyan-500"
              />
            </div>
            <div>
              <label className="block text-slate-400 mb-1">System Name</label>
              <input
                type="text"
                placeholder="e.g. Cluster Sentinel Agent"
                value={name}
                onChange={(e) => setName(e.target.value)}
                className="w-full rounded border border-slate-700 bg-slate-900 px-2.5 py-1 text-slate-200 focus:outline-none focus:border-cyan-500"
              />
            </div>
            <div>
              <label className="block text-slate-400 mb-1">System Type</label>
              <select
                value={type}
                onChange={(e) => setType(e.target.value as AiSystemType)}
                className="w-full rounded border border-slate-700 bg-slate-900 px-2.5 py-1 text-slate-200 focus:outline-none focus:border-cyan-500"
              >
                <option value="model">Model (Neural Network / LLM)</option>
                <option value="agent">Agent (Autonomous / Semi-Autonomous)</option>
                <option value="swarm">Swarm (Multi-Agent Swarm)</option>
                <option value="tool">Tool (Utility / Sandbox)</option>
                <option value="workflow">Workflow (Sequential Chains)</option>
                <option value="integration">Integration (External API connector)</option>
              </select>
            </div>
            <div>
              <label className="block text-slate-400 mb-1">Owner Team/Department</label>
              <input
                type="text"
                placeholder="e.g. Security Swarm"
                value={owner}
                onChange={(e) => setOwner(e.target.value)}
                className="w-full rounded border border-slate-700 bg-slate-900 px-2.5 py-1 text-slate-200 focus:outline-none focus:border-cyan-500"
              />
            </div>
          </div>

          <div>
            <label className="block text-slate-400 mb-1">Description</label>
            <textarea
              placeholder="Provide summary of model, training details, and intent..."
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              className="w-full h-12 rounded border border-slate-700 bg-slate-900 px-2.5 py-1 text-slate-200 focus:outline-none focus:border-cyan-500 resize-none"
            />
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-3 border-t border-slate-800 pt-3">
            <div>
              <label className="block text-slate-400 mb-1">Data Classification</label>
              <select
                value={classification}
                onChange={(e) => setClassification(e.target.value as any)}
                className="w-full rounded border border-slate-700 bg-slate-900 px-2.5 py-1 text-slate-200 focus:outline-none focus:border-cyan-500"
              >
                <option value="public">Public</option>
                <option value="internal">Internal</option>
                <option value="confidential">Confidential</option>
                <option value="restricted">Restricted (High Sensitivity)</option>
              </select>
            </div>
            <div className="flex items-center gap-2 mt-4">
              <input
                type="checkbox"
                id="piiAccess"
                checked={piiAccess}
                onChange={(e) => setPiiAccess(e.target.checked)}
                className="rounded border-slate-700 bg-slate-900 text-cyan-500"
              />
              <label htmlFor="piiAccess" className="text-slate-400 select-none">Accesses PII Data</label>
            </div>
            <div className="flex items-center gap-2 mt-4">
              <input
                type="checkbox"
                id="secretAccess"
                checked={secretAccess}
                onChange={(e) => setSecretAccess(e.target.checked)}
                className="rounded border-slate-700 bg-slate-900 text-cyan-500"
              />
              <label htmlFor="secretAccess" className="text-slate-400 select-none">Accesses API Secrets</label>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-3 border-t border-slate-800 pt-3">
            <div className="flex items-center gap-2 mt-4">
              <input
                type="checkbox"
                id="canRecommend"
                checked={canRecommend}
                onChange={(e) => setCanRecommend(e.target.checked)}
                className="rounded border-slate-700 bg-slate-900 text-cyan-500"
              />
              <label htmlFor="canRecommend" className="text-slate-400 select-none">Can Recommend Actions</label>
            </div>
            <div className="flex items-center gap-2 mt-4">
              <input
                type="checkbox"
                id="canExecute"
                checked={canExecute}
                onChange={(e) => setCanExecute(e.target.checked)}
                className="rounded border-slate-700 bg-slate-900 text-cyan-500"
              />
              <label htmlFor="canExecute" className="text-slate-400 select-none">Can Execute Code</label>
            </div>
            <div className="flex items-center gap-2 mt-4">
              <input
                type="checkbox"
                id="requiresHumanApproval"
                checked={requiresHumanApproval}
                onChange={(e) => setRequiresHumanApproval(e.target.checked)}
                className="rounded border-slate-700 bg-slate-900 text-cyan-500"
              />
              <label htmlFor="requiresHumanApproval" className="text-slate-400 select-none">Requires Human Approval</label>
            </div>
          </div>

          <div>
            <label className="block text-slate-400 mb-1">Max Execution Scope</label>
            <input
              type="text"
              placeholder="e.g. Execute shell scripts only on W1 nodes"
              value={maxExecutionScope}
              onChange={(e) => setMaxExecutionScope(e.target.value)}
              className="w-full rounded border border-slate-700 bg-slate-900 px-2.5 py-1 text-slate-200 focus:outline-none focus:border-cyan-500"
            />
          </div>

          <div className="flex justify-end pt-2">
            <button
              type="submit"
              className="rounded bg-cyan-500 hover:bg-cyan-600 px-4 py-1 text-xs font-semibold text-slate-950 transition-colors"
            >
              SAVE TO REGISTRY
            </button>
          </div>
        </form>
      )}

      <div className="overflow-x-auto">
        <table className="w-full border-collapse font-mono text-[11px] text-slate-300">
          <thead>
            <tr className="border-b border-slate-800 text-left text-slate-400 uppercase font-semibold tracking-wider">
              <th className="py-2.5 px-3">System / ID</th>
              <th className="py-2.5 px-3">Type</th>
              <th className="py-2.5 px-3">Owner</th>
              <th className="py-2.5 px-3">Risk Tier</th>
              <th className="py-2.5 px-3">Data Access</th>
              <th className="py-2.5 px-3">HITL Gate</th>
              <th className="py-2.5 px-3">Status</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-900">
            {systems.map((sys) => (
              <tr key={sys.system_id} className="hover:bg-slate-900/30 transition-colors">
                <td className="py-3 px-3">
                  <div className="font-semibold text-slate-100">{sys.name}</div>
                  <div className="text-[10px] text-slate-500">{sys.system_id}</div>
                </td>
                <td className="py-3 px-3 uppercase text-[10px] text-cyan-400 font-semibold">{sys.type}</td>
                <td className="py-3 px-3 text-slate-400">{sys.owner}</td>
                <td className="py-3 px-3">{getRiskBadge(sys.risk_tier)}</td>
                <td className="py-3 px-3">
                  <div className="capitalize text-slate-200">{sys.data_access.classification}</div>
                  <div className="text-[9px] text-slate-500">
                    {sys.data_access.pii_access ? "PII" : "No PII"} | {sys.data_access.secret_access ? "Secrets" : "No Secrets"}
                  </div>
                </td>
                <td className="py-3 px-3">
                  {sys.autonomy.requires_human_approval ? (
                    <span className="text-cyan-400">MANDATORY</span>
                  ) : (
                    <span className="text-red-400 font-bold">BYPASSED</span>
                  )}
                </td>
                <td className="py-3 px-3">{getStatusBadge(sys.status)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
