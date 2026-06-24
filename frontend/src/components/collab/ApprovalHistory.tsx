import { useApprovalStore } from "@/lib/collab/approvalStore";
import { History, ShieldCheck, XCircle, Clock } from "lucide-react";

export function ApprovalHistory() {
  const { requests } = useApprovalStore();
  const historicalRequests = requests.filter((r) => r.status !== "pending" && r.status !== "escalated");

  const getStatusIcon = (status: string) => {
    switch (status) {
      case "approved":
        return <ShieldCheck className="h-4 w-4 text-emerald-400" />;
      case "rejected":
        return <XCircle className="h-4 w-4 text-rose-500" />;
      default:
        return <Clock className="h-4 w-4 text-slate-500" />;
    }
  };

  const getStatusTextClass = (status: string) => {
    switch (status) {
      case "approved":
        return "text-emerald-400";
      case "rejected":
        return "text-rose-500";
      default:
        return "text-slate-400";
    }
  };

  return (
    <div className="rounded-lg border border-slate-800 bg-slate-950/60 p-4 backdrop-blur-md">
      <div className="mb-4 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <History className="h-4 w-4 text-cyan-400" />
          <h3 className="font-mono text-sm font-semibold tracking-wider text-slate-200">
            SIGN-OFF HISTORY LEDGER
          </h3>
        </div>
        <span className="font-mono text-xs text-slate-500">
          Decided Requests: {historicalRequests.length}
        </span>
      </div>

      <div className="space-y-3 max-h-[300px] overflow-y-auto pr-1">
        {historicalRequests.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-6 text-center border border-slate-900/50 rounded-md bg-slate-950/20">
            <p className="text-xs font-mono text-slate-500">
              No historical decisions recorded.
            </p>
          </div>
        ) : (
          historicalRequests.map((req) => (
            <div
              key={req.approval_id}
              className="rounded border border-slate-900 bg-slate-950/30 p-2.5 hover:border-slate-800 transition-colors"
            >
              <div className="flex items-center justify-between border-b border-slate-900 pb-1.5 mb-1.5 font-mono text-[11px]">
                <span className="text-slate-400 font-bold">{req.approval_id}</span>
                <div className="flex items-center gap-1.5">
                  {getStatusIcon(req.status)}
                  <span className={`uppercase font-semibold ${getStatusTextClass(req.status)}`}>
                    {req.status}
                  </span>
                </div>
              </div>

              <div className="font-mono text-xs space-y-1">
                <div className="text-slate-300 break-all bg-slate-950/50 p-1.5 rounded border border-slate-900">
                  {req.command.raw_text}
                </div>
                <div className="mt-2 text-[10px] text-slate-500 flex justify-between">
                  <span>Target: {req.target.name}</span>
                  <span>Risk: {req.command.risk.toUpperCase()}</span>
                </div>

                {req.decisions.length > 0 && (
                  <div className="mt-1.5 border-t border-slate-900/50 pt-1.5 text-[10px] text-slate-400">
                    <span className="font-bold text-slate-500">Signed By:</span>{" "}
                    {req.decisions[0].decided_by.name} ({req.decisions[0].decided_by.role})
                    <p className="mt-0.5 italic text-slate-500">"{req.decisions[0].note}"</p>
                  </div>
                )}
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
