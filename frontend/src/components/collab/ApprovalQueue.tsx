import { useState } from "react";
import { useApprovalStore } from "@/lib/collab/approvalStore";
import { ApprovalRequestCard } from "./ApprovalRequestCard";
import { ClipboardList, Inbox, CheckCircle, XCircle } from "lucide-react";

export function ApprovalQueue() {
  const { requests } = useApprovalStore();
  const [activeTab, setActiveTab] = useState<"pending" | "approved" | "rejected" | "all">("pending");

  const filteredRequests = requests.filter((r) => {
    if (activeTab === "pending") return r.status === "pending" || r.status === "escalated";
    if (activeTab === "approved") return r.status === "approved";
    if (activeTab === "rejected") return r.status === "rejected" || r.status === "changes_requested";
    return true; // "all"
  });

  const counts = {
    pending: requests.filter((r) => r.status === "pending" || r.status === "escalated").length,
    approved: requests.filter((r) => r.status === "approved").length,
    rejected: requests.filter((r) => r.status === "rejected" || r.status === "changes_requested").length,
    all: requests.length
  };

  return (
    <div className="rounded-lg border border-slate-800 bg-slate-950/60 p-4 backdrop-blur-md">
      <div className="mb-4 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <ClipboardList className="h-4 w-4 text-cyan-400" />
          <h3 className="font-mono text-sm font-semibold tracking-wider text-slate-200">
            SWARM APPROVAL QUEUE
          </h3>
        </div>
      </div>

      {/* Tabs */}
      <div className="mb-4 flex border-b border-slate-900">
        <button
          onClick={() => setActiveTab("pending")}
          className={`flex items-center gap-1.5 border-b-2 px-3 py-2 text-xs font-mono tracking-wider transition-all ${
            activeTab === "pending"
              ? "border-cyan-500 text-cyan-400 font-semibold"
              : "border-transparent text-slate-500 hover:text-slate-300"
          }`}
        >
          <Inbox className="h-3.5 w-3.5" />
          PENDING ({counts.pending})
        </button>
        <button
          onClick={() => setActiveTab("approved")}
          className={`flex items-center gap-1.5 border-b-2 px-3 py-2 text-xs font-mono tracking-wider transition-all ${
            activeTab === "approved"
              ? "border-cyan-500 text-cyan-400 font-semibold"
              : "border-transparent text-slate-500 hover:text-slate-300"
          }`}
        >
          <CheckCircle className="h-3.5 w-3.5" />
          APPROVED ({counts.approved})
        </button>
        <button
          onClick={() => setActiveTab("rejected")}
          className={`flex items-center gap-1.5 border-b-2 px-3 py-2 text-xs font-mono tracking-wider transition-all ${
            activeTab === "rejected"
              ? "border-cyan-500 text-cyan-400 font-semibold"
              : "border-transparent text-slate-500 hover:text-slate-300"
          }`}
        >
          <XCircle className="h-3.5 w-3.5" />
          REJECTED ({counts.rejected})
        </button>
        <button
          onClick={() => setActiveTab("all")}
          className={`flex items-center border-b-2 px-3 py-2 text-xs font-mono tracking-wider transition-all ${
            activeTab === "all"
              ? "border-cyan-500 text-cyan-400 font-semibold"
              : "border-transparent text-slate-500 hover:text-slate-300"
          }`}
        >
          ALL ({counts.all})
        </button>
      </div>

      {/* Request list */}
      <div className="space-y-3 max-h-[500px] overflow-y-auto pr-1">
        {filteredRequests.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-8 text-center border border-slate-900/50 rounded-md bg-slate-950/20">
            <ClipboardList className="h-8 w-8 text-slate-700 mb-2" />
            <p className="text-xs font-mono text-slate-500">
              No authorization requests in this category.
            </p>
          </div>
        ) : (
          filteredRequests.map((request) => (
            <ApprovalRequestCard key={request.approval_id} request={request} />
          ))
        )}
      </div>
    </div>
  );
}
