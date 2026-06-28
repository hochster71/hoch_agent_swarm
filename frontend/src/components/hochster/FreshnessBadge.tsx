import React from "react";

type FreshnessBadgeProps = {
  freshness: "live" | "stale" | "expired" | "error";
  source: string;
  receivedAt: string;
};

export const FreshnessBadge: React.FC<FreshnessBadgeProps> = (props) => {
  const getBadgeStyle = (f: typeof props.freshness) => {
    switch (f) {
      case "live":
        return "bg-green-500/10 text-green-400 border border-green-500/20";
      case "stale":
        return "bg-yellow-500/10 text-yellow-400 border border-yellow-500/20 animate-pulse";
      case "expired":
        return "bg-red-500/10 text-red-400 border border-red-500/20";
      case "error":
        return "bg-red-600/20 text-red-500 border border-red-600/30";
      default:
        return "bg-slate-500/10 text-slate-400 border border-slate-500/20";
    }
  };

  return (
    <span
      data-freshness={props.freshness}
      className={`px-2 py-0.5 rounded text-[8px] font-mono font-bold uppercase tracking-wider select-none ${getBadgeStyle(props.freshness)}`}
      title={`Received: ${new Date(props.receivedAt).toLocaleTimeString()}`}
    >
      {props.freshness.toUpperCase()} · {props.source}
    </span>
  );
};
