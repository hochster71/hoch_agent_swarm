import React, { useState, useEffect } from "react";
import { DistributedSolverMesh } from "./DistributedSolverMesh";
import { CandidateSolutionList } from "./CandidateSolutionList";
import { SolutionComparisonPanel } from "./SolutionComparisonPanel";
import { SolutionMemoryCorpus } from "./SolutionMemoryCorpus";
import { PullRequestAutomationPanel } from "./PullRequestAutomationPanel";

import { HochsterSecurityCertification } from "./security/HochsterSecurityCertification";
import { RedTeamScenarioSuite } from "./security/RedTeamScenarioSuite";
import { SupplyChainControlPanel } from "./security/SupplyChainControlPanel";
import { CertificationReportPanel } from "./security/CertificationReportPanel";

import { HochsterProductionRollout } from "./product/HochsterProductionRollout";
import { HochsterSlaDashboard } from "./product/HochsterSlaDashboard";
import { UsageQuotaPanel } from "./product/UsageQuotaPanel";
import { BillingMetricsPanel } from "./product/BillingMetricsPanel";
import { SupportPlaybookPanel } from "./product/SupportPlaybookPanel";
import { BaselineLockPanel } from "./BaselineLockPanel";
import { HochsterJobQueuePanel } from "./HochsterJobQueuePanel";

import { RealtimeWrapper } from "./RealtimeWrapper";
import { wrapRealtime } from "../../lib/realtime/freshness";
import { RealtimeUiDatum } from "../../lib/realtime/realtimeTypes";

import { mockCandidates, mockMemoryRecords, mockCertificationReport } from "../../lib/hochster/hochsterFixtures";

