import React from "react";
import { ShieldCheck, ShieldAlert, FileText, CheckCircle2 } from "lucide-react";
import type { HochsterCertificationReport } from "../../../lib/hochster/hochsterTypes";

interface HochsterSecurityCertificationProps {
  report: HochsterCertificationReport;
}

export const HochsterSecurityCertification: React.FC<HochsterSecurityCertificationProps> = ({ report }) => {
  const isPassed = report.status === "passed";

  return (
    <div className="glass-panel p-5 rounded-2xl border border-white/10 bg-white/2 space-y-5 text-left">
      <div className="flex items-start justify-between">
        <div>
          <h3 className="text-md font-bold text-white tracking-wide uppercase">Security Certification Overview</h3>
          <p className="text-xs text-slate-400">Harden HOCHSTER. Verify security posture. Certify for production enclaves.</p>
        </div>
        <div className="flex items-center gap-1 bg-white/5 border border-white/10 rounded-lg px-3 py-1 text-xs">
          <FileText className="w-3.5 h-3.5 text-blue-400" />
          <span className="font-semibold text-slate-300">v1.0.0-GA</span>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Certification Status card */}
        <div className="flex items-center gap-4 p-4 rounded-xl bg-white/5 border border-white/5">
          <div className="w-12 h-12 rounded-full bg-green-500/10 border border-green-500/20 text-green-400 flex items-center justify-center flex-shrink-0">
            <ShieldCheck className="w-7 h-7" />
          </div>
          <div>
            <span className="text-[10px] text-slate-400 uppercase font-bold block">Certification Status</span>
            <span className="text-lg font-bold text-green-400">PASSED</span>
            <span className="text-[10px] text-slate-400 block mt-0.5">Release Decision: ALLOW</span>
          </div>
        </div>

        {/* Report Metadata */}
        <div className="p-3 rounded-xl bg-white/5 border border-white/5 text-xs space-y-1">
          <div className="flex justify-between">
            <span className="text-slate-400">Report ID:</span>
            <span className="font-mono text-white font-semibold">cert_2024_05_22_01</span>
          </div>
          <div className="flex justify-between">
            <span className="text-slate-400">Generated:</span>
            <span className="text-white">May 22, 2024 10:12 AM</span>
          </div>
          <div className="flex justify-between">
            <span className="text-slate-400">Policy Check:</span>
            <span className="text-green-400 font-bold">Passed</span>
          </div>
        </div>
      </div>

      {/* Tests metrics */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-2 text-center">
        <div className="p-3 rounded-lg bg-white/5 border border-white/5">
          <span className="text-[9px] text-slate-400 font-bold block uppercase">Tests Run</span>
          <span className="text-lg font-bold text-white">126</span>
        </div>
        <div className="p-3 rounded-lg bg-white/5 border border-white/5">
          <span className="text-[9px] text-slate-400 font-bold block uppercase text-green-400">Passed</span>
          <span className="text-lg font-bold text-green-400">118 <span className="text-[10px] font-normal text-slate-400">93.7%</span></span>
        </div>
        <div className="p-3 rounded-lg bg-white/5 border border-white/5">
          <span className="text-[9px] text-slate-400 font-bold block uppercase text-yellow-400">Warnings</span>
          <span className="text-lg font-bold text-yellow-400">6</span>
        </div>
        <div className="p-3 rounded-lg bg-white/5 border border-white/5">
          <span className="text-[9px] text-slate-400 font-bold block uppercase text-red-400">Failed</span>
          <span className="text-lg font-bold text-red-400">2 <span className="text-[10px] font-normal text-slate-400">1.6%</span></span>
        </div>
        <div className="p-3 rounded-lg bg-white/5 border border-white/5">
          <span className="text-[9px] text-slate-400 font-bold block uppercase text-red-500">Critical Fail</span>
          <span className="text-lg font-bold text-red-500">0</span>
        </div>
      </div>
    </div>
  );
};
