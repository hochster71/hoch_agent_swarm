import React, { useState, useEffect } from "react";
import { RealtimeUiDatum } from "../../lib/realtime/realtimeTypes";
import { evaluateFreshness } from "../../lib/realtime/freshness";
import { FreshnessBadge } from "./FreshnessBadge";
import { RefreshCw, Shield, Clock, HelpCircle, Link2 } from "lucide-react";

interface RealtimeWrapperProps {
  datum: RealtimeUiDatum<any>;
  title?: string;
  children: React.ReactNode;
  onRefresh?: () => void;
}

export const RealtimeWrapper: React.FC<RealtimeWrapperProps> = ({
  datum: initialDatum,
  title,
  children,
  onRefresh
}) => {
  const [datum, setDatum] = useState<RealtimeUiDatum<any>>(initialDatum);

  // Sync state when props change
  useEffect(() => {
    setDatum(initialDatum);
  }, [initialDatum]);

  // Tick timer to check freshness every 1 second
  useEffect(() => {
    const timer = setInterval(() => {
      setDatum((prev) => {
        const fresh = evaluateFreshness({
          received_at: prev.received_at,
          ttl_ms: prev.ttl_ms,
          source: prev.source,
          error: prev.freshness === "error"
        });
        return {
          ...prev,
          freshness: fresh
        };
      });
    }, 1000);
    return () => clearInterval(timer);
  }, []);

  return (
    <div className="relative rounded-2xl border border-white/10 bg-slate-900/40 backdrop-blur-md overflow-hidden transition-all duration-300 hover:border-white/15">
      {/* Top telemetry bar */}
      <div className="flex items-center justify-between px-4 py-2 border-b border-white/5 bg-black/10 text-[9px] font-mono select-none">
        <div className="flex items-center gap-1.5">
          <span className="w-1.5 h-1.5 rounded-full bg-blue-400"></span>
          <span className="text-slate-400 uppercase tracking-wider">{datum.source_id}</span>
        </div>
        <div className="flex items-center gap-2">
          <FreshnessBadge
            freshness={datum.freshness}
            source={datum.source}
            receivedAt={datum.received_at}
          />
        </div>
      </div>

      {/* Main Panel Content */}
      <div className="p-4">
        {children}
      </div>

      {/* Bottom audit telemetry strip */}
      <div className="flex items-center justify-between px-4 py-1.5 border-t border-white/5 bg-black/5 text-[8px] font-mono text-slate-400">
        <div className="flex items-center gap-3">
          <span className="flex items-center gap-0.5">
            <Clock className="w-2.5 h-2.5" />
            Last Updated: {new Date(datum.observed_at).toLocaleTimeString()}
          </span>
          {datum.correlation_id && (
            <span className="flex items-center gap-0.5 text-blue-400">
              <Shield className="w-2.5 h-2.5" />
              Tx: {datum.correlation_id}
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          <span className="text-slate-500">TTL: {(datum.ttl_ms / 1000).toFixed(0)}s</span>
          {datum.evidence_refs.length > 0 && (
            <span className="flex items-center gap-0.5 text-green-400" title="Evidence Linked">
              <Link2 className="w-2.5 h-2.5" />
              Ev: {datum.evidence_refs.length}
            </span>
          )}
          {onRefresh && (
            <button
              onClick={onRefresh}
              className="p-0.5 rounded hover:bg-white/5 hover:text-white transition"
              title="Refresh telemetry"
            >
              <RefreshCw className="w-2.5 h-2.5" />
            </button>
          )}
        </div>
      </div>
    </div>
  );
};
