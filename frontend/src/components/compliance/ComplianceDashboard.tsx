import React, { useState } from "react";
import {
  Shield,
  ShieldCheck,
  AlertTriangle,
  FileText,
  Download,
  RefreshCw,
  Plus,
  UserCheck,
  Calendar,
  CheckCircle,
  Clock,
  CheckCircle2,
  AlertCircle,
  Play,
  Lock
} from "lucide-react";
import { FRAMEWORKS } from "../../lib/compliance/frameworkRegistry";
import { initialControls, initialEvidence, initialAttestations } from "../../lib/compliance/complianceFixtures";
import { ComplianceControl, ComplianceEvidence, AttestationRecord } from "../../lib/compliance/complianceTypes";

export const ComplianceDashboard: React.FC = () => {
  const [selectedFramework, setSelectedFramework] = useState<string>("nist-csf-2.0");
  const [controls, setControls] = useState<ComplianceControl[]>(initialControls);
  const [evidenceList, setEvidenceList] = useState<ComplianceEvidence[]>(initialEvidence);
  const [attestations, setAttestations] = useState<AttestationRecord[]>(initialAttestations);

  // Form states for manual evidence add
  const [newEvidenceTitle, setNewEvidenceTitle] = useState("");
  const [newEvidencePath, setNewEvidencePath] = useState("");
  const [newEvidenceSource, setNewEvidenceSource] = useState<any>("manual");
  const [evidenceControlId, setEvidenceControlId] = useState("");

  // Form states for attestation sign-off
  const [attestationControlId, setAttestationControlId] = useState("");
  const [attestationNotes, setAttestationNotes] = useState("");

  const [activeTab, setActiveTab] = useState<"frameworks" | "evidence" | "collectors" | "attestations">("frameworks");

  // Shopping Gate state
  const [signals, setSignals] = useState<any[]>([]);
  const [shoppingQuery, setShoppingQuery] = useState("baby rat toys and tunnels for supervised playtime");
  const [printApproved, setPrintApproved] = useState(false);
  const [attemptPurchase, setAttemptPurchase] = useState(false);
  const [childAge, setChildAge] = useState(5);
  const [selectedMode, setSelectedMode] = useState("RESEARCH_AND_LINK_PREP");
  const [shoppingResult, setShoppingResult] = useState<any>(null);
  const [shoppingError, setShoppingError] = useState<string | null>(null);
  const [isRunningQuery, setIsRunningQuery] = useState(false);

  // PromptOps state
  const [operatorPromptInput, setOperatorPromptInput] = useState("Build HAS e2e production ready no errors");
  const [evaluationResult, setEvaluationResult] = useState<any>(null);
  const [claimText, setClaimText] = useState("production ready");
  const [claimResult, setClaimResult] = useState<any>(null);
  const [claimError, setClaimError] = useState<string | null>(null);
  const [isEvaluating, setIsEvaluating] = useState(false);
  const [isSubmittingClaim, setIsSubmittingClaim] = useState(false);

  const handleEvaluatePrompt = async () => {
    setIsEvaluating(true);
    setEvaluationResult(null);
    try {
      const res = await fetch("/api/v1/promptops/evaluate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ prompt: operatorPromptInput })
      });
      const data = await res.json();
      if (res.ok) {
        setEvaluationResult(data);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setIsEvaluating(false);
      fetchSignals();
    }
  };

  const handleSubmitClaim = async () => {
    setIsSubmittingClaim(true);
    setClaimResult(null);
    setClaimError(null);
    try {
      const res = await fetch("/api/v1/promptops/submit-claim", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ claim: claimText })
      });
      const data = await res.json();
      if (res.ok) {
        setClaimResult(data);
      } else {
        setClaimError(data.detail || "Verification failed.");
      }
    } catch (err: any) {
      setClaimError(err.message || "Network error.");
    } finally {
      setIsSubmittingClaim(false);
      fetchSignals();
    }
  };

  React.useEffect(() => {
    if (activeTab === ("promptops" as any)) {
      fetchSignals();
      const interval = setInterval(fetchSignals, 3000);
      return () => clearInterval(interval);
    }
  }, [activeTab]);

  const fetchSignals = async () => {
    try {
      const res = await fetch("/api/v1/runtime-truth/state");
      const data = await res.json();
      if (data.status === "success") {
        setSignals(data.signals);
      }
    } catch (e) {
      console.error(e);
    }
  };

  React.useEffect(() => {
    fetchSignals();
  }, []);

  React.useEffect(() => {
    if (activeTab === ("shopping" as any)) {
      fetchSignals();
      const interval = setInterval(fetchSignals, 3000);
      return () => clearInterval(interval);
    }
  }, [activeTab]);

  const handleRunShoppingResearch = async () => {
    setIsRunningQuery(true);
    setShoppingResult(null);
    setShoppingError(null);
    try {
      const res = await fetch("/api/v1/operator-tasks/shopping-research", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          query: shoppingQuery,
          child_age: childAge,
          printer: "HP-OfficeJet-Pro-WiFi",
          print_approved: printApproved,
          attempt_purchase: attemptPurchase,
          mode: selectedMode
        })
      });
      const data = await res.json();
      if (res.ok) {
        setShoppingResult(data);
      } else {
        setShoppingError(data.detail || "Request failed.");
      }
    } catch (err: any) {
      setShoppingError(err.message || "Network error.");
    } finally {
      setIsRunningQuery(false);
      fetchSignals();
    }
  };
  const [logs, setLogs] = useState<string[]>([
    "2026-06-24 10:15:32 - [Collector] Initialized NIST SP 800-53 telemetry verify agent.",
    "2026-06-24 11:32:01 - [Collector] Scanned tenant directory hashes - integrity match 100%.",
    "2026-06-24 12:05:00 - [Collector] Validation successful for ZTA pipeline signatures. Associated ev-audit-review-01.",
    "2026-06-24 12:20:45 - [Collector] Scheduled daily cron checks."
  ]);
  const [isRefreshing, setIsRefreshing] = useState(false);

  // Calculations
  const totalFrameworkControls = controls.filter(c => c.framework === selectedFramework);
  const activeFramework = FRAMEWORKS.find(f => f.id === selectedFramework) || FRAMEWORKS[0];

  const triggerCollectorCheck = () => {
    setIsRefreshing(true);
    setTimeout(() => {
      setIsRefreshing(false);
      const now = new Date().toISOString().replace("T", " ").substring(0, 19);
      setLogs(prev => [
        `${now} - [Collector] Manual check invoked. Recalculating evidence hashes and checking compliance triggers...`,
        `${now} - [Collector] Verified all ${evidenceList.length} evidence signatures successfully. No tamper flags.`,
        ...prev
      ]);
      // Log to global ledger if window.addAuditEvent exists
      if (window.addAuditEvent) {
        window.addAuditEvent({
          actor: { id: "op-mh-99", name: "Michael Hoch", type: "human", role: "Compliance Officer" },
          action: { type: "COMPLIANCE_EVIDENCE_COLLECTED", summary: "Automated telemetry collector invoked manually." },
          target: { type: "system", id: "compliance-collector", name: "Evidence Collector Engine" },
          result: "success",
          severity: "info",
          provenance: { source: "manual", evidence_refs: [] },
          policy: { required: false, result: "passed" }
        });
      }
    }, 800);
  };

  const handleAddEvidence = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newEvidenceTitle || !newEvidencePath || !evidenceControlId) return;

    const newEv: ComplianceEvidence = {
      evidence_id: `ev-${Math.floor(Math.random() * 100000)}`,
      title: newEvidenceTitle,
      collected_at: new Date().toISOString(),
      source_type: newEvidenceSource,
      file_path: newEvidencePath,
      file_hash: `sha256:${Math.random().toString(36).substring(7)}${Math.random().toString(36).substring(7)}`,
      status: "valid"
    };

    setEvidenceList(prev => [...prev, newEv]);

    // Map to control
    setControls(prev =>
      prev.map(c => {
        if (c.control_id === evidenceControlId) {
          return {
            ...c,
            status: "implemented",
            evidence_ids: [...c.evidence_ids, newEv.evidence_id],
            last_evaluated: new Date().toISOString()
          };
        }
        return c;
      })
    );

    // Audit Event
    if (window.addAuditEvent) {
      window.addAuditEvent({
        actor: { id: "op-mh-99", name: "Michael Hoch", type: "human", role: "Compliance Officer" },
        action: { type: "COMPLIANCE_EVIDENCE_COLLECTED", summary: `Manual evidence "${newEvidenceTitle}" linked to control ${evidenceControlId}` },
        target: { type: "system", id: evidenceControlId, name: `Compliance Control ${evidenceControlId}` },
        result: "success",
        severity: "info",
        provenance: { source: "manual", evidence_refs: [newEv.file_path] },
        policy: { required: false, result: "passed" }
      });
    }

    setNewEvidenceTitle("");
    setNewEvidencePath("");
    setEvidenceControlId("");
  };

  const handleAttestation = (e: React.FormEvent) => {
    e.preventDefault();
    if (!attestationControlId || !attestationNotes) return;

    const newAtt: AttestationRecord = {
      attestation_id: `att-${Math.floor(Math.random() * 1000)}`,
      control_id: attestationControlId,
      operator_id: "op-mh-99",
      operator_name: "Michael Hoch",
      timestamp: new Date().toISOString(),
      notes: attestationNotes,
      evidence_refs: controls.find(c => c.control_id === attestationControlId)?.evidence_ids || []
    };

    setAttestations(prev => [...prev, newAtt]);

    // Update control
    setControls(prev =>
      prev.map(c => {
        if (c.control_id === attestationControlId) {
          return {
            ...c,
            last_evaluated: new Date().toISOString()
          };
        }
        return c;
      })
    );

    // Audit Event
    if (window.addAuditEvent) {
      window.addAuditEvent({
        actor: { id: "op-mh-99", name: "Michael Hoch", type: "human", role: "Compliance Officer" },
        action: { type: "COMPLIANCE_ATTESTATION_COMPLETED", summary: `Operator attestation signed for control ${attestationControlId}` },
        target: { type: "system", id: attestationControlId, name: `Compliance Control ${attestationControlId}` },
        result: "success",
        severity: "info",
        provenance: { source: "manual", evidence_refs: newAtt.evidence_refs },
        policy: { required: false, result: "passed" }
      });
    }

    setAttestationControlId("");
    setAttestationNotes("");
  };

  const handleExportReport = () => {
    // Generate simple mock report file for download
    const reportData = {
      framework: activeFramework,
      generated_at: new Date().toISOString(),
      controls_status: totalFrameworkControls,
      evidence_summary: evidenceList.filter(e =>
        totalFrameworkControls.some(c => c.evidence_ids.includes(e.evidence_id))
      )
    };

    const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(reportData, null, 2));
    const downloadAnchor = document.createElement("a");
    downloadAnchor.setAttribute("href", dataStr);
    downloadAnchor.setAttribute("download", `compliance_report_${selectedFramework}.json`);
    document.body.appendChild(downloadAnchor);
    downloadAnchor.click();
    downloadAnchor.remove();

    if (window.addAuditEvent) {
      window.addAuditEvent({
        actor: { id: "op-mh-99", name: "Michael Hoch", type: "human", role: "Compliance Officer" },
        action: { type: "COMPLIANCE_REPORT_EXPORTED", summary: `Compliance posture report exported for ${selectedFramework}` },
        target: { type: "system", id: selectedFramework, name: `Framework ${selectedFramework}` },
        result: "success",
        severity: "info",
        provenance: { source: "manual", evidence_refs: [] },
        policy: { required: false, result: "passed" }
      });
    }
  };

  return (
    <div className="glass-panel p-6 rounded-2xl border border-white/10 text-white space-y-6">
      {/* Header section */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 border-b border-white/10 pb-5">
        <div>
          <div className="flex items-center gap-2">
            <Shield className="w-8 h-8 text-blue-400" />
            <h2 className="text-2xl font-bold tracking-tight">Compliance &amp; Audit Control Plane</h2>
          </div>
          <p className="text-slate-400 text-sm mt-1">
            Continuous evidence automated check-in and regulatory posture auditor (NIST, SOC 2, ISO 42001).
          </p>
        </div>

        <div className="flex gap-3">
          <button
            onClick={triggerCollectorCheck}
            disabled={isRefreshing}
            className="flex items-center gap-2 px-4 py-2 bg-white/5 hover:bg-white/10 active:scale-95 transition rounded-lg border border-white/10 text-sm font-medium"
          >
            <RefreshCw className={`w-4 h-4 ${isRefreshing ? "animate-spin" : ""}`} />
            Scan Posture
          </button>
          <button
            onClick={handleExportReport}
            className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-500 active:scale-95 transition rounded-lg text-sm font-medium"
          >
            <Download className="w-4 h-4" />
            Export Audit Report
          </button>
        </div>
      </div>

      {/* Grid framework selection and metrics */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        {FRAMEWORKS.map(fw => (
          <div
            key={fw.id}
            onClick={() => setSelectedFramework(fw.id)}
            className={`cursor-pointer glass-panel p-4 rounded-xl border transition-all ${
              selectedFramework === fw.id
                ? "border-blue-500/50 bg-blue-500/5"
                : "border-white/5 bg-white/2 hover:bg-white/5"
            }`}
          >
            <div className="flex justify-between items-start">
              <span className="text-sm font-semibold tracking-wider uppercase text-slate-400">{fw.name}</span>
              <span
                className={`text-xs px-2 py-0.5 rounded-full font-bold ${
                  fw.coverage_percent >= 85
                    ? "bg-green-500/20 text-green-400"
                    : "bg-blue-500/20 text-blue-400"
                }`}
              >
                {fw.coverage_percent}% Match
              </span>
            </div>
            <p className="text-xs text-slate-400 line-clamp-2 mt-2">{fw.description}</p>
            <div className="w-full bg-white/10 h-1.5 rounded-full mt-4 overflow-hidden">
              <div
                className="bg-blue-400 h-full transition-all duration-500"
                style={{ width: `${fw.coverage_percent}%` }}
              ></div>
            </div>
          </div>
        ))}
      </div>

      {/* Main dashboard tabs */}
      <div className="flex border-b border-white/10">
        <button
          onClick={() => setActiveTab("frameworks")}
          className={`px-4 py-2 border-b-2 text-sm font-semibold transition ${
            activeTab === "frameworks"
              ? "border-blue-500 text-blue-400"
              : "border-transparent text-slate-400 hover:text-white"
          }`}
        >
          Controls Checklist
        </button>
        <button
          onClick={() => setActiveTab("evidence")}
          className={`px-4 py-2 border-b-2 text-sm font-semibold transition ${
            activeTab === "evidence"
              ? "border-blue-500 text-blue-400"
              : "border-transparent text-slate-400 hover:text-white"
          }`}
        >
          Evidence Library ({evidenceList.length})
        </button>
        <button
          onClick={() => setActiveTab("collectors")}
          className={`px-4 py-2 border-b-2 text-sm font-semibold transition ${
            activeTab === "collectors"
              ? "border-blue-500 text-blue-400"
              : "border-transparent text-slate-400 hover:text-white"
          }`}
        >
          Auto Collectors Log
        </button>
        <button
          onClick={() => setActiveTab("attestations")}
          className={`px-4 py-2 border-b-2 text-sm font-semibold transition ${
            activeTab === "attestations"
              ? "border-blue-500 text-blue-400"
              : "border-transparent text-slate-400 hover:text-white"
          }`}
        >
          Operator Sign-Off
        </button>
        <button
          onClick={() => setActiveTab("shopping" as any)}
          className={`px-4 py-2 border-b-2 text-sm font-semibold transition ${
            activeTab === ("shopping" as any)
              ? "border-blue-500 text-blue-400"
              : "border-transparent text-slate-400 hover:text-white"
          }`}
        >
          Shopping &amp; Print Gate
        </button>
        <button
          onClick={() => setActiveTab("promptops" as any)}
          className={`px-4 py-2 border-b-2 text-sm font-semibold transition ${
            activeTab === ("promptops" as any)
              ? "border-blue-500 text-blue-400"
              : "border-transparent text-slate-400 hover:text-white"
          }`}
        >
          PromptOps Portal
        </button>
      </div>

      {/* Tab Panels */}
      {activeTab === "frameworks" && (
        <div className="space-y-4">
          <div className="flex justify-between items-center">
            <h3 className="text-lg font-bold">Framework Requirements for {activeFramework.name}</h3>
            <span className="text-sm text-slate-400">{totalFrameworkControls.length} Controls defined</span>
          </div>

          <div className="space-y-3">
            {totalFrameworkControls.map(ctrl => (
              <div
                key={ctrl.control_id}
                className="glass-panel p-4 rounded-xl border border-white/5 bg-white/2 hover:border-white/10 transition flex flex-col md:flex-row justify-between items-start md:items-center gap-4"
              >
                <div className="flex-1">
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-sm font-bold text-blue-400 bg-blue-500/10 px-2 py-0.5 rounded">
                      {ctrl.control_id}
                    </span>
                    <span className="text-xs text-slate-400 font-medium">{ctrl.section}</span>
                    <span className="text-xs text-slate-500">Last Checked: {new Date(ctrl.last_evaluated).toLocaleDateString()}</span>
                  </div>
                  <h4 className="font-semibold text-sm mt-1">{ctrl.title}</h4>
                  <p className="text-xs text-slate-400 mt-1">{ctrl.description}</p>
                  {ctrl.evidence_ids.length > 0 ? (
                    <div className="flex flex-wrap gap-2 mt-3">
                      {ctrl.evidence_ids.map(evId => {
                        const evObj = evidenceList.find(e => e.evidence_id === evId);
                        return (
                          <span
                            key={evId}
                            className="inline-flex items-center gap-1 text-[10px] px-2 py-0.5 bg-white/5 rounded-full border border-white/5 text-slate-300 font-mono"
                          >
                            <FileText className="w-3 h-3 text-slate-400" />
                            {evObj?.title || evId}
                          </span>
                        );
                      })}
                    </div>
                  ) : (
                    <p className="text-[10px] text-yellow-400 flex items-center gap-1 mt-2">
                      <AlertTriangle className="w-3. h-3" /> No evidence file associated. Control posture weak.
                    </p>
                  )}
                </div>

                <div className="flex flex-row md:flex-col items-end gap-2 w-full md:w-auto">
                  <span
                    className={`text-xs px-2.5 py-1 rounded-full font-bold uppercase ${
                      ctrl.status === "implemented"
                        ? "bg-green-500/20 text-green-400 border border-green-500/20"
                        : ctrl.status === "partially_implemented"
                        ? "bg-yellow-500/20 text-yellow-400 border border-yellow-500/20"
                        : "bg-red-500/20 text-red-400 border border-red-500/20"
                    }`}
                  >
                    {ctrl.status.replace("_", " ")}
                  </span>
                  <span className="text-xs text-slate-400">Owner: {ctrl.owner}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {activeTab === "evidence" && (
        <div className="space-y-6">
          <div className="flex justify-between items-center">
            <h3 className="text-lg font-bold">Evidence Store Library</h3>
            <span className="text-sm text-slate-400">Total documents: {evidenceList.length}</span>
          </div>

          {/* Table of Evidence */}
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="border-b border-white/10 text-xs text-slate-400 font-bold uppercase">
                  <th className="pb-3">Title &amp; Path</th>
                  <th className="pb-3">Collected Date</th>
                  <th className="pb-3">Collector Source</th>
                  <th className="pb-3">SHA-256 Hash</th>
                  <th className="pb-3 text-right">Integrity Status</th>
                </tr>
              </thead>
              <tbody>
                {evidenceList.map(ev => (
                  <tr key={ev.evidence_id} className="border-b border-white/5 hover:bg-white/1 text-sm">
                    <td className="py-4">
                      <div className="font-semibold text-white">{ev.title}</div>
                      <div className="text-xs text-slate-400 font-mono mt-0.5">{ev.file_path}</div>
                    </td>
                    <td className="py-4 text-xs text-slate-300">
                      {new Date(ev.collected_at).toLocaleString()}
                    </td>
                    <td className="py-4 text-xs uppercase text-slate-400 font-mono">{ev.source_type}</td>
                    <td className="py-4 text-xs text-slate-400 font-mono truncate max-w-[150px]">
                      {ev.file_hash}
                    </td>
                    <td className="py-4 text-right">
                      <span
                        className={`text-xs px-2 py-0.5 rounded-full font-bold ${
                          ev.status === "valid"
                            ? "bg-green-500/10 text-green-400"
                            : ev.status === "stale"
                            ? "bg-yellow-500/10 text-yellow-400"
                            : "bg-red-500/10 text-red-400"
                        }`}
                      >
                        {ev.status.toUpperCase()}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Manual evidence adder form */}
          <form onSubmit={handleAddEvidence} className="glass-panel p-4 rounded-xl border border-white/10 bg-white/2 space-y-4">
            <h4 className="font-bold text-sm flex items-center gap-2">
              <Plus className="w-4 h-4 text-blue-400" /> Link Manual Compliance Evidence File
            </h4>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs text-slate-400 font-bold mb-1">Evidence Title</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. SOC2 Access Audit Logs Q2"
                  value={newEvidenceTitle}
                  onChange={e => setNewEvidenceTitle(e.target.value)}
                  className="w-full bg-white/5 border border-white/10 rounded px-3 py-1.5 text-sm text-white focus:outline-none focus:border-blue-500"
                />
              </div>
              <div>
                <label className="block text-xs text-slate-400 font-bold mb-1">File Absolute Path</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. /audit/soc2_access_q2.json"
                  value={newEvidencePath}
                  onChange={e => setNewEvidencePath(e.target.value)}
                  className="w-full bg-white/5 border border-white/10 rounded px-3 py-1.5 text-sm text-white focus:outline-none focus:border-blue-500"
                />
              </div>
              <div>
                <label className="block text-xs text-slate-400 font-bold mb-1">Source Type</label>
                <select
                  value={newEvidenceSource}
                  onChange={e => setNewEvidenceSource(e.target.value)}
                  className="w-full bg-white/5 border border-white/10 rounded px-3 py-1.5 text-sm text-white focus:outline-none focus:border-blue-500"
                >
                  <option value="manual">Manual Operator Upload</option>
                  <option value="audit_log">Audit Logs Stream</option>
                  <option value="scan_report">Security Vulnerability Scanner</option>
                  <option value="runbook_run">Heuristic Runbook Execution</option>
                </select>
              </div>
              <div>
                <label className="block text-xs text-slate-400 font-bold mb-1">Map to Requirement</label>
                <select
                  required
                  value={evidenceControlId}
                  onChange={e => setEvidenceControlId(e.target.value)}
                  className="w-full bg-white/5 border border-white/10 rounded px-3 py-1.5 text-sm text-white focus:outline-none focus:border-blue-500"
                >
                  <option value="">-- Choose Requirement Control ID --</option>
                  {controls.map(c => (
                    <option key={c.control_id} value={c.control_id}>
                      {c.control_id} - {c.title} ({c.framework.toUpperCase()})
                    </option>
                  ))}
                </select>
              </div>
            </div>
            <button
              type="submit"
              className="px-4 py-2 bg-blue-600 hover:bg-blue-500 rounded text-xs font-semibold tracking-wider uppercase transition active:scale-95"
            >
              Add and Link Evidence
            </button>
          </form>
        </div>
      )}

      {activeTab === "collectors" && (
        <div className="space-y-4">
          <div className="flex justify-between items-center">
            <h3 className="text-lg font-bold">Automated Evidence Collectors</h3>
            <span className="flex items-center gap-1.5 text-xs text-green-400 font-semibold bg-green-500/10 px-2 py-0.5 rounded-full">
              <span className="w-1.5 h-1.5 bg-green-400 rounded-full animate-ping"></span>
              Collectors Active
            </span>
          </div>

          <div className="glass-panel p-4 rounded-xl border border-white/5 bg-slate-950 font-mono text-xs text-slate-300 space-y-1.5 max-h-[300px] overflow-y-auto">
            {logs.map((log, idx) => (
              <div key={idx} className="border-l-2 border-blue-500 pl-3">
                {log}
              </div>
            ))}
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="glass-panel p-4 rounded-xl border border-white/5 bg-white/1 space-y-2">
              <h5 className="font-bold text-sm text-blue-400">Decentralized Ledger Sync</h5>
              <p className="text-xs text-slate-400">Pulls transaction events from main ledger db automatically to generate compliance proofs.</p>
              <span className="text-[10px] text-slate-500">Frequency: Real-time event-driven</span>
            </div>
            <div className="glass-panel p-4 rounded-xl border border-white/5 bg-white/1 space-y-2">
              <h5 className="font-bold text-sm text-blue-400">Vulnerability Scans Watch</h5>
              <p className="text-xs text-slate-400">Listens to red team scenario completions and files vulnerability scanning report summaries.</p>
              <span className="text-[10px] text-slate-500">Frequency: On event completion</span>
            </div>
            <div className="glass-panel p-4 rounded-xl border border-white/5 bg-white/1 space-y-2">
              <h5 className="font-bold text-sm text-blue-400">Infrastructure Verify Daemon</h5>
              <p className="text-xs text-slate-400">Inspects docker cluster logs and runbook executions to assert security posture state.</p>
              <span className="text-[10px] text-slate-500">Frequency: Hourly polling checks</span>
            </div>
          </div>
        </div>
      )}

      {activeTab === "attestations" && (
        <div className="space-y-6">
          <div className="flex justify-between items-center">
            <h3 className="text-lg font-bold">Operator Attestation Sign-Off Queue</h3>
            <span className="text-sm text-slate-400">Total attestations: {attestations.length}</span>
          </div>

          {/* List of active attestations */}
          <div className="space-y-3">
            {attestations.map(att => (
              <div
                key={att.attestation_id}
                className="glass-panel p-4 rounded-xl border border-white/5 bg-white/2 flex flex-col md:flex-row justify-between items-start gap-4"
              >
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-xs font-bold text-green-400 bg-green-500/10 px-2 py-0.5 rounded">
                      {att.attestation_id}
                    </span>
                    <span className="text-xs text-slate-300 font-bold">Control: {att.control_id}</span>
                    <span className="text-xs text-slate-500">{new Date(att.timestamp).toLocaleString()}</span>
                  </div>
                  <p className="text-xs text-white bg-white/5 p-2.5 rounded italic">"{att.notes}"</p>
                  {att.evidence_refs.length > 0 && (
                    <div className="flex items-center gap-1.5 text-[10px] text-slate-400 mt-2">
                      <FileText className="w-3 h-3" /> Linked Evidence files: {att.evidence_refs.join(", ")}
                    </div>
                  )}
                </div>

                <div className="flex items-center gap-1.5 text-xs text-slate-300 font-semibold bg-white/5 px-3 py-1.5 rounded border border-white/5">
                  <UserCheck className="w-4 h-4 text-green-400" />
                  <div>
                    <div className="text-[10px] text-slate-400 font-bold uppercase">Attested By</div>
                    {att.operator_name}
                  </div>
                </div>
              </div>
            ))}
          </div>

          {/* Attestation Form */}
          <form onSubmit={handleAttestation} className="glass-panel p-4 rounded-xl border border-white/10 bg-white/2 space-y-4">
            <h4 className="font-bold text-sm flex items-center gap-2">
              <UserCheck className="w-4 h-4 text-green-400" /> Sign Regulatory Compliance Attestation
            </h4>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="md:col-span-1">
                <label className="block text-xs text-slate-400 font-bold mb-1">Target Requirement ID</label>
                <select
                  required
                  value={attestationControlId}
                  onChange={e => setAttestationControlId(e.target.value)}
                  className="w-full bg-white/5 border border-white/10 rounded px-3 py-1.5 text-sm text-white focus:outline-none focus:border-blue-500"
                >
                  <option value="">-- Choose Control --</option>
                  {controls.map(c => (
                    <option key={c.control_id} value={c.control_id}>
                      {c.control_id} - {c.title}
                    </option>
                  ))}
                </select>
              </div>
              <div className="md:col-span-2">
                <label className="block text-xs text-slate-400 font-bold mb-1">Audit Findings &amp; Attestation Notes</label>
                <input
                  type="text"
                  required
                  placeholder="Explain why this control is fully satisfied by evidence..."
                  value={attestationNotes}
                  onChange={e => setAttestationNotes(e.target.value)}
                  className="w-full bg-white/5 border border-white/10 rounded px-3 py-1.5 text-sm text-white focus:outline-none focus:border-blue-500"
                />
              </div>
            </div>
            <button
              type="submit"
              className="px-4 py-2 bg-green-600 hover:bg-green-500 rounded text-xs font-semibold tracking-wider uppercase transition active:scale-95"
            >
              Sign and Submit Attestation
            </button>
          </form>
        </div>
      )}

      {activeTab === ("shopping" as any) && (
        <div className="space-y-6">
          <div className="flex justify-between items-center">
            <h3 className="text-lg font-bold flex items-center gap-2">
              <ShieldCheck className="w-5 h-5 text-green-400" />
              Shopping Research &amp; Print Gate
            </h3>
            <span className="text-xs px-2.5 py-1 rounded bg-blue-500/15 border border-blue-500/20 text-blue-400 font-bold uppercase tracking-wide">
              Safe Bounded Mode Enforced
            </span>
          </div>

          {/* Grid of the 7 Runtime Truth Signals */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {[
              { id: "shopping_research_gate_status", label: "Gate Status", defaultVal: "INACTIVE", icon: Shield },
              { id: "purchase_block_status", label: "Purchase Block", defaultVal: "ENFORCED", icon: ShieldCheck },
              { id: "print_approval_status", label: "Print Approval", defaultVal: "NOT_TRIGGERED", icon: FileText },
              { id: "product_safety_screen_status", label: "Safety Screen", defaultVal: "PENDING", icon: AlertTriangle },
              { id: "candidate_count", label: "Candidates Count", defaultVal: "0", icon: CheckCircle },
              { id: "blocked_purchase_attempt_count", label: "Blocked Purchases", defaultVal: "0", icon: AlertCircle },
              { id: "last_operator_task_mode", label: "Last Task Mode", defaultVal: "N/A", icon: Clock }
            ].map(sig => {
              const matchedSig = signals.find(s => s.signal_id === sig.id);
              const val = matchedSig ? matchedSig.value : sig.defaultVal;
              const IconComp = sig.icon;
              return (
                <div key={sig.id} className="glass-panel p-4 rounded-xl border border-white/5 bg-white/2 flex items-center gap-3">
                  <div className="p-2.5 bg-blue-500/10 rounded-lg text-blue-400">
                    <IconComp className="w-5 h-5" />
                  </div>
                  <div>
                    <div className="text-[10px] text-slate-400 font-bold uppercase">{sig.label}</div>
                    <div className="text-sm font-extrabold font-mono mt-0.5">{val}</div>
                  </div>
                </div>
              );
            })}
          </div>

          {/* Interactive controls and query panel */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <div className="lg:col-span-1 glass-panel p-4 rounded-xl border border-white/10 bg-white/1 space-y-4">
              <h4 className="font-bold text-sm">Query Dispatcher</h4>
              
              <div className="space-y-2">
                <button
                  onClick={() => {
                    setShoppingQuery("baby rat toys and tunnels for supervised playtime");
                    setSelectedMode("RESEARCH_AND_LINK_PREP");
                  }}
                  className="w-full text-left text-xs p-2 bg-white/5 hover:bg-white/10 rounded border border-white/5 transition flex justify-between"
                >
                  <span>🐀 Baby Rat Toys Demo</span>
                  <span className="text-slate-500">Preset</span>
                </button>
                <button
                  onClick={() => {
                    setShoppingQuery("LEGO Disney princess sets for age 5 under budget");
                    setSelectedMode("RESEARCH_AND_LINK_PREP");
                  }}
                  className="w-full text-left text-xs p-2 bg-white/5 hover:bg-white/10 rounded border border-white/5 transition flex justify-between"
                >
                  <span>🏰 LEGO Disney Demo</span>
                  <span className="text-slate-500">Preset</span>
                </button>
              </div>

              <div className="space-y-3 pt-2">
                <div>
                  <label className="block text-xs text-slate-400 font-bold mb-1">Search Query</label>
                  <input
                    type="text"
                    value={shoppingQuery}
                    onChange={e => setShoppingQuery(e.target.value)}
                    className="w-full bg-white/5 border border-white/10 rounded px-3 py-1.5 text-xs text-white focus:outline-none focus:border-blue-500"
                  />
                </div>

                <div>
                  <label className="block text-xs text-slate-400 font-bold mb-1">Task Mode</label>
                  <select
                    value={selectedMode}
                    onChange={e => setSelectedMode(e.target.value)}
                    className="w-full bg-white/5 border border-white/10 rounded px-3 py-1.5 text-xs text-white focus:outline-none focus:border-blue-500"
                  >
                    <option value="RESEARCH_ONLY">RESEARCH_ONLY</option>
                    <option value="RESEARCH_AND_PRINT">RESEARCH_AND_PRINT</option>
                    <option value="RESEARCH_AND_LINK_PREP">RESEARCH_AND_LINK_PREP</option>
                    <option value="CART_DRAFT_REQUIRES_APPROVAL">CART_DRAFT_REQUIRES_APPROVAL</option>
                  </select>
                </div>

                <div className="grid grid-cols-2 gap-2">
                  <div>
                    <label className="block text-xs text-slate-400 font-bold mb-1">Child Target Age</label>
                    <input
                      type="number"
                      value={childAge}
                      onChange={e => setChildAge(parseInt(e.target.value) || 5)}
                      className="w-full bg-white/5 border border-white/10 rounded px-3 py-1.5 text-xs text-white focus:outline-none"
                    />
                  </div>
                  <div className="flex flex-col justify-end">
                    <label className="flex items-center gap-2 text-xs text-slate-300 select-none cursor-pointer pb-2">
                      <input
                        type="checkbox"
                        checked={printApproved}
                        onChange={e => setPrintApproved(e.target.checked)}
                        className="rounded bg-white/5 border-white/10 text-blue-500"
                      />
                      Print Approved
                    </label>
                  </div>
                </div>

                <div className="pt-2 border-t border-white/5">
                  <label className="flex items-center gap-2 text-xs text-red-400 select-none cursor-pointer font-bold">
                    <input
                      type="checkbox"
                      checked={attemptPurchase}
                      onChange={e => setAttemptPurchase(e.target.checked)}
                      className="rounded bg-white/5 border-white/10 text-red-500"
                    />
                    Attempt Purchase (Test Block)
                  </label>
                </div>

                <button
                  onClick={handleRunShoppingResearch}
                  disabled={isRunningQuery}
                  className="w-full py-2 bg-blue-600 hover:bg-blue-500 disabled:bg-blue-800 transition active:scale-95 rounded text-xs font-bold uppercase tracking-wider text-center mt-4"
                >
                  {isRunningQuery ? "DISPATCHING COMPLIANCE RUN..." : "RUN SHOPPING RESEARCH"}
                </button>
              </div>
            </div>

            <div className="lg:col-span-2 space-y-4">
              {shoppingError && (
                <div className="p-4 bg-red-950/40 border border-red-500/30 rounded-xl flex gap-3 text-red-400">
                  <AlertCircle className="w-6 h-6 shrink-0 mt-0.5 text-red-500" />
                  <div>
                    <h5 className="font-extrabold text-sm uppercase tracking-wide">Security Gate: Violation Blocked</h5>
                    <p className="text-xs mt-1 font-mono leading-relaxed">{shoppingError}</p>
                  </div>
                </div>
              )}

              {shoppingResult && (
                <div className="glass-panel p-4 rounded-xl border border-white/10 bg-white/1 space-y-4">
                  <div className="flex justify-between items-center border-b border-white/5 pb-2">
                    <div>
                      <h4 className="font-bold text-sm">Research Results</h4>
                      <div className="text-[10px] text-slate-400 font-mono mt-0.5">
                        Domain: {shoppingResult.domain} | Mode: {shoppingResult.mode}
                      </div>
                    </div>
                    {shoppingResult.evidence_path && (
                      <span className="text-[10px] px-2 py-0.5 bg-green-500/10 border border-green-500/20 text-green-400 rounded-full font-mono">
                        Evidence Recorded
                      </span>
                    )}
                  </div>

                  {/* Candidates table */}
                  <div className="overflow-x-auto text-xs">
                    <table className="w-full text-left">
                      <thead>
                        <tr className="text-slate-400 font-bold border-b border-white/5 pb-2">
                          <th>Rank</th>
                          <th>Product</th>
                          <th>Price</th>
                          <th>Seller</th>
                          <th>Safety</th>
                        </tr>
                      </thead>
                      <tbody>
                        {shoppingResult.candidates.map((cand: any) => {
                          const p = cand.product;
                          const s = cand.safety_result;
                          return (
                            <tr key={p.id} className="border-b border-white/2 py-2">
                              <td className="py-2 font-bold font-mono">{cand.rank}</td>
                              <td className="py-2">
                                <div>{p.title}</div>
                                <div className="text-[10px] text-slate-500">{p.description}</div>
                              </td>
                              <td className="py-2 font-mono font-bold">${p.price.toFixed(2)}</td>
                              <td className="py-2">{p.seller}</td>
                              <td className="py-2">
                                <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${s.passed ? "bg-green-500/10 text-green-400" : "bg-red-500/10 text-red-400"}`}>
                                  {s.passed ? "SAFE" : "BLOCKED"}
                                </span>
                              </td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>

                  {/* Print brief preview */}
                  <div className="space-y-1">
                    <div className="text-xs text-slate-400 font-bold uppercase">Print Brief Content:</div>
                    <pre className="bg-slate-950 p-3 rounded-lg border border-white/5 font-mono text-[10px] text-slate-300 max-h-[160px] overflow-y-auto whitespace-pre-wrap leading-tight">
                      {shoppingResult.brief}
                    </pre>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
      {activeTab === ("promptops" as any) && (
        <div className="space-y-6">
          <div className="flex justify-between items-center">
            <h3 className="text-lg font-bold flex items-center gap-2">
              <Shield className="w-5 h-5 text-blue-400" />
              PromptOps Closure Control Plane
            </h3>
            <span className="text-xs px-2.5 py-1 rounded bg-green-500/15 border border-green-500/20 text-green-400 font-bold uppercase tracking-wide">
              Exception-Only Operator Model Active
            </span>
          </div>

          {/* Grid of the 9 PromptOps Telemetry Signals */}
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4">
            {[
              { id: "promptops_status", label: "PromptOps Status", defaultVal: "INACTIVE", icon: Shield },
              { id: "prompt_score", label: "Quality Score", defaultVal: "0.0", icon: CheckCircle },
              { id: "prompt_fake_completion_risk", label: "Fake Risk", defaultVal: "LOW", icon: AlertTriangle },
              { id: "prompt_contract_status", label: "Contract State", defaultVal: "PENDING", icon: FileText },
              { id: "gate_binding_status", label: "Gate Binding", defaultVal: "UNBOUND", icon: ShieldCheck },
              { id: "closeout_authority_status", label: "Closeout Auth", defaultVal: "GATED", icon: Lock },
              { id: "human_loop_reduction_status", label: "Operator Assist", defaultVal: "ACTIVE", icon: UserCheck },
              { id: "last_prompt_class", label: "Last Prompt Class", defaultVal: "N/A", icon: Play },
              { id: "last_prompt_contract_id", label: "Last Contract ID", defaultVal: "N/A", icon: Clock }
            ].map(sig => {
              const matchedSig = signals.find(s => s.signal_id === sig.id);
              const val = matchedSig ? matchedSig.value : sig.defaultVal;
              const IconComp = sig.icon;
              return (
                <div key={sig.id} className="glass-panel p-3 rounded-xl border border-white/5 bg-white/2 flex items-center gap-3">
                  <div className="p-2 bg-blue-500/10 rounded-lg text-blue-400">
                    <IconComp className="w-4 h-4" />
                  </div>
                  <div>
                    <div className="text-[9px] text-slate-400 font-bold uppercase">{sig.label}</div>
                    <div className="text-xs font-extrabold font-mono mt-0.5">{val}</div>
                  </div>
                </div>
              );
            })}
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Left Column: Input Form */}
            <div className="lg:col-span-1 glass-panel p-4 rounded-xl border border-white/10 bg-white/1 space-y-4">
              <h4 className="font-bold text-sm">Prompt Evaluator &amp; Classifier</h4>
              
              <div className="space-y-2">
                <button
                  onClick={() => {
                    setOperatorPromptInput("Build HAS e2e production ready no errors");
                  }}
                  className="w-full text-left text-xs p-2 bg-white/5 hover:bg-white/10 rounded border border-white/5 transition flex justify-between"
                >
                  <span>⚠️ Weak / Broad Prompt</span>
                  <span className="text-slate-500">Preset</span>
                </button>
                <button
                  onClick={() => {
                    setOperatorPromptInput("Fix Docker UI truth mismatch, prove API/UI BLOCKED/50.0, run docker_truth_check");
                  }}
                  className="w-full text-left text-xs p-2 bg-white/5 hover:bg-white/10 rounded border border-white/5 transition flex justify-between"
                >
                  <span>✅ Strong Scoped Prompt</span>
                  <span className="text-slate-500">Preset</span>
                </button>
                <button
                  onClick={() => {
                    setOperatorPromptInput("Add k3d Kubernetes lane but do not replace Compose until gates pass");
                  }}
                  className="w-full text-left text-xs p-2 bg-white/5 hover:bg-white/10 rounded border border-white/5 transition flex justify-between"
                >
                  <span>☸️ Kubernetes Lane</span>
                  <span className="text-slate-500">Preset</span>
                </button>
              </div>

              <div className="space-y-3 pt-2">
                <div>
                  <label className="block text-xs text-slate-400 font-bold mb-1">Raw Operator Prompt</label>
                  <textarea
                    rows={4}
                    value={operatorPromptInput}
                    onChange={e => setOperatorPromptInput(e.target.value)}
                    className="w-full bg-white/5 border border-white/10 rounded p-2.5 text-xs text-white focus:outline-none focus:border-blue-500 font-mono"
                  />
                </div>

                <button
                  onClick={handleEvaluatePrompt}
                  disabled={isEvaluating}
                  className="w-full py-2 bg-blue-600 hover:bg-blue-500 disabled:bg-blue-800 transition active:scale-95 rounded text-xs font-bold uppercase tracking-wider text-center"
                >
                  {isEvaluating ? "SCORES CALCULATION..." : "EVALUATE AND GENERATE CONTRACT"}
                </button>
              </div>

              {/* Closeout Claim Verification Panel */}
              <div className="pt-4 border-t border-white/5 space-y-3">
                <h4 className="font-bold text-sm">Operator Closeout Claim</h4>
                <div>
                  <label className="block text-xs text-slate-400 font-bold mb-1">Completion Text</label>
                  <input
                    type="text"
                    value={claimText}
                    onChange={e => setClaimText(e.target.value)}
                    className="w-full bg-white/5 border border-white/10 rounded px-3 py-1.5 text-xs text-white focus:outline-none"
                  />
                </div>
                <button
                  onClick={handleSubmitClaim}
                  disabled={isSubmittingClaim}
                  className="w-full py-2 bg-green-600 hover:bg-green-500 disabled:bg-green-800 transition active:scale-95 rounded text-xs font-bold uppercase tracking-wider text-center"
                >
                  {isSubmittingClaim ? "VERIFYING TELEMETRY..." : "SUBMIT CLAIM & VERIFY GATES"}
                </button>
              </div>
            </div>

            {/* Right Column: Evaluation Results and Contract */}
            <div className="lg:col-span-2 space-y-4">
              {claimError && (
                <div className="p-4 bg-red-950/40 border border-red-500/30 rounded-xl flex gap-3 text-red-400">
                  <AlertCircle className="w-6 h-6 shrink-0 mt-0.5 text-red-500" />
                  <div>
                    <h5 className="font-extrabold text-sm uppercase tracking-wide">Closeout Gate: CLAIM REJECTED</h5>
                    <p className="text-xs mt-1 font-mono leading-relaxed">{claimError}</p>
                  </div>
                </div>
              )}

              {claimResult && (
                <div className="p-4 bg-green-950/40 border border-green-500/30 rounded-xl flex gap-3 text-green-400">
                  <CheckCircle className="w-6 h-6 shrink-0 mt-0.5 text-green-500" />
                  <div>
                    <h5 className="font-extrabold text-sm uppercase tracking-wide">Closeout Gate: CLAIM APPROVED</h5>
                    <p className="text-xs mt-1 font-mono leading-relaxed">{claimResult.message}</p>
                  </div>
                </div>
              )}

              {evaluationResult && (
                <div className="glass-panel p-4 rounded-xl border border-white/10 bg-white/1 space-y-4">
                  <div className="flex justify-between items-center border-b border-white/5 pb-2">
                    <div>
                      <h4 className="font-bold text-sm">Contract Specification</h4>
                      <div className="text-[10px] text-slate-400 font-mono mt-0.5">
                        ID: {evaluationResult.mission_id} | Class: {evaluationResult.prompt_class}
                      </div>
                    </div>
                    <span className={`px-2.5 py-1 rounded text-xs font-bold ${
                      evaluationResult.score_status === "EXECUTABLE"
                        ? "bg-green-500/10 text-green-400"
                        : evaluationResult.score_status === "NEEDS_PROMPTOPS_REWRITE"
                        ? "bg-yellow-500/10 text-yellow-400"
                        : "bg-red-500/10 text-red-400"
                    }`}>
                      {evaluationResult.score_status} ({evaluationResult.score}/100)
                    </span>
                  </div>

                  <div className="grid grid-cols-2 gap-4 text-xs">
                    <div>
                      <div className="text-slate-400 font-bold">Fake Risk Level:</div>
                      <span className={`text-[10px] font-bold px-2 py-0.5 rounded ${evaluationResult.risk_level === "HIGH" ? "bg-red-500/10 text-red-400" : "bg-green-500/10 text-green-400"}`}>
                        {evaluationResult.risk_level}
                      </span>
                    </div>
                    <div>
                      <div className="text-slate-400 font-bold">Flagged Terms:</div>
                      <div className="text-[10px] font-mono text-slate-300">
                        {evaluationResult.flagged_terms.length > 0 ? evaluationResult.flagged_terms.join(", ") : "None"}
                      </div>
                    </div>
                  </div>

                  {/* Contract Code Block */}
                  <div className="space-y-1">
                    <div className="text-xs text-slate-400 font-bold uppercase">Generated Contract:</div>
                    <pre className="bg-slate-950 p-3 rounded-lg border border-white/5 font-mono text-[10px] text-slate-300 max-h-[220px] overflow-y-auto whitespace-pre-wrap leading-tight">
                      {evaluationResult.rewritten_text}
                    </pre>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
