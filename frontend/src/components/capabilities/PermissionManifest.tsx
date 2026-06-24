import { Shield, ShieldAlert, Key, Globe, FileCode, Mail, Calendar, Terminal } from "lucide-react";
import type { CapabilityRecord } from "../../lib/capabilities/capabilityTypes";
import { useCapabilityRegistryStore } from "../../lib/capabilities/capabilityRegistry";

type Props = {
  capability: CapabilityRecord;
};

export function PermissionManifest({ capability }: Props) {
  const { updatePermissions } = useCapabilityRegistryStore();

  const handleToggle = (key: keyof CapabilityRecord["permissions"]) => {
    const updated = {
      ...capability.permissions,
      [key]: !capability.permissions[key],
    };
    updatePermissions(capability.capability_id, updated);
  };

  const items = [
    { key: "filesystem" as const, label: "Filesystem Read/Write", icon: FileCode, desc: "Access to local directory storage." },
    { key: "network" as const, label: "Network Connectivity", icon: Globe, desc: "Outbound and inbound sockets." },
    { key: "email" as const, label: "Email Dispatcher", icon: Mail, desc: "Send reports via SMTP server." },
    { key: "calendar" as const, label: "Calendar Access", icon: Calendar, desc: "Inspect and schedule operations." },
    { key: "browser" as const, label: "Browser Automation", icon: Shield, desc: "Crawling and UI integrations." },
    { key: "shell" as const, label: "Shell Commands", icon: Terminal, desc: "Execute CLI shell scripts.", warning: true },
    { key: "secrets" as const, label: "Secrets Access", icon: Key, desc: "Decrypt API keys and credentials.", warning: true },
    { key: "external_write" as const, label: "External Write Access", icon: ShieldAlert, desc: "Write payloads to external databases.", warning: true },
  ];

  return (
    <div className="rounded-lg border border-slate-800 bg-slate-950/60 p-4 font-mono">
      <h3 className="text-xs font-bold tracking-wider text-slate-400 mb-3 uppercase flex items-center gap-2">
        <Shield className="h-4 w-4 text-cyan-400" />
        Permission Manifest Scope
      </h3>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-[11px]">
        {items.map((item) => {
          const Icon = item.icon;
          const active = capability.permissions[item.key];
          return (
            <div
              key={item.key}
              onClick={() => handleToggle(item.key)}
              className={`flex items-start justify-between p-3 rounded border cursor-pointer transition-all ${
                active
                  ? item.warning
                    ? "bg-red-950/20 border-red-800/40 text-red-200"
                    : "bg-cyan-950/20 border-cyan-800/40 text-cyan-200"
                  : "bg-slate-900/30 border-slate-800/50 text-slate-500 hover:border-slate-700/80 hover:text-slate-300"
              }`}
            >
              <div className="flex gap-2">
                <Icon className={`h-4 w-4 mt-0.5 ${active ? (item.warning ? "text-red-400" : "text-cyan-400") : "text-slate-500"}`} />
                <div>
                  <div className="font-bold">{item.label}</div>
                  <div className="text-[9px] text-slate-500 mt-0.5">{item.desc}</div>
                </div>
              </div>
              <div className="flex items-center">
                <span
                  className={`h-2.5 w-2.5 rounded-full ${
                    active ? (item.warning ? "bg-red-500 animate-pulse" : "bg-cyan-500") : "bg-slate-700"
                  }`}
                />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
