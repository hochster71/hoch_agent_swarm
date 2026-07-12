import React, { useEffect, useState, useRef } from "react";
import { Brain, Info } from "lucide-react";
import { fetchJsonWithStatus } from "../../lib/helmApiClient";

type AnyObj = Record<string, any>;

const CONFIG = {
  FRESH_MS: 90_000,
  STALE_MS: 600_000
};

const S = {
  GO: 'go',
  CONDITIONAL: 'cond',
  STALE: 'stale',
  BLOCKED: 'blocked',
  UNKNOWN: 'unknown'
};

// No mock success payload — fail-closed when authoritative burn-in status is unavailable.

export const HochNeuroVisualization: React.FC = () => {
  const [data, setData] = useState<AnyObj | null>(null);
  const [hoveredNode, setHoveredNode] = useState<string | null>(null);
  const [fetchedAt, setFetchedAt] = useState<string>("");
  const [isLive, setIsLive] = useState<boolean>(false);
  const [loadError, setLoadError] = useState<string | null>(null);

  const ecgRef = useRef<SVGPolylineElement>(null);

  useEffect(() => {
    let alive = true;
    const load = async () => {
      try {
        const response = await fetchJsonWithStatus<any>("/api/burn-in/status");
        if (response.status !== "OK" || !response.data) throw new Error(`HTTP Status ${response.status}`);
        if (!alive) return;
        setData(response.data);
        setIsLive(true);
        setLoadError(null);
        setFetchedAt(new Date().toLocaleTimeString());
      } catch (err) {
        if (!alive) return;
        // Clear prior success — do not retain green mock state (no-fake-green)
        setData(null);
        setIsLive(false);
        setLoadError(err instanceof Error ? err.message : String(err));
        setFetchedAt(new Date().toLocaleTimeString() + " (AUTHORITATIVE_SOURCE_UNAVAILABLE)");
      }
    };

    load();
    const interval = setInterval(load, 10000);
    return () => {
      alive = false;
      clearInterval(interval);
    };
  }, []);

  // ECG animation tick
  useEffect(() => {
    if (!data) return;

    let ecgX = 0;
    let beatBoost = 0;
    let lastCycle = data.ledger_proof?.current_cycle_count;
    let animId = 0;

    const freshnessReport = data.freshness || {};
    const anyStale = Object.values(freshnessReport).some(
      (f: any) => f?.status === "STALE" || f?.status === "EXPIRED" || f?.status === "UNKNOWN"
    );
    const isCoreFresh = data.heartbeat_status === "HEARTBEAT_FRESH" && !anyStale;

    const tick = () => {
      if (!ecgRef.current) return;
      const w = 880, base = 524, mid = 60;

      const currentCycle = data.ledger_proof?.current_cycle_count;
      if (currentCycle != null && currentCycle !== lastCycle) {
        beatBoost = 1;
        lastCycle = currentCycle;
      }

      const active = isCoreFresh || beatBoost > 0;
      const step = active ? 4.5 : 2.0;
      beatBoost = Math.max(0, beatBoost - 0.02);

      let points = "";
      const period = active ? 120 : 260;

      for (let x = 0; x <= w; x += 4) {
        const gx = mid + x;
        const ph = (x + ecgX) % period;
        let y = base;

        if (active && ph > period - 26 && ph < period - 6) {
          const k = (ph - (period - 26)) / 20;
          y = base - Math.sin(k * Math.PI) * (k < 0.5 ? 6 : 28) * (k < 0.35 ? 0.4 : 1);
          if (k > 0.45 && k < 0.62) y = base + 16; // QRS complex dip
        }

        points += `${gx},${y} `;
      }

      ecgRef.current.setAttribute("points", points.trim());
      ecgRef.current.setAttribute("stroke", isLive ? (active ? "#3ad07a" : "#2a6a44") : "#8a2b34");

      ecgX = (ecgX + step) % 1000000;
      animId = requestAnimationFrame(tick);
    };

    animId = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(animId);
  }, [data, isLive]);

  if (!data) {
    return (
      <div className="rounded-lg border border-slate-900 bg-[#03050b] p-6 text-center font-mono text-xs">
        {loadError ? (
          <span className="text-red-400">
            HOCH NEURO status UNKNOWN — authoritative source unavailable ({loadError}). No simulated GO state.
          </span>
        ) : (
          <span className="text-slate-500">Loading HOCH NEURO dynamic angiogram…</span>
        )}
      </div>
    );
  }

  // Derived core status
  const freshnessReport = data.freshness || {};
  const anyStale = Object.values(freshnessReport).some(
    (f: any) => f?.status === "STALE" || f?.status === "EXPIRED" || f?.status === "UNKNOWN"
  );
  const isCoreFresh = data.heartbeat_status === "HEARTBEAT_FRESH" && !anyStale;

  // Liveness mapping helper
  const getRegionState = (id: string) => {
    if (id === "relay-001") {
      const isStale = data.heartbeat_status === "HEARTBEAT_STALE";
      const isBlocked = !!data.policy_explainer?.operator_hold || (data.policy_explainer?.blocked_by && data.policy_explainer.blocked_by.length > 0);
      const isRunning = data.daemon_state?.daemon_status === "RUNNING";
      const status = isStale ? "STALE" : isBlocked ? "BLOCKED" : isRunning ? "ONLINE" : "OFFLINE";

      return {
        status,
        isStale,
        isBlocked,
        isGo: status === "ONLINE" && !isStale && !isBlocked,
        owner: "Orchestrator",
        blocker: isBlocked ? (data.policy_explainer?.blocked_by?.join(", ") || "Operator hold") : "None",
        evidence: data.ledger_proof?.ledger_path || "has_live_project_tracker/data/ag_execution_burn_in_ledger.jsonl",
        nextAction: data.mission_commander?.exact_next_safe_action || "pytest tests/integration/test_relay_checks.py",
        lastUpdateAge: freshnessReport.daemon_state?.age_seconds != null ? `${freshnessReport.daemon_state.age_seconds}s` : "UNKNOWN"
      };
    }

    if (id === "HSF") {
      return {
        status: "UNKNOWN",
        isStale: true,
        isBlocked: false,
        isGo: false,
        owner: "HSF-Story-Studio",
        blocker: "None",
        evidence: "docs/evidence/hsf_chronicle.md",
        nextAction: "None",
        lastUpdateAge: "UNKNOWN"
      };
    }

    const lane = data.factory_lanes?.[id];
    if (!lane) {
      return {
        status: "UNKNOWN",
        isStale: true,
        isBlocked: false,
        isGo: false,
        owner: `${id}-Agent`,
        blocker: "None",
        evidence: "None",
        nextAction: "None",
        lastUpdateAge: "UNKNOWN"
      };
    }

    const isStale = lane.stale_status !== "FRESH" || lane.status === "STALE";
    const isBlocked = lane.status === "BLOCKED" || (lane.blocked_by && lane.blocked_by !== "None" && lane.blocked_by !== "");
    const status = isBlocked ? "BLOCKED" : isStale ? "STALE" : lane.status || "UNKNOWN";

    return {
      status,
      isStale,
      isBlocked,
      isGo: (status === "CONVERGED" || status === "IMPROVING" || status === "GO") && !isStale && !isBlocked,
      owner: lane.owner_agent || "Orchestrator",
      blocker: lane.blocked_by || "None",
      evidence: lane.evidence || "None",
      nextAction: lane.next_action || "None",
      lastUpdateAge: freshnessReport[id]?.age_seconds != null ? `${freshnessReport[id].age_seconds}s` : (isStale ? "STALE" : "FRESH")
    };
  };

  const hasf = getRegionState("HASF");
  const hmf = getRegionState("HMF");
  const hrf = getRegionState("HRF");
  const hsf = getRegionState("HSF");
  const relay = getRegionState("relay-001");

  const getArteryConfig = (stateObj: ReturnType<typeof getRegionState>, defaultColor: string) => {
    if (stateObj.isGo) return { color: defaultColor, width: 4.5, opacity: 1.0, glow: true, dur: "2.0s" };
    if (stateObj.status === "CONDITIONAL") return { color: "#f5b23d", width: 3.5, opacity: 0.95, glow: true, dur: "3.5s" };
    if (stateObj.isStale) return { color: "#5a6480", width: 2.2, opacity: 0.5, glow: false, dur: "6.0s", dash: "2 8" };
    if (stateObj.isBlocked) return { color: "#5a2530", width: 3.0, opacity: 0.6, glow: false, dur: null };
    return { color: "#3a4766", width: 2.0, opacity: 0.4, glow: false, dur: null, dash: "1 8" };
  };

  const aHasf = getArteryConfig(hasf, "#ff6b52");
  const aHsf = getArteryConfig(hsf, "#ff7a4d");
  const aHrf = getArteryConfig(hrf, "#ff6b52");
  const aHmf = getArteryConfig(hmf, "#ff5e6e");
  const aRelay = getArteryConfig(relay, "#ff5a3c");

  const activeCardInfo = hoveredNode ? getRegionState(hoveredNode) : null;

  return (
    <div className="rounded-xl border border-slate-900 bg-[#03050b] p-6 text-slate-100 font-mono relative overflow-hidden select-none">
      {/* Quiet top system pulse strip */}
      <div className="flex flex-wrap items-center justify-between gap-4 border-b border-slate-950 pb-4 mb-6 text-[10px] text-slate-500">
        <div className="flex items-center gap-1.5 font-bold tracking-wider text-slate-400">
          <Brain className="h-3.5 w-3.5 text-[#38e6ff]" />
          HOCH NEURO RUNTIME VISUALIZATION
        </div>
        <div className="flex flex-wrap gap-x-6 gap-y-1">
          <div>cycle: <span className="text-slate-300 font-bold">{data.ledger_proof?.current_cycle_count ?? "UNKNOWN"}</span></div>
          <div>posture: <span className={`font-bold ${data.policy_explainer?.operator_hold ? "text-amber-500" : "text-green-500"}`}>{data.policy_explainer?.operator_hold ? "HOLD" : "ALLOW"}</span></div>
          <div>governor: <span className={`font-bold ${data.mission_commander?.verdict === "GO" ? "text-green-500" : "text-red-500"}`}>{data.mission_commander?.verdict ?? "UNKNOWN"}</span></div>
          <div>relay: <span className={`font-bold ${relay.status === "ONLINE" ? "text-green-500" : "text-red-500"}`}>{relay.status}</span></div>
          <div>freshness: <span className="text-slate-300">{freshnessReport.daemon_state?.age_seconds != null ? `${freshnessReport.daemon_state.age_seconds}s` : "UNKNOWN"}</span></div>
          <div className="text-[9px] opacity-65 text-slate-600">source: {isLive ? "relay-001" : "offline emulation"}</div>
        </div>
      </div>

      {/* Main angio stage */}
      <div className="relative w-full flex justify-center items-center">
        <svg className="stage w-full max-w-[960px] h-auto bg-transparent" viewBox="0 0 1000 560" xmlns="http://www.w3.org/2000/svg">
          <defs>
            <radialGradient id="gcortex" cx="42%" cy="33%" r="80%">
              <stop offset="0%" stopColor="#142138" />
              <stop offset="55%" stopColor="#080c18" />
              <stop offset="100%" stopColor="#03050c" />
            </radialGradient>
            <radialGradient id="gcore" cx="50%" cy="50%" r="50%">
              <stop offset="0%" stopColor="#8ff6ff" />
              <stop offset="45%" stopColor="#2fd0ee" />
              <stop offset="100%" stopColor="#0a2f3e" stopOpacity="0" />
            </radialGradient>
            <radialGradient id="gspec" cx="50%" cy="50%" r="50%">
              <stop offset="0%" stopColor="#bcd6ff" stopOpacity="0.22" />
              <stop offset="100%" stopColor="#bcd6ff" stopOpacity="0" />
            </radialGradient>
            <filter id="fglow" x="-60%" y="-60%" width="220%" height="220%">
              <feGaussianBlur stdDeviation="3.2" result="b" />
              <feMerge>
                <feMergeNode in="b" />
                <feMergeNode in="SourceGraphic" />
              </feMerge>
            </filter>
            <filter id="fsoft" x="-40%" y="-40%" width="180%" height="180%">
              <feGaussianBlur stdDeviation="6" />
            </filter>
          </defs>

          {/* Shadows */}
          <ellipse cx="500" cy="470" rx="300" ry="34" fill="#000" opacity="0.55" filter="url(#fsoft)" />

          {/* Cerebrum body silhouette */}
          <g id="brainbody">
            <path d="M250 330 C205 215 320 120 470 116 C600 112 728 150 782 232 C820 290 812 356 758 392 C734 408 734 420 760 438 C734 466 650 460 628 440 C586 470 486 476 420 456 C346 484 280 442 280 414 C250 414 232 372 250 330 Z"
                  fill="url(#gcortex)" stroke="#1a2b4b" strokeWidth="1" />

            {/* gyri sheen */}
            <g fill="none" stroke="#253a5c" strokeOpacity="0.45" strokeWidth="2" strokeLinecap="round">
              <path d="M300 290 C350 262 360 320 420 296 C480 272 486 330 548 306" />
              <path d="M318 356 C368 336 380 392 440 372 C500 352 512 400 576 382" />
              <path d="M340 214 C392 190 408 244 470 224 C532 204 548 250 612 236" />
              <path d="M430 158 C486 140 504 196 566 178 C628 160 644 206 706 196" />
              <path d="M560 132 C614 124 636 178 694 168 C742 160 760 200 786 210" />
              <path d="M600 420 C654 400 664 342 724 346" />
            </g>
            <ellipse cx="420" cy="230" rx="180" ry="120" fill="url(#gspec)" />
          </g>

          {/* cerebellum + brainstem */}
          <path id="cerebellum" d="M648 452 C716 458 762 424 772 402 C762 430 772 448 760 456 C734 480 650 470 628 448 Z" fill="#0d182b" stroke="#1a2b4b" strokeWidth="1" />
          <path id="brainstem" d="M498 460 C496 500 508 536 500 560 L500 560 C492 536 480 500 484 460 Z" fill="#0f1b2d" stroke="#1d2e4a" strokeWidth="1" />

          {/* ===== ORGANIC ARTERIES = TRANSPORTS ===== */}
          <g fill="none" strokeLinecap="round">
            {/* HASF (MCA left branch) */}
            {aHasf.glow && (
              <path d="M360 238 C370 270 420 326 500 344" stroke={aHasf.color} strokeWidth={aHasf.width * 2} strokeOpacity="0.25" filter="url(#fglow)" />
            )}
            <path id="v-hasf" d="M360 238 C370 270 420 326 500 344" stroke={aHasf.color} strokeWidth={aHasf.width} strokeOpacity={aHasf.opacity} strokeDasharray={aHasf.dash} />

            {/* HSF (ACA top branch) */}
            {aHsf.glow && (
              <path d="M580 196 C560 220 520 280 500 344" stroke={aHsf.color} strokeWidth={aHsf.width * 2} strokeOpacity="0.25" filter="url(#fglow)" />
            )}
            <path id="v-hsf" d="M580 196 C560 220 520 280 500 344" stroke={aHsf.color} strokeWidth={aHsf.width} strokeOpacity={aHsf.opacity} strokeDasharray={aHsf.dash} />

            {/* HRF (temporal branch) */}
            {aHrf.glow && (
              <path d="M380 380 C400 380 440 380 500 344" stroke={aHrf.color} strokeWidth={aHrf.width * 2} strokeOpacity="0.25" filter="url(#fglow)" />
            )}
            <path id="v-hrf" d="M380 380 C400 380 440 380 500 344" stroke={aHrf.color} strokeWidth={aHrf.width} strokeOpacity={aHrf.opacity} strokeDasharray={aHrf.dash} />

            {/* HMF (PCA right branch) */}
            {aHmf.glow && (
              <path d="M720 270 C720 300 640 336 500 344" stroke={aHmf.color} strokeWidth={aHmf.width * 2} strokeOpacity="0.25" filter="url(#fglow)" />
            )}
            <path id="v-hmf" d="M720 270 C720 300 640 336 500 344" stroke={aHmf.color} strokeWidth={aHmf.width} strokeOpacity={aHmf.opacity} strokeDasharray={aHmf.dash} />

            {/* relay-001 (Basilar brainstem branch) */}
            {aRelay.glow && (
              <path d="M500 552 C502 508 498 470 500 436 C502 402 500 372 500 344" stroke={aRelay.color} strokeWidth={aRelay.width * 2} strokeOpacity="0.25" filter="url(#fglow)" />
            )}
            <path id="v-basilar" d="M500 552 C502 508 498 470 500 436 C502 402 500 372 500 344" stroke={aRelay.color} strokeWidth={aRelay.width} strokeOpacity={aRelay.opacity} strokeDasharray={aRelay.dash} />
          </g>

          {/* ===== BLOOD-FLOW PERFUSION PARTICLES ===== */}
          <g fill="#ffd2c2" filter="url(#fglow)">
            {aHasf.dur && (
              <circle r={hasf.isGo ? 3.0 : 2.0} opacity="0.9">
                <animateMotion dur={aHasf.dur} repeatCount="indefinite" path="M360 238 C370 270 420 326 500 344" />
              </circle>
            )}
            {aHsf.dur && (
              <circle r={hsf.isGo ? 3.0 : 2.0} opacity="0.9">
                <animateMotion dur={aHsf.dur} repeatCount="indefinite" path="M580 196 C560 220 520 280 500 344" />
              </circle>
            )}
            {aHrf.dur && (
              <circle r={hrf.isGo ? 3.0 : 2.0} opacity="0.9">
                <animateMotion dur={aHrf.dur} repeatCount="indefinite" path="M380 380 C400 380 440 380 500 344" />
              </circle>
            )}
            {aHmf.dur && (
              <circle r={hmf.isGo ? 3.0 : 2.0} opacity="0.9">
                <animateMotion dur={aHmf.dur} repeatCount="indefinite" path="M720 270 C720 300 640 336 500 344" />
              </circle>
            )}
            {aRelay.dur && (
              <circle r={relay.isGo ? 3.2 : 2.2} opacity="0.9">
                <animateMotion dur={aRelay.dur} repeatCount="indefinite" path="M500 552 C502 508 498 470 500 436 C502 402 500 372 500 344" />
              </circle>
            )}
          </g>

          {/* ===== SUBTLE CLOT MARKERS ===== */}
          {hasf.isBlocked && (
            <circle cx="430" cy="290" r="5.5" fill="#15080c" stroke="#8a2b34" strokeWidth="1.5" filter="url(#fglow)" className="animate-pulse" data-testid="clot-HASF" />
          )}
          {hsf.isBlocked && (
            <circle cx="540" cy="270" r="5.5" fill="#15080c" stroke="#8a2b34" strokeWidth="1.5" filter="url(#fglow)" className="animate-pulse" data-testid="clot-HSF" />
          )}
          {hrf.isBlocked && (
            <circle cx="440" cy="362" r="5.5" fill="#15080c" stroke="#8a2b34" strokeWidth="1.5" filter="url(#fglow)" className="animate-pulse" data-testid="clot-HRF" />
          )}
          {hmf.isBlocked && (
            <circle cx="610" cy="307" r="5.5" fill="#15080c" stroke="#8a2b34" strokeWidth="1.5" filter="url(#fglow)" className="animate-pulse" data-testid="clot-HMF" />
          )}
          {relay.isBlocked && (
            <circle cx="500" cy="448" r="5.5" fill="#15080c" stroke="#8a2b34" strokeWidth="1.5" filter="url(#fglow)" className="animate-pulse" data-testid="clot-relay" />
          )}

          {/* ===== LOBE TERMINATION CIRCLES (Verifies fill condition in test) ===== */}
          <circle cx="360" cy="238" r="4.5" fill={hasf.isGo ? "#ff9c7a" : "#1a1624"} stroke={hasf.isGo ? "#ff9c7a" : "#3a4766"} strokeWidth="1.2" data-testid="node-HASF"
                  onMouseEnter={() => setHoveredNode("HASF")} onMouseLeave={() => setHoveredNode(null)} className="cursor-pointer" />
          <circle cx="580" cy="196" r="4.5" fill={hsf.isGo ? "#ff9c7a" : "#1a1624"} stroke={hsf.isGo ? "#ff9c7a" : "#3a4766"} strokeWidth="1.2" data-testid="node-HSF"
                  onMouseEnter={() => setHoveredNode("HSF")} onMouseLeave={() => setHoveredNode(null)} className="cursor-pointer" />
          <circle cx="380" cy="380" r="4.5" fill={hrf.isGo ? "#ff9c7a" : "#1a1624"} stroke={hrf.isGo ? "#ff9c7a" : "#3a4766"} strokeWidth="1.2" data-testid="node-HRF"
                  onMouseEnter={() => setHoveredNode("HRF")} onMouseLeave={() => setHoveredNode(null)} className="cursor-pointer" />
          <circle cx="720" cy="270" r="4.5" fill={hmf.isGo ? "#ff9c7a" : "#1a1624"} stroke={hmf.isGo ? "#ff9c7a" : "#3a4766"} strokeWidth="1.2" data-testid="node-HMF"
                  onMouseEnter={() => setHoveredNode("HMF")} onMouseLeave={() => setHoveredNode(null)} className="cursor-pointer" />
          <circle cx="500" cy="530" r="4.5" fill={relay.isGo ? "#ff9c7a" : "#1a1624"} stroke={relay.isGo ? "#ff9c7a" : "#3a4766"} strokeWidth="1.2" data-testid="node-relay-001"
                  onMouseEnter={() => setHoveredNode("relay-001")} onMouseLeave={() => setHoveredNode(null)} className="cursor-pointer" />

          {/* ===== HAS THALAMIC CORE ===== */}
          <circle id="coreGlow" cx="500" cy="344" r="38" fill="url(#gcore)" opacity={isCoreFresh ? 0.35 : 0.1} className="transition-opacity duration-500 pointer-events-none" />
          <circle id="coreDot" cx="500" cy="344" r="10" fill={isCoreFresh ? "#102c38" : "#0d1421"} stroke={isCoreFresh ? "#38e6ff" : "#3a4766"} strokeWidth="1.5"
                  className="cursor-pointer" data-testid="node-HAS"
                  onMouseEnter={() => setHoveredNode("HAS")}
                  onMouseLeave={() => setHoveredNode(null)} />
          <text x="500" y="322" textAnchor="middle" fontSize="12" fontWeight="600" fill="#8ff6ff" pointerEvents="none">HAS</text>
          <text id="coreStatus" x="500" y="376" textAnchor="middle" fontSize="9" fill={isCoreFresh ? "#8ff6ff" : "#63719a"} pointerEvents="none">
            {isCoreFresh ? "FRESH" : "STALE"}
          </text>

          {/* ===== PREMIUM EXTERNAL LABELS & CONNECTOR LINES ===== */}
          {/* HASF (Frontal Lobe) */}
          <path d="M 210 180 L 320 180 L 350 220" stroke="#16233d" strokeWidth="0.8" fill="none" pointerEvents="none" />
          <circle cx="350" cy="220" r="2" fill="#ff9c7a" pointerEvents="none" />
          <g className="cursor-pointer text-[11px]" onMouseEnter={() => setHoveredNode("HASF")} onMouseLeave={() => setHoveredNode(null)}>
            <text x="200" y="176" textAnchor="end" fontWeight="600" fill="#dfe7f5">frontal lobe</text>
            <text x="200" y="190" textAnchor="end" fontSize="9" fill={hasf.isStale ? "#5a6480" : "#ff9c7a"}>HASF</text>
            {hasf.isStale && (
              <text x="165" y="190" textAnchor="end" fontSize="8" fontWeight="bold" fill="#ffb84d">STALE</text>
            )}
            {hasf.isBlocked && (
              <text x="165" y="190" textAnchor="end" fontSize="8" fontWeight="bold" fill="#ff5566">BLOCKED</text>
            )}
          </g>

          {/* HSF (Parietal Lobe) */}
          <path d="M 790 160 L 640 160 L 590 188" stroke="#16233d" strokeWidth="0.8" fill="none" pointerEvents="none" />
          <circle cx="590" cy="188" r="2" fill="#ff9c7a" pointerEvents="none" />
          <g className="cursor-pointer text-[11px]" onMouseEnter={() => setHoveredNode("HSF")} onMouseLeave={() => setHoveredNode(null)}>
            <text x="800" y="156" textAnchor="start" fontWeight="600" fill="#dfe7f5">parietal lobe</text>
            <text x="800" y="170" textAnchor="start" fontSize="9" fill={hsf.isStale ? "#5a6480" : "#ff9c7a"}>HSF</text>
            {hsf.isStale && (
              <text x="835" y="170" textAnchor="start" fontSize="8" fontWeight="bold" fill="#ffb84d">STALE</text>
            )}
          </g>

          {/* HRF (Temporal Lobe) */}
          <path d="M 210 420 L 330 420 L 370 390" stroke="#16233d" strokeWidth="0.8" fill="none" pointerEvents="none" />
          <circle cx="370" cy="390" r="2" fill="#ff9c7a" pointerEvents="none" />
          <g className="cursor-pointer text-[11px]" onMouseEnter={() => setHoveredNode("HRF")} onMouseLeave={() => setHoveredNode(null)}>
            <text x="200" y="416" textAnchor="end" fontWeight="600" fill="#dfe7f5">temporal lobe</text>
            <text x="200" y="430" textAnchor="end" fontSize="9" fill={hrf.isStale ? "#5a6480" : "#ff9c7a"}>HRF</text>
            {hrf.isStale && (
              <text x="165" y="430" textAnchor="end" fontSize="8" fontWeight="bold" fill="#ffb84d">STALE</text>
            )}
          </g>

          {/* HMF (Occipital Lobe) */}
          <path d="M 790 320 L 760 320 L 730 282" stroke="#16233d" strokeWidth="0.8" fill="none" pointerEvents="none" />
          <circle cx="730" cy="282" r="2" fill="#ff9c7a" pointerEvents="none" />
          <g className="cursor-pointer text-[11px]" onMouseEnter={() => setHoveredNode("HMF")} onMouseLeave={() => setHoveredNode(null)}>
            <text x="800" y="316" textAnchor="start" fontWeight="600" fill="#dfe7f5">occipital lobe</text>
            <text x="800" y="330" textAnchor="start" fontSize="9" fill={hmf.isStale ? "#5a6480" : "#ff9c7a"}>HMF</text>
            {hmf.isStale && (
              <text x="835" y="330" textAnchor="start" fontSize="8" fontWeight="bold" fill="#ffb84d">STALE</text>
            )}
            {hmf.isBlocked && (
              <text x="835" y="330" textAnchor="start" fontSize="8" fontWeight="bold" fill="#ff5566">BLOCKED</text>
            )}
          </g>

          {/* Brainstem label */}
          <text x="516" y="546" fontSize="9" fill="#63719a" pointerEvents="none">brainstem · relay-001</text>

          {/* ECG background axis & animating line */}
          <line x1="60" y1="524" x2="940" y2="524" stroke="#0d1424" strokeWidth="1" pointerEvents="none" />
          <polyline id="ecg" ref={ecgRef} fill="none" strokeWidth="1.8" opacity="0.9" filter="url(#fglow)" pointerEvents="none" />
        </svg>

        {/* Floating Tooltip Hover Card */}
        {hoveredNode && activeCardInfo && (
          <div
            className="absolute z-50 rounded-xl border border-[#22406e] bg-[#090f1c]/95 p-4 shadow-2xl backdrop-blur-md text-[11px] text-slate-300 w-[270px] pointer-events-none"
            style={{
              top: hoveredNode === "HASF" ? "10%" : hoveredNode === "HSF" ? "10%" : hoveredNode === "relay-001" ? "auto" : "32%",
              bottom: hoveredNode === "relay-001" ? "12%" : "auto",
              left: hoveredNode === "HASF" || hoveredNode === "HRF" ? "5%" : hoveredNode === "relay-001" || hoveredNode === "HAS" ? "50%" : "auto",
              right: hoveredNode === "HSF" || hoveredNode === "HMF" ? "5%" : "auto",
              transform: hoveredNode === "relay-001" || hoveredNode === "HAS" ? "translateX(-50%)" : "none"
            }}
          >
            <div className="flex items-center justify-between border-b border-slate-900 pb-2 mb-2">
              <strong className="text-white tracking-wider text-xs flex items-center gap-1">
                {hoveredNode.toUpperCase()} Node Info
              </strong>
              <span className={`px-2 py-0.5 rounded text-[8px] font-bold ${
                activeCardInfo.status === "CONVERGED" || activeCardInfo.status === "ONLINE"
                  ? "bg-green-950/40 text-green-400 border border-green-900/35"
                  : activeCardInfo.status === "STALE" || activeCardInfo.status === "UNKNOWN"
                  ? "bg-amber-950/40 text-amber-400 border border-amber-900/35"
                  : "bg-red-950/40 text-red-400 border border-red-900/35"
              }`}>
                {activeCardInfo.status}
              </span>
            </div>

            <div className="space-y-1.5 leading-normal">
              <div>
                <span className="text-slate-500 font-semibold mr-1">Owner:</span>
                <span className="text-slate-200">{activeCardInfo.owner}</span>
              </div>
              <div>
                <span className="text-slate-500 font-semibold mr-1">Last Update:</span>
                <span className="text-slate-200">{activeCardInfo.lastUpdateAge}</span>
              </div>
              <div>
                <span className="text-slate-500 font-semibold mr-1">Blocker:</span>
                <span className={activeCardInfo.blocker !== "None" ? "text-red-400" : "text-slate-400"}>
                  {activeCardInfo.blocker}
                </span>
              </div>
              <div className="pt-1.5 border-t border-slate-900">
                <span className="text-slate-500 font-semibold block mb-0.5">Evidence:</span>
                <span className="text-[10px] text-[#38e6ff] break-all block bg-slate-950/60 p-1 rounded border border-slate-950">
                  {activeCardInfo.evidence}
                </span>
              </div>
              <div className="pt-1.5">
                <span className="text-slate-500 font-semibold block mb-0.5">Next Safe Action:</span>
                <span className="text-[10px] text-green-400 break-words block bg-slate-950/60 p-1 rounded border border-slate-950">
                  {activeCardInfo.nextAction}
                </span>
              </div>
            </div>
          </div>
        )}

        {/* HAS Thalamic Core Overlay Info */}
        {hoveredNode === "HAS" && (
          <div
            className="absolute z-50 rounded-xl border border-[#22406e] bg-[#090f1c]/95 p-4 shadow-2xl backdrop-blur-md text-[11px] text-slate-300 w-[270px]"
            style={{ top: "18%", left: "50%", transform: "translateX(-50%)" }}
          >
            <div className="flex items-center justify-between border-b border-slate-900 pb-2 mb-2">
              <strong className="text-white tracking-wider text-xs flex items-center gap-1">
                HAS THALAMIC CORE
              </strong>
              <span className={`px-2 py-0.5 rounded text-[8px] font-bold ${
                isCoreFresh ? "bg-cyan-950/40 text-[#38e6ff] border border-cyan-900/35" : "bg-red-950/40 text-red-400 border border-red-900/35"
              }`}>
                {isCoreFresh ? "FRESH" : "STALE"}
              </span>
            </div>
            <div className="space-y-1.5 leading-normal">
              <div>
                <span className="text-slate-500 font-semibold mr-1">Verdict:</span>
                <span className={`font-bold ${data.mission_commander?.verdict === "GO" ? "text-green-400" : "text-red-400"}`}>
                  {data.mission_commander?.verdict ?? "UNKNOWN"}
                </span>
              </div>
              <div>
                <span className="text-slate-500 font-semibold mr-1">Cycles:</span>
                <span className="text-slate-200">{data.ledger_proof?.current_cycle_count ?? 0}</span>
              </div>
              <div>
                <span className="text-slate-500 font-semibold mr-1">Reason:</span>
                <span className="text-slate-400 block mt-0.5 text-[10px] leading-relaxed">{data.mission_commander?.verdict_reason ?? "None"}</span>
              </div>
              <div className="pt-1.5 border-t border-slate-900">
                <span className="text-slate-500 font-semibold block mb-0.5">Prohibited:</span>
                <span className="text-[10px] text-red-400 flex flex-wrap gap-1 mt-0.5">
                  {data.policy_explainer?.prohibited_actions?.map((act: string) => (
                    <span key={act} className="bg-red-950/30 border border-red-900/20 px-1 rounded">{act}</span>
                  )) || "None"}
                </span>
              </div>
            </div>
          </div>
        )}
      </div>

      <style>{`
        #brainbody {
          transform-origin: 500px 280px;
          animation: breathe 7s ease-in-out infinite;
        }
        @keyframes breathe {
          0%, 100% { transform: scale(1); }
          50% { transform: scale(1.008); }
        }
      `}</style>
    </div>
  );
};
