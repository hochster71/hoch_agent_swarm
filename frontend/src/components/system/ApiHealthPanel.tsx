import { useState, useEffect } from "react";
import { Activity, Heart } from "lucide-react";

export function ApiHealthPanel() {
  const [latency, setLatency] = useState<number>(12);
  const [ttfb, setTtfb] = useState<number>(45);
  const wsStatus = "connected";
  const [history, setHistory] = useState<number[]>([15, 12, 18, 14, 11, 15, 12]);

  useEffect(() => {
    const timer = setInterval(() => {
      // Simulate real-time API latency measurements
      const newLatency = Math.round(10 + Math.random() * 8);
      const newTtfb = Math.round(35 + Math.random() * 20);
      setLatency(newLatency);
      setTtfb(newTtfb);
      setHistory((prev) => [...prev.slice(1), newLatency]);
    }, 5000);

    return () => clearInterval(timer);
  }, []);

  return (
    <div className="rounded-lg border border-slate-800 bg-slate-950/60 p-4 backdrop-blur-md">
      <div className="mb-4 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Activity className="h-4 w-4 text-cyan-400" />
          <h3 className="font-mono text-sm font-semibold tracking-wider text-slate-200">
            SWARM CONSOLE CONNECTIVITY HEALTH
          </h3>
        </div>
        <span className="flex items-center gap-1 font-mono text-xs text-emerald-400">
          <Heart className="h-3 w-3 fill-emerald-400" />
          ACTIVE
        </span>
      </div>

      <div className="grid grid-cols-3 gap-2 font-mono text-[11px] mb-4">
        <div className="rounded border border-slate-900 bg-slate-950/40 p-2 text-center">
          <span className="text-slate-500 block mb-0.5">API LATENCY</span>
          <span className="text-sm font-bold text-slate-200">{latency} ms</span>
        </div>
        <div className="rounded border border-slate-900 bg-slate-950/40 p-2 text-center">
          <span className="text-slate-500 block mb-0.5">DB TTFB</span>
          <span className="text-sm font-bold text-slate-200">{ttfb} ms</span>
        </div>
        <div className="rounded border border-slate-900 bg-slate-950/40 p-2 text-center">
          <span className="text-slate-500 block mb-0.5">WS STREAM</span>
          <span className="text-sm font-bold text-emerald-400 uppercase">{wsStatus}</span>
        </div>
      </div>

      {/* Mini graphical display */}
      <div className="border border-slate-900 bg-slate-950/20 rounded p-2.5">
        <span className="font-mono text-[10px] text-slate-500 uppercase tracking-widest block mb-2">
          Ping History (5s Intervals)
        </span>
        <div className="flex h-10 items-end gap-1.5 pt-2">
          {history.map((val, idx) => {
            const pct = Math.min(100, (val / 30) * 100);
            return (
              <div
                key={idx}
                style={{ height: `${pct}%` }}
                className="w-full bg-cyan-500/20 hover:bg-cyan-400/40 border border-cyan-500/30 rounded-t-sm transition-all duration-300"
                title={`${val} ms`}
              />
            );
          })}
        </div>
      </div>
    </div>
  );
}
