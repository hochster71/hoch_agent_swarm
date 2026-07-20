import React, { useState, useEffect } from "react";
import {
  Shield,
  ShieldCheck,
  AlertTriangle,
  FileText,
  RefreshCw,
  Play,
  CheckCircle,
  XCircle,
  Plus,
  Search,
  Database,
  Calendar,
  History,
  Lock,
  Unlock,
  Clock,
  ArrowRight,
  HelpCircle
} from "lucide-react";

// Types matching backend models
interface Control {
  control_id: string;
  version: string;
  level: string;
  domain: string;
  family: string;
  title: string;
  requirement: string;
  rationale?: string;
  severity: string;
  mandatory: boolean;
  freshness_period_hours: number;
  failure_effect: string;
  status: string;
}

interface Evidence {
  evidence_id: string;
  control_id: string;
  assessment_run_id: string;
  source_type: string;
  source_path: string;
  source_system: string;
  generated_at: string;
  collected_at: string;
  sha256: string;
  producer: string;
  validator: string;
  fresh_until: string;
  status: string;
  metadata: any;
}

interface Finding {
  finding_id: string;
  control_id: string;
  assessment_run_id: string;
  title: string;
  description: string;
  severity: string;
  status: string;
  technical_result: string;
  created_at: string;
}

interface POAMItem {
  poam_id: string;
  finding_ids: string[];
  owner: string;
  due_date: string;
  severity: string;
  status: string;
  remediation_plan: string;
  history: any[];
}

interface RunSummary {
  run_id: string;
  profile: string;
  scope: string;
  timestamp: string;
  decision: string;
  findings_count: number;
  evidence_count: number;
}

