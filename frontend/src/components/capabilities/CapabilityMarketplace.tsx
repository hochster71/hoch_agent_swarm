import React, { useState } from "react";
import { useCapabilityRegistryStore } from "../../lib/capabilities/capabilityRegistry";
import type { CapabilityRecord, CapabilityKind, CapabilityStatus, CapabilityRisk } from "../../lib/capabilities/capabilityTypes";
import { AgentRegistry } from "./AgentRegistry";
import { SkillRegistry } from "./SkillRegistry";
import { ToolRegistry } from "./ToolRegistry";
import { CapabilityDetailPanel } from "./CapabilityDetailPanel";
import { useAuditStore } from "../../lib/audit/auditStore";
import {
  Grid,
  Search,
  Filter,
  Plus,
  Cpu,
  Hammer,
  Wrench,
  Globe,
  GitFork,
  Network,
  ShieldCheck,
  Activity,
  ArrowUpRight,
  PlusCircle,
  HelpCircle,
  FileCode,
  Flame,
  CheckCircle,
  AlertTriangle,
  History,
  Info
} from "lucide-react";

export function CapabilityMarketplace() {
  const { capabilities, registerCapability } = useCapabilityRegistryStore();
  const { events } = useAuditStore();

  const [selectedCap, setSelectedCap] = useState<CapabilityRecord | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [filterKind, setFilterKind] = useState<string>("all");
  const [filterRisk, setFilterRisk] = useState<string>("all");
  const [filterStatus, setFilterStatus] = useState<string>("all");
  
  // Publish Form State
  const [showPublishForm, setShowPublishForm] = useState(false);
  const [newName, setNewName] = useState("");
  const [newKind, setNewKind] = useState<CapabilityKind>("agent");
  const [newVersion, setNewVersion] = useState("v1.0.0");
  const [newOwner, setNewOwner] = useState("SecOps Team");
  const [newDesc, setNewDesc] = useState("");
  const [newTags, setNewTags] = useState("");
  
  const handlePublish = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newName || !newDesc) {
      alert("Name and description are required.");
      return;
    }
    
    registerCapability({
      capability_id: newName.toLowerCase().trim().replace(/\s+/g, "-"),
      name: newName,
      kind: newKind,
      version: newVersion,
      owner: newOwner,
      status: "draft",
      description: newDesc,
      tags: newTags ? newTags.split(",").map(t => t.trim()) : [],
      permissions: {
        filesystem: false,
        network: false,
        email: false,
        calendar: false,
        browser: false,
        shell: false,
        secrets: false,
        external_write: false
      },
      guardrails: {
        requires_human_approval: true,
        allowed_environments: ["DEV"],
        blocked_actions: [],
        max_autonomy_level: "recommend"
      }
    });

    setNewName("");
    setNewDesc("");
    setNewTags("");
    setShowPublishForm(false);
  };

  // Filter capabilities
  const filtered = capabilities.filter((c) => {
    const matchesSearch = c.name.toLowerCase().includes(searchQuery.toLowerCase()) || 
                          c.description.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesKind = filterKind === "all" || c.kind === filterKind;
    const matchesRisk = filterRisk === "all" || c.risk === filterRisk;
    const matchesStatus = filterStatus === "all" || c.status === filterStatus;
    return matchesSearch && matchesKind && matchesRisk && matchesStatus;
  });

  // Category counts
  const countKind = (kind: CapabilityKind) => capabilities.filter(c => c.kind === kind).length;
  const countStatus = (status: CapabilityStatus) => capabilities.filter(c => c.status === status).length;
  
  // Total capability counts (add hardcoded mock values to match exact image dashboard 260 total)
  const totalCaps = 260; 
  const approvedCapsCount = 182;
  const testingCapsCount = 42;
  const restrictedCapsCount = 18;
  const deprecatedCapsCount = 10;
  const retiredCapsCount = 8;

  // Filter audit events
  const capabilityEvents = events.filter((e) => 
    e.action.type.startsWith("CAPABILITY_")
  ).slice(0, 5);

  const pendingApprovals = capabilities.filter(c => c.status === "draft" || c.status === "testing").slice(0, 5);

  return (
    <div className="p-6 space-y-6 max-h-[calc(100vh-120px)] overflow-y-auto w-full text-slate-200">
      
      {/* View Header */}
      <div className="flex items-center justify-between border-b border-slate-900 pb-3">
        <div>
          <div className="flex items-center gap-2">
            <span className="bg-purple-950 border border-purple-800 text-purple-400 text-[10px] font-bold px-2 py-0.5 rounded font-mono">PHASE 16</span>
            <h1 className="text-xl font-bold tracking-wider font-mono text-slate-100 flex items-center gap-2">
              <Grid className="h-5 w-5 text-cyan-400" />
              Agent Marketplace, Capability Registry & Skill Lifecycle
            </h1>
          </div>
          <p className="text-xs text-slate-500 font-mono mt-1">
            Discover, govern, and lifecycle-manage agents, skills, tools, and capabilities.
          </p>
        </div>
        <div>
          <span className="bg-emerald-950/40 border border-emerald-800/40 text-emerald-400 text-[10px] font-mono px-2 py-1 rounded font-bold uppercase animate-pulse">
            Marketplace Active
          </span>
        </div>
      </div>

      {/* Top Categories Row */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4 font-mono text-xs">
        {[
          { label: "Agents", count: 32, activeCount: countKind("agent"), icon: Cpu, color: "text-purple-400" },
          { label: "Skills", count: 68, activeCount: countKind("skill"), icon: Hammer, color: "text-blue-400" },
          { label: "Tools", count: 112, activeCount: capabilities.filter(c => c.kind === "tool").length, icon: Wrench, color: "text-emerald-400" },
          { label: "Connectors", count: 24, activeCount: capabilities.filter(c => c.kind === "connector").length, icon: Globe, color: "text-orange-400" },
          { label: "Workflows", count: 16, activeCount: capabilities.filter(c => c.kind === "workflow").length, icon: GitFork, color: "text-indigo-400" },
          { label: "Swarm Packs", count: 8, activeCount: capabilities.filter(c => c.kind === "swarm").length, icon: Network, color: "text-pink-400" }
        ].map((cat, i) => {
          const Icon = cat.icon;
          return (
            <div key={i} className="rounded-lg border border-slate-800 bg-slate-950/40 p-3 flex items-center justify-between">
              <div>
                <span className="text-[10px] text-slate-500 uppercase">{cat.label}</span>
                <div className="text-xl font-bold text-slate-200 mt-1">{cat.count}</div>
                <div className="text-[9px] text-slate-600 mt-0.5">{cat.activeCount} active registry</div>
              </div>
              <Icon className={`h-8 w-8 ${cat.color} opacity-40`} />
            </div>
          );
        })}
      </div>

      {/* Search & Publish Toolbar */}
      <div className="flex flex-col md:flex-row gap-3 items-center justify-between p-3 rounded-lg bg-slate-900/20 border border-slate-800">
        <div className="flex flex-1 w-full md:w-auto items-center gap-3">
          <div className="relative flex-1 max-w-xs">
            <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-slate-500" />
            <input
              type="text"
              placeholder="Search capabilities..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full bg-slate-950 border border-slate-800 rounded pl-9 pr-3 py-2 text-[11px] font-mono outline-none text-slate-300 focus:border-cyan-500"
            />
          </div>
          
          <select
            value={filterKind}
            onChange={(e) => setFilterKind(e.target.value)}
            className="bg-slate-950 border border-slate-800 rounded px-2 py-2 text-[11px] font-mono outline-none text-slate-400 focus:border-cyan-500"
          >
            <option value="all">All Kinds</option>
            <option value="agent">Agents</option>
            <option value="skill">Skills</option>
            <option value="tool">Tools</option>
            <option value="connector">Connectors</option>
            <option value="workflow">Workflows</option>
            <option value="swarm">Swarms</option>
          </select>

          <select
            value={filterRisk}
            onChange={(e) => setFilterRisk(e.target.value)}
            className="bg-slate-950 border border-slate-800 rounded px-2 py-2 text-[11px] font-mono outline-none text-slate-400 focus:border-cyan-500"
          >
            <option value="all">All Risk</option>
            <option value="low">Low Risk</option>
            <option value="medium">Medium Risk</option>
            <option value="high">High Risk</option>
            <option value="critical">Critical Risk</option>
          </select>

          <select
            value={filterStatus}
            onChange={(e) => setFilterStatus(e.target.value)}
            className="bg-slate-950 border border-slate-800 rounded px-2 py-2 text-[11px] font-mono outline-none text-slate-400 focus:border-cyan-500"
          >
            <option value="all">All Status</option>
            <option value="draft">Draft</option>
            <option value="testing">Testing</option>
            <option value="approved">Approved</option>
            <option value="restricted">Restricted</option>
            <option value="deprecated">Deprecated</option>
            <option value="retired">Retired</option>
          </select>
        </div>

        <button
          onClick={() => setShowPublishForm(!showPublishForm)}
          className="flex items-center gap-1.5 px-4 py-2 rounded text-[11px] font-mono font-bold bg-cyan-500 text-slate-950 hover:bg-cyan-400 transition-all border border-transparent"
        >
          <Plus className="h-4 w-4" />
          Publish Capability
        </button>
      </div>

      {/* Publish Form (Toggleable) */}
      {showPublishForm && (
        <form onSubmit={handlePublish} className="p-4 rounded-lg border border-slate-800 bg-slate-950/60 font-mono text-[11px] space-y-4 max-w-lg">
          <h3 className="text-xs font-bold text-cyan-400 uppercase flex items-center gap-1">
            <PlusCircle className="h-4 w-4" /> Register New Swarm Capability
          </h3>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-slate-500 mb-1">Capability Name</label>
              <input
                type="text"
                placeholder="e.g. Host Scanner"
                value={newName}
                onChange={e => setNewName(e.target.value)}
                className="w-full bg-slate-900 border border-slate-800 rounded px-2 py-1.5 outline-none focus:border-cyan-500 text-slate-200"
              />
            </div>
            <div>
              <label className="block text-slate-500 mb-1">Kind</label>
              <select
                value={newKind}
                onChange={e => setNewKind(e.target.value as CapabilityKind)}
                className="w-full bg-slate-900 border border-slate-800 rounded px-2 py-1.5 outline-none focus:border-cyan-500 text-slate-200"
              >
                <option value="agent">Agent</option>
                <option value="skill">Skill</option>
                <option value="tool">Tool</option>
                <option value="connector">Connector</option>
                <option value="workflow">Workflow</option>
                <option value="swarm">Swarm Pack</option>
              </select>
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-slate-500 mb-1">Version</label>
              <input
                type="text"
                value={newVersion}
                onChange={e => setNewVersion(e.target.value)}
                className="w-full bg-slate-900 border border-slate-800 rounded px-2 py-1.5 outline-none focus:border-cyan-500 text-slate-200"
              />
            </div>
            <div>
              <label className="block text-slate-500 mb-1">Owner Team</label>
              <input
                type="text"
                value={newOwner}
                onChange={e => setNewOwner(e.target.value)}
                className="w-full bg-slate-900 border border-slate-800 rounded px-2 py-1.5 outline-none focus:border-cyan-500 text-slate-200"
              />
            </div>
          </div>
          <div>
            <label className="block text-slate-500 mb-1">Description</label>
            <textarea
              placeholder="Describe capability functions, parameters, and design scope..."
              value={newDesc}
              onChange={e => setNewDesc(e.target.value)}
              className="w-full bg-slate-900 border border-slate-800 rounded px-2 py-1.5 outline-none focus:border-cyan-500 text-slate-200 h-16 resize-none"
            />
          </div>
          <div>
            <label className="block text-slate-500 mb-1">Tags (comma-separated)</label>
            <input
              type="text"
              placeholder="e.g. security, utility, scan"
              value={newTags}
              onChange={e => setNewTags(e.target.value)}
              className="w-full bg-slate-900 border border-slate-800 rounded px-2 py-1.5 outline-none focus:border-cyan-500 text-slate-200"
            />
          </div>
          <div className="flex justify-end gap-2 pt-2 border-t border-slate-900">
            <button
              type="button"
              onClick={() => setShowPublishForm(false)}
              className="px-3 py-1.5 rounded border border-slate-800 text-slate-400 hover:text-slate-200"
            >
              Cancel
            </button>
            <button
              type="submit"
              className="px-4 py-1.5 rounded bg-cyan-500 text-slate-950 font-bold hover:bg-cyan-400"
            >
              Submit Registry
            </button>
          </div>
        </form>
      )}

      {/* Main Content Layout */}
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
        
        {/* Left/Middle Column (Registries + Featured) */}
        <div className="xl:col-span-2 space-y-6">
          
          {/* Featured Capabilities Grid */}
          <div className="rounded-lg border border-slate-800 bg-slate-950/40 p-4 font-mono text-[11px]">
            <div className="flex items-center justify-between border-b border-slate-900 pb-2 mb-3">
              <h3 className="text-xs font-bold tracking-wider text-slate-400 uppercase flex items-center gap-1.5">
                <ArrowUpRight className="h-4 w-4 text-cyan-400" />
                Featured Capabilities
              </h3>
              <span className="text-[10px] text-slate-500">Curated Swarm Catalog</span>
            </div>
            
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {filtered.slice(0, 4).map((cap) => {
                const getRiskBadge = (r: CapabilityRisk) => {
                  switch (r) {
                    case "critical": return "text-red-500 bg-red-950/30 border-red-900/50";
                    case "high": return "text-orange-500 bg-orange-950/30 border-orange-900/50";
                    case "medium": return "text-yellow-500 bg-yellow-950/30 border-yellow-900/50";
                    default: return "text-green-500 bg-green-950/30 border-green-900/50";
                  }
                };
                
                const getStatusBadge = (s: CapabilityStatus) => {
                  switch (s) {
                    case "approved": return "text-green-400 bg-green-950/20 border-green-900/30";
                    case "restricted": return "text-red-400 bg-red-950/20 border-red-900/30";
                    case "testing": return "text-blue-400 bg-blue-950/20 border-blue-900/30 animate-pulse";
                    case "deprecated": return "text-orange-400 bg-orange-950/20 border-orange-900/30";
                    default: return "text-slate-400 bg-slate-900/40 border-slate-800/40";
                  }
                };

                return (
                  <div
                    key={cap.capability_id}
                    onClick={() => setSelectedCap(cap)}
                    className="p-4 rounded border border-slate-800/80 bg-slate-900/10 hover:bg-slate-900/30 cursor-pointer transition-all flex flex-col justify-between h-36"
                  >
                    <div>
                      <div className="flex items-center justify-between">
                        <span className="text-[9px] text-slate-500 font-bold uppercase">{cap.kind}</span>
                        <span className={`text-[8px] font-bold uppercase border px-1.5 rounded ${getRiskBadge(cap.risk)}`}>
                          Risk: {cap.risk}
                        </span>
                      </div>
                      <h4 className="font-bold text-slate-100 mt-1">{cap.name}</h4>
                      <p className="text-[10px] text-slate-500 line-clamp-2 mt-1 leading-relaxed">{cap.description}</p>
                    </div>
                    
                    <div className="flex items-center justify-between border-t border-slate-900/80 pt-2 text-[9px] text-slate-500">
                      <div className="flex items-center gap-2">
                        <span className={`border px-1.5 rounded uppercase font-bold text-[8px] ${getStatusBadge(cap.status)}`}>
                          {cap.status}
                        </span>
                        <span>{cap.version}</span>
                      </div>
                      <div className="font-bold text-slate-400">
                        {cap.telemetry.executions_30d >= 1000 ? `${(cap.telemetry.executions_30d/1000).toFixed(1)}K` : cap.telemetry.executions_30d} execs
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Registries lists */}
          <AgentRegistry onSelect={setSelectedCap} selectedId={selectedCap?.capability_id} />
          <SkillRegistry onSelect={setSelectedCap} selectedId={selectedCap?.capability_id} />
          <ToolRegistry onSelect={setSelectedCap} selectedId={selectedCap?.capability_id} />

        </div>

        {/* Right Column (Summaries, Telemetry, Audits) */}
        <div className="space-y-6">
          
          {/* Selected details view */}
          {selectedCap ? (
            <CapabilityDetailPanel capability={selectedCap} onClose={() => setSelectedCap(null)} />
          ) : (
            <div className="rounded-lg border border-slate-800 bg-slate-950/40 p-6 font-mono text-[11px] text-center text-slate-500 flex flex-col items-center justify-center min-h-[300px]">
              <Info className="h-8 w-8 text-slate-600 mb-2 animate-bounce" />
              <span>Select a capability or registry item to view risk metrics, permission scope, test results, and lifecycle controls.</span>
            </div>
          )}

          {/* Capability Registry Summary */}
          <div className="rounded-lg border border-slate-800 bg-slate-950/40 p-4 font-mono text-[11px]">
            <h3 className="text-xs font-bold tracking-wider text-slate-400 mb-3 uppercase flex items-center justify-between border-b border-slate-900 pb-2">
              <span>Capability Registry Summary</span>
              <span className="text-[10px] text-emerald-400 font-bold">+18 this week</span>
            </h3>

            <div className="grid grid-cols-2 gap-4">
              <div className="p-3 bg-slate-900/20 border border-slate-900 rounded">
                <span className="text-slate-500 block text-[9px] uppercase">Total Capabilities</span>
                <span className="text-2xl font-bold text-slate-200 mt-1">{totalCaps}</span>
              </div>
              <div className="p-3 bg-slate-900/20 border border-slate-900 rounded">
                <span className="text-slate-500 block text-[9px] uppercase">Approved Status</span>
                <span className="text-2xl font-bold text-green-400 mt-1">{approvedCapsCount}</span>
                <span className="text-[9px] text-slate-600 block mt-0.5">70% of registry</span>
              </div>
            </div>

            <div className="space-y-2 mt-4">
              {[
                { label: "Approved", count: approvedCapsCount, percent: "70%", color: "bg-green-500" },
                { label: "Testing", count: testingCapsCount, percent: "16%", color: "bg-blue-500" },
                { label: "Restricted", count: restrictedCapsCount, percent: "7%", color: "bg-red-500" },
                { label: "Deprecated", count: deprecatedCapsCount, percent: "4%", color: "bg-orange-500" },
                { label: "Retired", count: retiredCapsCount, percent: "3%", color: "bg-slate-500" }
              ].map((item, idx) => (
                <div key={idx} className="flex items-center justify-between text-[10px] text-slate-400">
                  <span className="flex items-center gap-1.5">
                    <span className={`h-2 w-2 rounded-full ${item.color}`} />
                    {item.label}
                  </span>
                  <div className="flex items-center gap-2">
                    <span className="font-bold text-slate-200">{item.count}</span>
                    <span className="text-slate-600">({item.percent})</span>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Risk Distribution Chart Card */}
          <div className="rounded-lg border border-slate-800 bg-slate-950/40 p-4 font-mono text-[11px]">
            <h3 className="text-xs font-bold tracking-wider text-slate-400 mb-3 uppercase border-b border-slate-900 pb-2">
              Risk Distribution Profiles
            </h3>
            <div className="space-y-3">
              {[
                { label: "Low Threat Profile", count: 92, percent: 35, color: "bg-green-500" },
                { label: "Medium Threat Profile", count: 88, percent: 34, color: "bg-yellow-500" },
                { label: "High Threat Profile", count: 56, percent: 22, color: "bg-orange-500" },
                { label: "Critical Threat Profile", count: 24, percent: 9, color: "bg-red-500" }
              ].map((item, idx) => (
                <div key={idx} className="space-y-1">
                  <div className="flex justify-between text-[10px]">
                    <span className="text-slate-400">{item.label}</span>
                    <span className="text-slate-200 font-bold">{item.count} ({item.percent}%)</span>
                  </div>
                  <div className="w-full bg-slate-900 rounded-full h-1.5">
                    <div className={`h-1.5 rounded-full ${item.color}`} style={{ width: `${item.percent}%` }} />
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Test Suite stats */}
          <div className="rounded-lg border border-slate-800 bg-slate-950/40 p-4 font-mono text-[11px]">
            <h3 className="text-xs font-bold tracking-wider text-slate-400 mb-3 uppercase border-b border-slate-900 pb-2 flex items-center gap-1">
              <ShieldCheck className="h-4 w-4 text-green-400" />
              Capability Test Suite Metrics
            </h3>
            <div className="grid grid-cols-2 md:grid-cols-5 gap-2">
              {[
                { name: "Sandbox", count: "214/234", pass: "91%" },
                { name: "Perms", count: "188/212", pass: "88%" },
                { name: "Integ", count: "176/190", pass: "92%" },
                { name: "Perf", count: "203/231", pass: "87%" },
                { name: "Safety", count: "211/225", pass: "93%" }
              ].map((suite, idx) => (
                <div key={idx} className="p-2 bg-slate-900/30 rounded border border-slate-900 text-center flex flex-col justify-between">
                  <span className="text-slate-500 text-[8px] uppercase block">{suite.name}</span>
                  <span className="font-bold text-slate-300 block text-[10px] mt-1">{suite.count}</span>
                  <span className="text-[9px] text-green-400 block font-bold mt-0.5">{suite.pass}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Recent capability events */}
          <div className="rounded-lg border border-slate-800 bg-slate-950/40 p-4 font-mono text-[11px] space-y-3">
            <h3 className="text-xs font-bold tracking-wider text-slate-400 uppercase border-b border-slate-900 pb-2 flex items-center gap-1.5">
              <History className="h-4 w-4 text-cyan-400" />
              Recent Capability Events
            </h3>
            <div className="space-y-2 max-h-[160px] overflow-y-auto pr-1">
              {capabilityEvents.length === 0 ? (
                <div className="text-slate-600 italic">No lifecycle events logged.</div>
              ) : (
                capabilityEvents.map((evt, idx) => (
                  <div key={idx} className="p-2 bg-slate-900/20 border border-slate-900/40 rounded flex flex-col gap-1">
                    <div className="flex justify-between items-center text-[9px]">
                      <span className="text-cyan-400 font-bold uppercase">{evt.action.type.replace("CAPABILITY_", "")}</span>
                      <span className="text-slate-500">{new Date(evt.timestamp).toLocaleTimeString()}</span>
                    </div>
                    <span className="text-slate-300 text-[10px]">{evt.action.summary}</span>
                  </div>
                ))
              )}
            </div>
          </div>

          {/* Pending approvals */}
          <div className="rounded-lg border border-slate-800 bg-slate-950/40 p-4 font-mono text-[11px] space-y-3">
            <h3 className="text-xs font-bold tracking-wider text-slate-400 uppercase border-b border-slate-900 pb-2">
              Pending Approvals ({pendingApprovals.length})
            </h3>
            <div className="space-y-2">
              {pendingApprovals.length === 0 ? (
                <div className="text-slate-600 italic">No capabilities currently awaiting review.</div>
              ) : (
                pendingApprovals.map((cap) => (
                  <div
                    key={cap.capability_id}
                    onClick={() => setSelectedCap(cap)}
                    className="p-2 bg-slate-900/30 border border-slate-850 hover:bg-slate-900/60 cursor-pointer rounded flex items-center justify-between"
                  >
                    <div>
                      <span className="font-bold text-slate-300">{cap.name}</span>
                      <span className="text-slate-600 block text-[9px] uppercase mt-0.5">{cap.kind} • {cap.version}</span>
                    </div>
                    <span className="text-[9px] uppercase bg-orange-950/20 border border-orange-900/40 text-orange-400 px-1.5 py-0.5 rounded font-bold animate-pulse">
                      Under Review
                    </span>
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
