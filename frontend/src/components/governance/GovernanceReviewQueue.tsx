import { useGovernanceRegistryStore } from "../../lib/governance/aiSystemRegistry";
import { Check, X, Users } from "lucide-react";

export function GovernanceReviewQueue() {
  const { systems, approveReview, rejectReview } = useGovernanceRegistryStore();

  const underReviewSystems = systems.filter((s) => s.status === "under_review");
  const completedReviews = systems.filter((s) => s.status === "approved" || s.status === "restricted");

  return (
    <div className="rounded-lg border border-slate-800 bg-slate-950/60 p-4 backdrop-blur-md">
      <div className="mb-4 flex items-center gap-2">
        <Users className="h-4 w-4 text-cyan-400" />
        <h3 className="font-mono text-sm font-semibold tracking-wider text-slate-200">
          GOVERNANCE REVIEW & APPROVAL QUEUE
        </h3>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Under Review list */}
        <div className="rounded border border-slate-900 bg-slate-950/40 p-3 font-mono text-xs">
          <span className="font-bold text-slate-200 block mb-3">PENDING EVALUATION ({underReviewSystems.length})</span>
          <div className="space-y-3 max-h-[220px] overflow-y-auto pr-1">
            {underReviewSystems.length > 0 ? (
              underReviewSystems.map((sys) => (
                <div
                  key={sys.system_id}
                  className="rounded border border-yellow-500/20 bg-yellow-500/5 p-3 hover:border-yellow-500/30 transition-colors"
                >
                  <div className="flex items-start justify-between mb-1.5">
                    <div>
                      <span className="font-bold text-slate-200">{sys.name}</span>
                      <span className="ml-1.5 text-[10px] text-slate-500">({sys.type})</span>
                    </div>
                    <span className="rounded bg-yellow-500/10 px-1.5 py-0.5 text-[9px] font-semibold text-yellow-400 uppercase">
                      {sys.risk_tier} RISK
                    </span>
                  </div>
                  <p className="text-[10px] text-slate-400 leading-normal mb-3">{sys.description}</p>
                  <div className="flex justify-end gap-2">
                    <button
                      onClick={() => rejectReview(sys.system_id, "Michael Hoch")}
                      className="flex items-center gap-1 rounded bg-red-500/10 hover:bg-red-500/20 border border-red-500/30 px-2 py-0.5 text-[10px] font-semibold text-red-400 transition-colors"
                    >
                      <X className="h-3 w-3" /> RESTRICT
                    </button>
                    <button
                      onClick={() => approveReview(sys.system_id, "Michael Hoch")}
                      className="flex items-center gap-1 rounded bg-green-500/10 hover:bg-green-500/20 border border-green-500/30 px-2 py-0.5 text-[10px] font-semibold text-green-400 transition-colors"
                    >
                      <Check className="h-3 w-3" /> APPROVE
                    </button>
                  </div>
                </div>
              ))
            ) : (
              <div className="text-slate-600 italic text-[11px] py-6 text-center">
                All registered capabilities are currently reviewed and triaged.
              </div>
            )}
          </div>
        </div>

        {/* History list */}
        <div className="rounded border border-slate-900 bg-slate-950/40 p-3 font-mono text-xs">
          <span className="font-bold text-slate-200 block mb-3">REVIEW AUDIT LOG</span>
          <div className="space-y-2 max-h-[220px] overflow-y-auto pr-1">
            {completedReviews.length > 0 ? (
              completedReviews.map((sys) => (
                <div key={sys.system_id} className="flex items-start justify-between text-[10px] bg-slate-950/60 p-2 rounded border border-slate-900/50 hover:border-slate-800">
                  <div className="space-y-0.5">
                    <span className="font-semibold text-slate-300">{sys.name}</span>
                    <div className="text-slate-500 text-[9px]">
                      Reviewed by {sys.review.reviewed_by || "System"} on {sys.review.reviewed_at ? sys.review.reviewed_at.split("T")[0] : "N/A"}
                    </div>
                  </div>
                  <span className={`status-badge ${sys.status === 'approved' ? 'success' : 'fail'}`}>
                    {sys.status}
                  </span>
                </div>
              ))
            ) : (
              <div className="text-slate-600 italic text-[11px] py-6 text-center">
                No logs recorded yet.
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