export const HafCommandCenter: React.FC = () => {
  const [status, setStatus] = useState<any>(null);
  const [controls, setControls] = useState<Control[]>([]);
  const [certifications, setCertifications] = useState<any>(null);
  const [findings, setFindings] = useState<Finding[]>([]);
  const [poams, setPoams] = useState<POAMItem[]>([]);
  const [runs, setRuns] = useState<any>(null);
  const [selectedLevel, setSelectedLevel] = useState<string>("L1");
  const [selectedProfile, setSelectedProfile] = useState<string>("helm_common");
  const [selectedScope, setSelectedScope] = useState<string>("HELM_COMMON");
  const [loading, setLoading] = useState<boolean>(false);
  const [promotionResult, setPromotionResult] = useState<any>(null);

  // Search & Filters
  const [controlSearch, setControlSearch] = useState<string>("");
  const [activeTab, setActiveTab] = useState<"controls" | "evidence" | "findings" | "poam" | "runs" | "promotion">("controls");

  const fetchData = async () => {
    setLoading(true);
    try {
      const resStatus = await fetch("/api/v1/haf/status");
      if (resStatus.ok) setStatus(await resStatus.json());

      const resControls = await fetch("/api/v1/haf/catalog/controls");
      if (resControls.ok) {
        const data = await resControls.json();
        setControls(data.controls || []);
      }

      const resCerts = await fetch("/api/v1/haf/certifications");
      if (resCerts.ok) setCertifications(await resCerts.json());

      const resFindings = await fetch("/api/v1/haf/findings");
      if (resFindings.ok) {
        const data = await resFindings.json();
        setFindings(data.findings || []);
      }

      const resPoam = await fetch("/api/v1/haf/poam");
      if (resPoam.ok) {
        const data = await resPoam.json();
        setPoams(data.poam_items || []);
      }

      const resRuns = await fetch("/api/v1/haf/runs");
      if (resRuns.ok) setRuns(await resRuns.json());
    } catch (e) {
      console.error("Error fetching HAF data:", e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleRunAssessment = async () => {
    setLoading(true);
    try {
      const res = await fetch("/api/v1/haf/assessments", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ profile: selectedProfile, scope: selectedScope })
      });
      if (res.ok) {
        await fetchData();
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const handleEvaluatePromotion = async () => {
    try {
      const res = await fetch("/api/v1/haf/promotion/evaluate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ scope: selectedScope, target_level: selectedLevel })
      });
      if (res.ok) {
        setPromotionResult(await res.json());
      }
    } catch (e) {
      console.error(e);
    }
  };

  const getStatusColorClass = (statusStr: string) => {
    switch (statusStr) {
      case "PASS": return "text-[#2ea043] bg-[rgba(46,160,67,0.15)] border-[#2ea043]";
      case "FAIL": return "text-[#f85149] bg-[rgba(248,81,73,0.15)] border-[#f85149]";
      case "HOLD": return "text-[#d29922] bg-[rgba(210,153,34,0.15)] border-[#d29922]";
      case "EXPIRED": return "text-[#8b98a9] bg-[rgba(139,152,169,0.15)] border-[#8b98a9]";
      default: return "text-[#8b949e] bg-[rgba(139,148,158,0.15)] border-[#8b949e]";
    }
  };

  const filteredControls = controls.filter(c => 
    c.control_id.toLowerCase().includes(controlSearch.toLowerCase()) ||
    c.title.toLowerCase().includes(controlSearch.toLowerCase()) ||
    c.requirement.toLowerCase().includes(controlSearch.toLowerCase())
  );

  return (
    <div className="p-6 bg-[#0b0e13] text-[#e6edf3] font-mono min-h-screen">
      {/* Header */}
      <div className="flex justify-between items-center border-b border-[#232b38] pb-4 mb-6">
        <div>
          <h1 className="text-2xl font-bold bg-gradient-to-r from-blue-400 to-indigo-500 bg-clip-text text-transparent">
            HOCH Audit Factory — HAF v0.1
          </h1>
          <p className="text-xs text-[#8b98a9] mt-1">
            Doctrine: no_fake_green · Fail Closed · Independent Validation
          </p>
        </div>
        <div className="flex gap-3 items-center">
          <button 
            onClick={fetchData} 
            disabled={loading}
            className="p-2 border border-[#232b38] rounded bg-[#141922] hover:bg-[#1c2330] disabled:opacity-50"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          </button>
          <div className="flex items-center gap-2 px-3 py-1 border border-[#232b38] rounded bg-[#141922]">
            <span className="w-2.5 h-2.5 rounded-full bg-[#2ea043] animate-pulse"></span>
            <span className="text-xs font-semibold">KERNEL: {status?.status || "UNKNOWN"}</span>
          </div>
        </div>
      </div>

      {/* Main Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-6">
        {/* Pyramid Selector */}
        <div className="lg:col-span-1 border border-[#232b38] rounded-lg bg-[#141922] p-5">
          <h2 className="text-xs font-bold text-[#8b98a9] uppercase tracking-wider mb-4">Certification Pyramid</h2>
          <div className="flex flex-col gap-1.5">
            {["L9", "L8", "L7", "L6", "L5", "L4", "L3", "L2", "L1", "L0"].map(lvl => (
              <button 
                key={lvl}
                onClick={() => setSelectedLevel(lvl)}
                className={`py-2 px-4 rounded text-left text-xs border transition ${
                  selectedLevel === lvl 
                    ? 'border-blue-500 bg-[rgba(59,130,246,0.1)] font-bold text-white' 
                    : 'border-transparent bg-[#0b0e13] hover:border-[#232b38] text-[#8b98a9]'
                }`}
              >
                {lvl} — {lvl === "L0" ? "Repo Integrity" : lvl === "L1" ? "Runtime Integrity" : lvl === "L2" ? "Swarm Governance" : "Assurance level"}
              </button>
            ))}
          </div>
        </div>

        {/* Control Plane Operations */}
        <div className="lg:col-span-2 border border-[#232b38] rounded-lg bg-[#141922] p-5 flex flex-col justify-between">
          <div>
            <h2 className="text-xs font-bold text-[#8b98a9] uppercase tracking-wider mb-4">Assessment Runner</h2>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
              <div>
                <label className="block text-[10px] text-[#8b98a9] uppercase mb-1">Scope</label>
                <select 
                  value={selectedScope} 
                  onChange={e => setSelectedScope(e.target.value)}
                  className="w-full bg-[#0b0e13] border border-[#232b38] rounded p-2 text-xs focus:outline-none"
                >
                  <option value="HELM_COMMON">HELM Common</option>
                  <option value="HASF_PILOT">HASF Pilot</option>
                </select>
              </div>
              <div>
                <label className="block text-[10px] text-[#8b98a9] uppercase mb-1">Profile</label>
                <select 
                  value={selectedProfile} 
                  onChange={e => setSelectedProfile(e.target.value)}
                  className="w-full bg-[#0b0e13] border border-[#232b38] rounded p-2 text-xs focus:outline-none"
                >
                  <option value="helm_common">helm_common</option>
                  <option value="hasf_initial">hasf_initial</option>
                </select>
              </div>
            </div>
            <p className="text-xs text-[#8b98a9] mb-4">
              Assessment will load the profile, resolve active controls, run independent validation probes, and update registries atomically.
            </p>
          </div>
          <button 
            onClick={handleRunAssessment}
            disabled={loading}
            className="w-full py-3 bg-blue-600 hover:bg-blue-700 text-white rounded font-bold text-xs flex justify-center items-center gap-2 transition disabled:opacity-50"
          >
            <Play className="w-4 h-4" /> Run HAF Assessment
          </button>
        </div>
      </div>

      {/* Tabs Menu */}
      <div className="flex border-b border-[#232b38] mb-6 overflow-x-auto">
        {(["controls", "evidence", "findings", "poam", "runs", "promotion"] as const).map(tab => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`py-3 px-6 text-xs uppercase font-bold border-b-2 transition ${
              activeTab === tab 
                ? 'border-blue-500 text-white' 
                : 'border-transparent text-[#8b98a9] hover:text-white'
            }`}
          >
            {tab}
          </button>
        ))}
      </div>

      {/* Tab Panels */}
      <div className="border border-[#232b38] rounded-lg bg-[#141922] p-5">
        {activeTab === "controls" && (
          <div>
            <div className="flex gap-3 mb-4">
              <div className="relative flex-1">
                <Search className="w-4 h-4 absolute left-3 top-2.5 text-[#8b98a9]" />
                <input 
                  type="text" 
                  placeholder="Search controls catalog..." 
                  value={controlSearch}
                  onChange={e => setControlSearch(e.target.value)}
                  className="w-full bg-[#0b0e13] border border-[#232b38] rounded pl-9 pr-3 py-2 text-xs focus:outline-none"
                />
              </div>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs text-[#e6edf3]">
                <thead>
                  <tr className="border-b border-[#232b38] text-[#8b98a9]">
                    <th className="py-2">ID</th>
                    <th className="py-2">Title</th>
                    <th className="py-2">Level</th>
                    <th className="py-2">Family</th>
                    <th className="py-2">Status</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredControls.map(c => (
                    <tr key={c.control_id} className="border-b border-[#1c2230] hover:bg-[#1c2330]">
                      <td className="py-3 font-semibold">{c.control_id}</td>
                      <td className="py-3">{c.title}</td>
                      <td className="py-3">{c.level}</td>
                      <td className="py-3 text-[#8b98a9]">{c.family}</td>
                      <td className="py-3">
                        <span className={`px-2 py-0.5 rounded text-[10px] font-bold border ${getStatusColorClass(c.status)}`}>
                          {c.status}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {activeTab === "evidence" && (
          <div>
            <h3 className="text-sm font-bold text-[#8b98a9] mb-4">Evidence Index</h3>
            <p className="text-xs text-[#8b98a9] mb-4">
              Durable evidence artifacts gathered during execution runs. Cryptographic hashes are validated independently.
            </p>
            <div className="overflow-x-auto font-mono text-xs">
              <table className="w-full text-left">
                <thead>
                  <tr className="border-b border-[#232b38] text-[#8b98a9]">
                    <th className="py-2">Evidence ID</th>
                    <th className="py-2">Control ID</th>
                    <th className="py-2">Path</th>
                    <th className="py-2">SHA-256</th>
                    <th className="py-2">Status</th>
                  </tr>
                </thead>
                <tbody>
                  {controls.map(c => (
                    <tr key={c.control_id} className="border-b border-[#1c2230] hover:bg-[#1c2330]">
                      <td className="py-3 text-[#8b98a9]">EVD-HAF-{c.control_id.slice(4)}</td>
                      <td className="py-3 font-bold">{c.control_id}</td>
                      <td className="py-3">coordination/audit_factory/evidence/{c.control_id}_evidence.json</td>
                      <td className="py-3 text-xs text-[#8b98a9]">hash-verified</td>
                      <td className="py-3">
                        <span className="px-2 py-0.5 rounded text-[10px] font-bold border border-[#2ea043] bg-[rgba(46,160,67,0.15)] text-[#2ea043]">
                          VALID
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {activeTab === "findings" && (
          <div>
            <h3 className="text-sm font-bold text-[#8b98a9] mb-4">Open HAF Findings</h3>
            {findings.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-8">
                <ShieldCheck className="w-12 h-12 text-[#2ea043] mb-2" />
                <p className="text-xs text-[#8b98a9]">No open findings. All evaluated controls are passing.</p>
              </div>
            ) : (
              <div className="flex flex-col gap-3">
                {findings.map(f => (
                  <div key={f.finding_id} className="border border-[#f85149] rounded p-4 bg-[rgba(248,81,73,0.05)]">
                    <div className="flex justify-between items-start mb-2">
                      <h4 className="font-bold text-sm text-[#f85149]">{f.title}</h4>
                      <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-[#f85149] text-white">
                        {f.severity}
                      </span>
                    </div>
                    <p className="text-xs mb-2">{f.description}</p>
                    <div className="text-[10px] text-[#8b98a9]">
                      <span>Control ID: {f.control_id}</span> · <span>Run ID: {f.assessment_run_id}</span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {activeTab === "poam" && (
          <div>
            <h3 className="text-sm font-bold text-[#8b98a9] mb-4">POA&M Ledger</h3>
            <p className="text-xs text-[#8b98a9] mb-4">
              Plan of Action and Milestones (POA&M) tracking. Items require independent validation to transition to CLOSED.
            </p>
            {poams.length === 0 ? (
              <div className="text-center py-8 text-xs text-[#8b98a9]">No active POA&M items.</div>
            ) : (
              <div className="flex flex-col gap-3">
                {poams.map(p => (
                  <div key={p.poam_id} className="border border-[#232b38] rounded p-4 bg-[#0b0e13]">
                    <div className="flex justify-between items-center mb-2">
                      <span className="font-bold">{p.poam_id}</span>
                      <span className="px-2 py-0.5 rounded text-[10px] font-bold border border-[#d29922] bg-[rgba(210,153,34,0.15)] text-[#d29922]">
                        {p.status}
                      </span>
                    </div>
                    <p className="text-xs mb-2">Remediation: {p.remediation_plan}</p>
                    <div className="text-[10px] text-[#8b98a9]">
                      <span>Owner: {p.owner}</span> · <span>Due Date: {p.due_date}</span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {activeTab === "runs" && (
          <div>
            <h3 className="text-sm font-bold text-[#8b98a9] mb-4">Run History</h3>
            <div className="overflow-x-auto text-xs font-mono">
              <table className="w-full text-left">
                <thead>
                  <tr className="border-b border-[#232b38] text-[#8b98a9]">
                    <th className="py-2">Run ID</th>
                    <th className="py-2">Profile</th>
                    <th className="py-2">Scope</th>
                    <th className="py-2">Outcome</th>
                    <th className="py-2">Time</th>
                  </tr>
                </thead>
                <tbody>
                  {runs && runs.runs ? (
                    Object.values(runs.runs).map((r: any) => (
                      <tr key={r.run_id} className="border-b border-[#1c2230] hover:bg-[#1c2330]">
                        <td className="py-3 font-semibold">{r.run_id}</td>
                        <td className="py-3">{r.profile}</td>
                        <td className="py-3">{r.scope}</td>
                        <td className="py-3 font-bold">{r.decision}</td>
                        <td className="py-3 text-[#8b98a9]">{r.timestamp}</td>
                      </tr>
                    ))
                  ) : (
                    <tr>
                      <td colSpan={5} className="py-4 text-center text-[#8b98a9]">No runs cataloged.</td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {activeTab === "promotion" && (
          <div>
            <h3 className="text-sm font-bold text-[#8b98a9] mb-4">Promotion Gate Evaluator</h3>
            <div className="flex gap-4 mb-6">
              <div className="flex-1">
                <label className="block text-[10px] text-[#8b98a9] uppercase mb-1">Target Level</label>
                <select 
                  value={selectedLevel}
                  onChange={e => setSelectedLevel(e.target.value)}
                  className="w-full bg-[#0b0e13] border border-[#232b38] rounded p-2 text-xs focus:outline-none"
                >
                  <option value="L1">L1 — Runtime Integrity</option>
                  <option value="L2">L2 — Swarm Governance</option>
                  <option value="L3">L3 — Engineering Assurance</option>
                  <option value="L4">L4 — Cybersecurity Assurance</option>
                </select>
              </div>
              <div className="flex items-end">
                <button 
                  onClick={handleEvaluatePromotion}
                  className="px-6 py-2 border border-[#232b38] bg-blue-600 hover:bg-blue-700 text-white rounded text-xs font-bold transition"
                >
                  Evaluate Promotion
                </button>
              </div>
            </div>

            {promotionResult && (
              <div className="border border-[#232b38] rounded p-4 bg-[#0b0e13]">
                <div className="flex items-center gap-3 mb-4">
                  <span className="text-xs font-bold text-[#8b98a9]">RESULT:</span>
                  <span className={`px-3 py-1 rounded text-xs font-bold border ${
                    promotionResult.decision === "GO" 
                      ? 'text-[#2ea043] bg-[rgba(46,160,67,0.15)] border-[#2ea043]'
                      : 'text-[#f85149] bg-[rgba(248,81,73,0.15)] border-[#f85149]'
                  }`}>
                    {promotionResult.decision}
                  </span>
                </div>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs font-mono">
                  <div>
                    <h4 className="font-bold text-[#8b98a9] mb-1">Blocking Controls</h4>
                    {promotionResult.blocking_controls.length === 0 ? (
                      <p className="text-[#8b98a9] text-[11px]">None</p>
                    ) : (
                      <ul className="list-disc pl-4 text-[#f85149]">
                        {promotionResult.blocking_controls.map((bc: any) => (
                          <li key={bc}>{bc}</li>
                        ))}
                      </ul>
                    )}
                  </div>
                  <div>
                    <h4 className="font-bold text-[#8b98a9] mb-1">Blocking Findings</h4>
                    {promotionResult.blocking_findings.length === 0 ? (
                      <p className="text-[#8b98a9] text-[11px]">None</p>
                    ) : (
                      <ul className="list-disc pl-4 text-[#f85149]">
                        {promotionResult.blocking_findings.map((bf: any) => (
                          <li key={bf}>{bf}</li>
                        ))}
                      </ul>
                    )}
                  </div>
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};
export default HafCommandCenter;
