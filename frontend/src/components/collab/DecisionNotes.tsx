import type { ApprovalRequest } from "@/lib/collab/collaborationTypes";
import { ShieldCheck, Lock } from "lucide-react";

type Props = {
  request: ApprovalRequest;
};

export function DecisionNotes({ request }: Props) {
  if (request.decisions.length === 0) {
    return (
      <div className="rounded-md border border-slate-900 bg-slate-950/20 p-3 text-center">
        <span className="font-mono text-xs text-slate-500">No cryptographic signature blocks found.</span>
      </div>
    );
  }

  return (
    <div className="space-y-3 font-mono text-xs">
      {request.decisions.map((dec) => {
        // Generate a mock SHA-256 block signature for visual depth
        const dummyHash = `SHA256:${dec.decision_id.repeat(4).substring(0, 16)}...${dec.decided_by.id.substring(0, 4)}`;

        return (
          <div
            key={dec.decision_id}
            className="rounded border border-emerald-950/20 bg-emerald-950/5 p-3"
          >
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-1.5 text-emerald-400">
                <ShieldCheck className="h-4 w-4" />
                <span className="font-bold">SIGNATURE SEALED</span>
              </div>
              <span className="text-[10px] text-slate-500">{new Date(dec.decided_at).toLocaleString()}</span>
            </div>

            <div className="space-y-1.5 border-t border-slate-900/60 pt-2 text-[11px]">
              <div>
                <span className="text-slate-500">Signer:</span>{" "}
                <span className="text-slate-300">{dec.decided_by.name}</span>{" "}
                <span className="text-slate-500">({dec.decided_by.role.toUpperCase()})</span>
              </div>
              <div>
                <span className="text-slate-500">Decision:</span>{" "}
                <span className={`font-semibold uppercase ${
                  dec.decision === "approve"
                    ? "text-emerald-400"
                    : dec.decision === "reject"
                    ? "text-rose-400"
                    : "text-amber-400"
                }`}>
                  {dec.decision}
                </span>
              </div>
              <div className="flex items-start gap-1">
                <span className="text-slate-500 shrink-0">Audit Note:</span>
                <span className="text-slate-400 italic">"{dec.note}"</span>
              </div>
              <div className="mt-2 flex items-center gap-1.5 rounded bg-slate-950/80 px-2 py-1 text-[9px] text-slate-400 border border-slate-900">
                <Lock className="h-3 w-3 text-cyan-400" />
                <span>{dummyHash}</span>
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}
