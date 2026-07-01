import React, { useState } from "react";
import { Terminal, Send, AlertTriangle, ShieldCheck } from "lucide-react";
import { HochsterTool, HochsterProblemType } from "../../lib/hochster/hochsterTypes";

interface Props {
  onSubmit: (data: {
    problem: string;
    type: HochsterProblemType;
    severity: "low" | "medium" | "high" | "critical";
    repository: string;
    branch: string;
    files: string[];
    allowed_tools: HochsterTool[];
    max_instances: number;
    requires_approval: boolean;
  }) => void;
  isSubmitting: boolean;
}

export const HochsterRequestPanel: React.FC<Props> = ({ onSubmit, isSubmitting }) => {
  const [problem, setProblem] = useState("NullReferenceException in UserService.cs");
  const [type, setType] = useState<HochsterProblemType>("runtime_exception");
  const [severity, setSeverity] = useState<"low" | "medium" | "high" | "critical">("high");
  const [repository, setRepository] = useState("hoch-agent-swarm");
  const [branch, setBranch] = useState("feature/control-plane");
  const [files, setFiles] = useState("src/services/UserService.cs");
  const [maxInstances, setMaxInstances] = useState(3);
  const [requiresApproval, setRequiresApproval] = useState(true);

  const [allowedTools, setAllowedTools] = useState<HochsterTool[]>([
    "filesystem",
    "shell",
    "docker",
    "tests",
    "diff_patch"
  ]);

  const handleToggleTool = (tool: HochsterTool) => {
    setAllowedTools(prev =>
      prev.includes(tool) ? prev.filter(t => t !== tool) : [...prev, tool]
    );
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSubmit({
      problem,
      type,
      severity,
      repository,
      branch,
      files: files.split(",").map(f => f.trim()),
      allowed_tools: allowedTools,
      max_instances: maxInstances,
      requires_approval: requiresApproval
    });
  };

  const allAvailableTools: HochsterTool[] = [
    "filesystem",
    "shell",
    "docker",
    "kubernetes",
    "database",
    "web",
    "mcp",
    "tests",
    "security",
    "observability",
    "diff_patch"
  ];

  return (
    <div className="glass-panel p-5 rounded-xl border border-white/10 bg-white/2 space-y-4">
      <h3 className="text-lg font-bold flex items-center gap-2">
        <Terminal className="w-5 h-5 text-blue-400" /> Swarm Integration API Emulator
      </h3>

      <form onSubmit={handleSubmit} className="space-y-4">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="md:col-span-2">
            <label className="block text-xs text-slate-400 font-bold mb-1">Problem Statement</label>
            <input
              type="text"
              required
              value={problem}
              onChange={e => setProblem(e.target.value)}
              className="w-full bg-white/5 border border-white/10 rounded px-3 py-2 text-sm text-white focus:outline-none focus:border-blue-500"
            />
          </div>

          <div>
            <label className="block text-xs text-slate-400 font-bold mb-1">Problem Classification</label>
            <select
              value={type}
              onChange={e => setType(e.target.value as HochsterProblemType)}
              className="w-full bg-white/5 border border-white/10 rounded px-3 py-2 text-sm text-white focus:outline-none focus:border-blue-500"
            >
              <option value="code_bug">Code Bug</option>
              <option value="build_failure">Build Failure</option>
              <option value="test_failure">Test Failure</option>
              <option value="container_failure">Container Failure</option>
              <option value="runtime_exception">Runtime Exception</option>
              <option value="security_vulnerability">Security Vulnerability</option>
            </select>
          </div>

          <div>
            <label className="block text-xs text-slate-400 font-bold mb-1">Incident Severity</label>
            <select
              value={severity}
              onChange={e => setSeverity(e.target.value as any)}
              className="w-full bg-white/5 border border-white/10 rounded px-3 py-2 text-sm text-white focus:outline-none focus:border-blue-500"
            >
              <option value="low">Low</option>
              <option value="medium">Medium</option>
              <option value="high">High</option>
              <option value="critical">Critical</option>
            </select>
          </div>

          <div>
            <label className="block text-xs text-slate-400 font-bold mb-1">Repository Name</label>
            <input
              type="text"
              required
              value={repository}
              onChange={e => setRepository(e.target.value)}
              className="w-full bg-white/5 border border-white/10 rounded px-3 py-2 text-sm text-white focus:outline-none focus:border-blue-500"
            />
          </div>

          <div>
            <label className="block text-xs text-slate-400 font-bold mb-1">Branch Name</label>
            <input
              type="text"
              required
              value={branch}
              onChange={e => setBranch(e.target.value)}
              className="w-full bg-white/5 border border-white/10 rounded px-3 py-2 text-sm text-white focus:outline-none focus:border-blue-500"
            />
          </div>

          <div className="md:col-span-2">
            <label className="block text-xs text-slate-400 font-bold mb-1">Context Files (comma separated)</label>
            <input
              type="text"
              required
              value={files}
              onChange={e => setFiles(e.target.value)}
              className="w-full bg-white/5 border border-white/10 rounded px-3 py-2 text-sm text-white focus:outline-none focus:border-blue-500"
            />
          </div>
        </div>

        {/* Allowed tools checklist */}
        <div>
          <label className="block text-xs text-slate-400 font-bold mb-1.5">Allowed Tool Stack</label>
          <div className="flex flex-wrap gap-2">
            {allAvailableTools.map(tool => {
              const isAllowed = allowedTools.includes(tool);
              return (
                <button
                  type="button"
                  key={tool}
                  onClick={() => handleToggleTool(tool)}
                  className={`text-xs px-2.5 py-1 rounded transition border ${
                    isAllowed
                      ? "bg-blue-500/20 text-blue-400 border-blue-500/30"
                      : "bg-white/2 text-slate-400 border-white/5 hover:bg-white/5"
                  }`}
                >
                  {tool}
                </button>
              );
            })}
          </div>
        </div>

        {/* Max instances and constraints */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-xs text-slate-400 font-bold mb-1">Max Solver Instances</label>
            <input
              type="number"
              min="1"
              max="5"
              value={maxInstances}
              onChange={e => setMaxInstances(Number(e.target.value))}
              className="w-full bg-white/5 border border-white/10 rounded px-3 py-1.5 text-sm text-white focus:outline-none focus:border-blue-500"
            />
          </div>

          <div className="flex items-center gap-2 pt-5">
            <input
              type="checkbox"
              id="requires_approval"
              checked={requiresApproval}
              onChange={e => setRequiresApproval(e.target.checked)}
              className="rounded border-white/20 text-blue-500 focus:ring-0 cursor-pointer"
            />
            <label htmlFor="requires_approval" className="text-xs text-slate-300 font-semibold cursor-pointer">
              Requires Human Operator Confirmation Gate
            </label>
          </div>
        </div>

        <button
          type="submit"
          disabled={isSubmitting}
          className="w-full py-2.5 bg-blue-600 hover:bg-blue-500 disabled:bg-blue-800 transition rounded-lg text-sm font-semibold uppercase tracking-wider flex items-center justify-center gap-2 active:scale-95"
        >
          <Send className="w-4 h-4" />
          {isSubmitting ? "Orchestrator Routing solve..." : "Submit Solve Request"}
        </button>
      </form>
    </div>
  );
};