export const HochsterDashboard: React.FC = () => {
  // Initialize states with wrapRealtime mock wrappers
  const [candidatesDatum, setCandidatesDatum] = useState<RealtimeUiDatum<any>>(
    wrapRealtime(mockCandidates, "simulation", "solver-coordinator", 10000)
  );
  const [memoryDatum, setMemoryDatum] = useState<RealtimeUiDatum<any>>(
    wrapRealtime(mockMemoryRecords, "simulation", "solution-memory-store", 30000)
  );
  const [certDatum, setCertDatum] = useState<RealtimeUiDatum<any>>(
    wrapRealtime(mockCertificationReport, "simulation", "security-certification", 30000)
  );
  const [sloDatum, setSloDatum] = useState<RealtimeUiDatum<any>>(
    wrapRealtime([], "simulation", "hochster-slo", 15000)
  );
  const [rolloutDatum, setRolloutDatum] = useState<RealtimeUiDatum<any>>(
    wrapRealtime(null, "simulation", "rollout-rings", 20000)
  );
  const [billingDatum, setBillingDatum] = useState<RealtimeUiDatum<any>>(
    wrapRealtime({ totalRequests: 0, billableRequests: 0, estChargeback: 0, costPerRequest: 0 }, "simulation", "billing-metrics", 15000)
  );
  const [quotasDatum, setQuotasDatum] = useState<RealtimeUiDatum<any>>(
    wrapRealtime([], "simulation", "usage-quotas", 15000)
  );
  const [healthDatum, setHealthDatum] = useState<RealtimeUiDatum<any>>(
    wrapRealtime([], "simulation", "cluster-health", 5000)
  );

  const [selectedCandidateId, setSelectedCandidateId] = useState<string | null>("cand_01");
  const [lockDecision, setLockDecision] = useState<string>("PASS");

  // Fetch live telemetry from the backend API
  const fetchTelemetry = async () => {
    try {
      // 1. Fetch Candidates
      const candRes = await fetch("/api/v1/hochster/mesh/candidates");
      if (candRes.ok) {
        const data = await candRes.json();
        setCandidatesDatum(wrapRealtime(data.candidates, "live", "solver-coordinator", 10000, data.correlation_id, ["rec_l3_1"]));
      }

      // 2. Fetch Memory Records
      const memRes = await fetch("/api/v1/hochster/memory/records");
      if (memRes.ok) {
        const data = await memRes.json();
        setMemoryDatum(wrapRealtime(data.records, "live", "solution-memory-store", 30000, data.correlation_id, ["rec_l3_1"]));
      }

      // 3. Fetch Security Certification
      const certRes = await fetch("/api/v1/hochster/security/certification");
      if (certRes.ok) {
        const data = await certRes.json();
        setCertDatum(wrapRealtime(data.report, "live", "security-certification", 30000, data.correlation_id, ["rec_l3_1"]));
      }

      // 4. Fetch SLO
      const sloRes = await fetch("/api/v1/hochster/product/slo");
      if (sloRes.ok) {
        const data = await sloRes.json();
        setSloDatum(wrapRealtime(data.slos, "live", "hochster-slo", 15000, data.correlation_id));
      }

      // 5. Fetch Rollout
      const rolloutRes = await fetch("/api/v1/hochster/product/rollout");
      if (rolloutRes.ok) {
        const data = await rolloutRes.json();
        setRolloutDatum(wrapRealtime(data.rollout, "live", "rollout-rings", 20000, data.correlation_id));
      }

      // 6. Fetch Billing
      const billRes = await fetch("/api/v1/hochster/product/billing");
      if (billRes.ok) {
        const data = await billRes.json();
        setBillingDatum(wrapRealtime(data.billing, "live", "billing-metrics", 15000, data.correlation_id));
      }

      // 7. Fetch Quotas
      const quotaRes = await fetch("/api/v1/hochster/product/quotas");
      if (quotaRes.ok) {
        const data = await quotaRes.json();
        setQuotasDatum(wrapRealtime(data.quotas, "live", "usage-quotas", 15000, data.correlation_id));
      }

      // 8. Fetch Health
      const healthRes = await fetch("/api/v1/hochster/health");
      if (healthRes.ok) {
        const data = await healthRes.json();
        setHealthDatum(wrapRealtime(data.services, "live", "cluster-health", 5000, data.correlation_id));
      }

      // 9. Fetch Baseline Lock
      try {
        const lockRes = await fetch("/api/v1/hochster/baseline/lock");
        if (lockRes.ok) {
          const data = await lockRes.json();
          setLockDecision(data.report.decision.status);
        }
      } catch (err) {
        console.error("Failed to fetch baseline lock status", err);
      }
    } catch (e) {
      console.error("Failed to fetch live dashboard telemetry", e);
    }
  };

  useEffect(() => {
    fetchTelemetry();
    // Poll endpoints every 4 seconds
    const interval = setInterval(fetchTelemetry, 4000);
    return () => clearInterval(interval);
  }, []);

  const candidatesList = candidatesDatum.value || [];
  const selectedCandidate = candidatesList.find((c: any) => c.candidate_id === selectedCandidateId) || candidatesList[0];

  const getServiceStatus = (id: string): "online" | "offline" => {
    const services = healthDatum.value || [];
    const svc = services.find((s: any) => s.id === id);
    return svc ? svc.status : "offline";
  };

  const getStatusBadge = (statusStr: string) => {
    let colorClass = "";
    switch (statusStr.toUpperCase()) {
      case "ONLINE":
      case "LIVE":
      case "VERIFIED":
      case "ACTIVE":
      case "RUNNING":
      case "PASS":
        colorClass = "bg-green-500/10 text-green-400 border border-green-500/20";
        break;
      case "STALE":
      case "DEGRADED":
      case "INACTIVE":
        colorClass = "bg-yellow-500/10 text-yellow-400 border border-yellow-500/20 animate-pulse";
        break;
      case "BLOCK":
      case "OFFLINE":
      case "STOPPED":
      case "ERROR":
      case "BLOCKED":
      case "FAIL":
        colorClass = "bg-red-500/10 text-red-400 border border-red-500/20 animate-pulse";
        break;
      case "SIMULATED":
        colorClass = "bg-purple-500/10 text-purple-400 border border-purple-500/20";
        break;
      default:
        colorClass = "bg-slate-500/10 text-slate-400 border border-slate-500/20";
    }
    return (
      <span className={`inline-block px-2 py-0.5 rounded text-[10px] font-mono font-bold uppercase tracking-wider ${colorClass}`}>
        {statusStr}
      </span>
    );
  };

  const isApiOnline = getServiceStatus("hochster-api-01") === "online";
  const isTelemetryOnline = getServiceStatus("hochster-telemetry-01") === "online";
  const isAuditOnline = getServiceStatus("hochster-audit-01") === "online";
  const isPolicyOnline = getServiceStatus("hochster-policy-01") === "online";
  const isDockerOnline = getServiceStatus("hochster-docker-01") === "online";

  const totalServices = healthDatum.value?.length || 0;
  const onlineServicesCount = (healthDatum.value || []).filter((s: any) => s.status === "online").length;

  const sysStatus = isApiOnline ? "ONLINE" : "OFFLINE";
  const telStatus = isTelemetryOnline ? "LIVE" : "STALE";
  const auditStatus = isAuditOnline ? "VERIFIED" : "BLOCKED";
  const policyStatus = isPolicyOnline ? "ACTIVE" : "INACTIVE";
  const clusterStatus = totalServices > 0 && onlineServicesCount === totalServices ? "ACTIVE" : "DEGRADED";
  const dockerStatus = isDockerOnline ? "RUNNING" : "STOPPED";
  const gateStatus = lockDecision || "BLOCK";

  return (
    <div className="space-y-6 text-white pb-10">
      {/* Top Header stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 xl:grid-cols-7 gap-4 bg-slate-900/60 border border-white/10 p-4 rounded-2xl backdrop-blur-md text-left">
        <div>
          <span className="text-[9px] text-slate-400 font-bold uppercase tracking-wider block">System Status</span>
          <div className="mt-1.5">{getStatusBadge(sysStatus)}</div>
          <span className="text-[8px] text-slate-400 block mt-1">API Controller Heartbeat</span>
        </div>

        <div>
          <span className="text-[9px] text-slate-400 font-bold uppercase tracking-wider block">Telemetry Status</span>
          <div className="mt-1.5">{getStatusBadge(telStatus)}</div>
          <span className="text-[8px] text-slate-400 block mt-1">OTel Heartbeat Stream</span>
        </div>

        <div>
          <span className="text-[9px] text-slate-400 font-bold uppercase tracking-wider block">Audit Stream</span>
          <div className="mt-1.5">{getStatusBadge(auditStatus)}</div>
          <span className="text-[8px] text-slate-400 block mt-1">Ledger Chain Verification</span>
        </div>

        <div>
          <span className="text-[9px] text-slate-400 font-bold uppercase tracking-wider block">Policy Engine</span>
          <div className="mt-1.5">{getStatusBadge(policyStatus)}</div>
          <span className="text-[8px] text-slate-400 block mt-1">Server-Side Gate Control</span>
        </div>

        <div>
          <span className="text-[9px] text-slate-400 font-bold uppercase tracking-wider block">HOCHSTER Cluster</span>
          <div className="mt-1.5">{getStatusBadge(clusterStatus)}</div>
          <span className="text-[8px] text-slate-400 block mt-1">{onlineServicesCount}/{totalServices || 8} Node Roles Active</span>
        </div>

        <div>
          <span className="text-[9px] text-slate-400 font-bold uppercase tracking-wider block">Docker Runtime</span>
          <div className="mt-1.5">{getStatusBadge(dockerStatus)}</div>
          <span className="text-[8px] text-slate-400 block mt-1">Socket Health Check</span>
        </div>

        <div>
          <span className="text-[9px] text-slate-400 font-bold uppercase tracking-wider block">Baseline Gate</span>
          <div className="mt-1.5">{getStatusBadge(gateStatus)}</div>
          <span className="text-[8px] text-slate-400 block mt-1">v0.1.0-RT-LOCK State</span>
        </div>
      </div>

      {/* Main 3 Column Mesh dashboard */}
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
        
        {/* Phase 25 column */}
        <div className="space-y-6">
          <div className="p-3 bg-blue-600/10 border border-blue-500/20 rounded-xl text-left">
            <span className="text-[9px] font-bold text-blue-400 uppercase tracking-widest block">Phase 25</span>
            <span className="text-xs font-semibold text-white block mt-0.5">Distributed Solver Mesh, Memory Corpus & PR Automation</span>
          </div>

          <RealtimeWrapper datum={candidatesDatum} onRefresh={fetchTelemetry}>
            <DistributedSolverMesh
              candidates={candidatesList}
              onSelectCandidate={setSelectedCandidateId}
              selectedCandidateId={selectedCandidateId}
            />
          </RealtimeWrapper>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <RealtimeWrapper datum={candidatesDatum}>
              <CandidateSolutionList
                candidates={candidatesList}
                onSelectCandidate={setSelectedCandidateId}
                selectedCandidateId={selectedCandidateId}
              />
            </RealtimeWrapper>
            <RealtimeWrapper datum={candidatesDatum}>
              <SolutionComparisonPanel
                candidateA={candidatesList[0]}
                candidateB={candidatesList[1]}
              />
            </RealtimeWrapper>
          </div>

          <RealtimeWrapper datum={memoryDatum}>
            <SolutionMemoryCorpus records={memoryDatum.value || []} />
          </RealtimeWrapper>

          {selectedCandidate && (
            <RealtimeWrapper datum={candidatesDatum}>
              <PullRequestAutomationPanel candidate={selectedCandidate} />
            </RealtimeWrapper>
          )}
        </div>

        {/* Phase 26 column */}
        <div className="space-y-6">
          <div className="p-3 bg-green-600/10 border border-green-500/20 rounded-xl text-left">
            <span className="text-[9px] font-bold text-green-400 uppercase tracking-widest block">Phase 26</span>
            <span className="text-xs font-semibold text-white block mt-0.5">Security Certification, Red-Team Harness & Supply-Chain Controls</span>
          </div>

          <RealtimeWrapper datum={certDatum}>
            <HochsterSecurityCertification report={certDatum.value} />
          </RealtimeWrapper>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <RealtimeWrapper datum={certDatum}>
              <RedTeamScenarioSuite />
            </RealtimeWrapper>
            <RealtimeWrapper datum={certDatum}>
              <SupplyChainControlPanel />
            </RealtimeWrapper>
          </div>

          <RealtimeWrapper datum={certDatum}>
            <CertificationReportPanel />
          </RealtimeWrapper>

          {/* Baseline Lock dashboard Panel */}
          <HochsterJobQueuePanel />
          <BaselineLockPanel />
        </div>

        {/* Phase 27 column */}
        <div className="space-y-6">
          <div className="p-3 bg-yellow-600/10 border border-yellow-500/20 rounded-xl text-left">
            <span className="text-[9px] font-bold text-yellow-400 uppercase tracking-widest block">Phase 27</span>
            <span className="text-xs font-semibold text-white block mt-0.5">Production Rollout, SLA Monitoring & Marketplace Packaging</span>
          </div>

          {rolloutDatum.value && (
            <RealtimeWrapper datum={rolloutDatum}>
              <HochsterProductionRollout />
            </RealtimeWrapper>
          )}

          <RealtimeWrapper datum={sloDatum}>
            <HochsterSlaDashboard slos={sloDatum.value || []} />
          </RealtimeWrapper>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <RealtimeWrapper datum={quotasDatum}>
              <UsageQuotaPanel quotas={quotasDatum.value || []} />
            </RealtimeWrapper>
            <RealtimeWrapper datum={billingDatum}>
              <BillingMetricsPanel billing={billingDatum.value} />
            </RealtimeWrapper>
          </div>

          <RealtimeWrapper datum={rolloutDatum}>
            <SupportPlaybookPanel />
          </RealtimeWrapper>
        </div>

      </div>
    </div>
  );
};
