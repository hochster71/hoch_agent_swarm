import { useChaosEngineStore } from "../../lib/adversarial/chaosEngine";
import { Zap, AlertTriangle } from "lucide-react";

export function ChaosDrillPanel() {
  const { injectedFaults, setFault } = useChaosEngineStore();

  const handleSliderChange = (key: "telemetryDelay" | "packetLoss" | "apiErrors" | "dbLatency", val: number) => {
    setFault(key, val);
  };

  const activeFaultsCount = Object.values(injectedFaults).filter(v => v > 0).length;

  return (
    <div className="rounded-lg border border-slate-800 bg-slate-950/60 p-4 backdrop-blur-md">
      <div className="mb-4 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Zap className="h-4 w-4 text-orange-500 animate-pulse" />
          <h3 className="font-mono text-sm font-semibold tracking-wider text-slate-200 uppercase">
            CHAOS & FAULT INJECTION CONTROLLER
          </h3>
        </div>
        {activeFaultsCount > 0 && (
          <span className="flex items-center gap-1 text-[10px] font-bold text-orange-500 font-mono bg-orange-500/10 border border-orange-500/30 px-2 py-0.5 rounded">
            <AlertTriangle className="h-3.5 w-3.5" /> {activeFaultsCount} ACTIVE FAULTS
          </span>
        )}
      </div>

      <div className="space-y-4 font-mono text-xs text-slate-300">
        {/* Telemetry Delay Slider */}
        <div className="rounded border border-slate-900 bg-slate-950/40 p-3">
          <div className="flex items-center justify-between mb-1.5">
            <span className="font-bold text-slate-300">TELEMETRY DELAY (LATENCY)</span>
            <span className="text-cyan-400 font-bold">{injectedFaults.telemetryDelay} ms</span>
          </div>
          <input
            type="range"
            min="0"
            max="5000"
            step="100"
            value={injectedFaults.telemetryDelay}
            onChange={(e) => handleSliderChange("telemetryDelay", parseInt(e.target.value))}
            className="w-full h-1 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-cyan-500"
          />
          <div className="flex justify-between text-[8px] text-slate-600 mt-1">
            <span>0 ms (Normal)</span>
            <span>2.5s (High)</span>
            <span>5.0s (Critical)</span>
          </div>
        </div>

        {/* Packet Loss Slider */}
        <div className="rounded border border-slate-900 bg-slate-950/40 p-3">
          <div className="flex items-center justify-between mb-1.5">
            <span className="font-bold text-slate-300">PACKET LOSS PROBABILITY</span>
            <span className="text-orange-400 font-bold">{injectedFaults.packetLoss}%</span>
          </div>
          <input
            type="range"
            min="0"
            max="100"
            step="5"
            value={injectedFaults.packetLoss}
            onChange={(e) => handleSliderChange("packetLoss", parseInt(e.target.value))}
            className="w-full h-1 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-orange-500"
          />
          <div className="flex justify-between text-[8px] text-slate-600 mt-1">
            <span>0% (Stable)</span>
            <span>50% (Degraded)</span>
            <span>100% (Disconnected)</span>
          </div>
        </div>

        {/* API Error rate Slider */}
        <div className="rounded border border-slate-900 bg-slate-950/40 p-3">
          <div className="flex items-center justify-between mb-1.5">
            <span className="font-bold text-slate-300">API ERROR SIMULATION RATE</span>
            <span className="text-red-400 font-bold">{injectedFaults.apiErrors}%</span>
          </div>
          <input
            type="range"
            min="0"
            max="100"
            step="5"
            value={injectedFaults.apiErrors}
            onChange={(e) => handleSliderChange("apiErrors", parseInt(e.target.value))}
            className="w-full h-1 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-red-500"
          />
          <div className="flex justify-between text-[8px] text-slate-600 mt-1">
            <span>0% (Clean)</span>
            <span>50% (Flaky)</span>
            <span>100% (Outage)</span>
          </div>
        </div>

        {/* DB Latency Slider */}
        <div className="rounded border border-slate-900 bg-slate-950/40 p-3">
          <div className="flex items-center justify-between mb-1.5">
            <span className="font-bold text-slate-300">DATABASE QUERY LATENCY</span>
            <span className="text-yellow-400 font-bold">{injectedFaults.dbLatency} ms</span>
          </div>
          <input
            type="range"
            min="0"
            max="1000"
            step="50"
            value={injectedFaults.dbLatency}
            onChange={(e) => handleSliderChange("dbLatency", parseInt(e.target.value))}
            className="w-full h-1 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-yellow-500"
          />
          <div className="flex justify-between text-[8px] text-slate-600 mt-1">
            <span>0 ms (Normal)</span>
            <span>500 ms (Lagging)</span>
            <span>1000 ms (Congested)</span>
          </div>
        </div>
      </div>
    </div>
  );
}
