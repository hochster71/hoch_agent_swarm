import React from "react";
import { BookOpen, HelpCircle } from "lucide-react";

export const SupportPlaybookPanel: React.FC = () => {
  const documents = [
    { title: "User Guide", version: "v1.0" },
    { title: "API Reference", version: "v1.0" },
    { title: "Integration Guide", version: "v1.0" },
    { title: "Runbook", version: "v1.0" },
    { title: "Support Playbooks", version: "v1.0" }
  ];

  return (
    <div className="glass-panel p-4 rounded-xl border border-white/10 bg-white/2 space-y-4 text-left">
      <div>
        <h4 className="text-xs font-bold text-slate-300 uppercase tracking-wider">Documentation & Support</h4>
      </div>

      <div className="space-y-1.5 text-xs">
        {documents.map((doc, idx) => (
          <div key={idx} className="flex items-center justify-between p-2 rounded bg-white/5 border border-white/5 hover:bg-white/10 transition cursor-pointer">
            <span className="flex items-center gap-1.5 text-slate-200">
              <BookOpen className="w-3.5 h-3.5 text-blue-400" />
              {doc.title}
            </span>
            <span className="text-[10px] px-1.5 py-0.5 rounded bg-white/10 text-slate-300 font-semibold">{doc.version}</span>
          </div>
        ))}
      </div>

      <div className="text-[10px] text-slate-400 text-center flex items-center justify-center gap-1 pt-1 border-t border-white/5">
        <HelpCircle className="w-3 h-3 text-slate-400" />
        Support Contact: <span className="text-blue-400 hover:underline">hochster-support@org.com</span>
      </div>
    </div>
  );
};
