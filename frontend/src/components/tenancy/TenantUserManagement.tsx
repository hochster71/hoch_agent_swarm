import React, { useState } from "react";
import type { TenantRecord } from "../../lib/tenancy/tenantTypes";
import { useTenantStore } from "../../lib/tenancy/tenantRegistry";
import { UserCheck, Plus, ShieldCheck } from "lucide-react";

type Props = {
  tenant: TenantRecord;
};

export function TenantUserManagement({ tenant }: Props) {
  const { addUserToTenant } = useTenantStore();

  const [newName, setNewName] = useState("");
  const [newEmail, setNewEmail] = useState("");
  const [showAddUser, setShowAddUser] = useState(false);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newName || !newEmail) {
      alert("Name and email are required.");
      return;
    }
    
    addUserToTenant(tenant.tenant_id, {
      user_id: `usr-${Math.random().toString(36).substring(2, 6)}`,
      name: newName,
      email: newEmail,
    });

    setNewName("");
    setNewEmail("");
    setShowAddUser(false);
  };

  return (
    <div className="rounded-lg border border-slate-800 bg-slate-950/60 p-4 font-mono text-[11px] space-y-4">
      <div className="flex items-center justify-between border-b border-slate-900 pb-2">
        <h3 className="text-xs font-bold tracking-wider text-slate-400 uppercase flex items-center gap-1.5">
          <UserCheck className="h-4 w-4 text-cyan-400" />
          Tenant Admin User Directory
        </h3>
        <button
          onClick={() => setShowAddUser(!showAddUser)}
          className="px-2.5 py-1 rounded bg-slate-900 border border-slate-800 text-cyan-400 font-bold hover:bg-slate-800 text-[10px] flex items-center gap-1"
        >
          <Plus className="h-3.5 w-3.5" /> Add User
        </button>
      </div>

      {showAddUser && (
        <form onSubmit={handleSubmit} className="p-3 bg-slate-900/30 border border-slate-900 rounded space-y-3">
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-slate-500 mb-1">Full Name</label>
              <input
                type="text"
                placeholder="e.g. Clark Kent"
                value={newName}
                onChange={e => setNewName(e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 rounded px-2 py-1 outline-none text-slate-300 focus:border-cyan-500"
              />
            </div>
            <div>
              <label className="block text-slate-500 mb-1">Email</label>
              <input
                type="email"
                placeholder="e.g. clark@stark.com"
                value={newEmail}
                onChange={e => setNewEmail(e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 rounded px-2 py-1 outline-none text-slate-300 focus:border-cyan-500"
              />
            </div>
          </div>
          <div className="flex justify-end gap-2">
            <button
              type="button"
              onClick={() => setShowAddUser(false)}
              className="px-2.5 py-1 rounded border border-slate-800 text-slate-400"
            >
              Cancel
            </button>
            <button
              type="submit"
              className="px-3 py-1 rounded bg-cyan-500 text-slate-950 font-bold hover:bg-cyan-400"
            >
              Invite
            </button>
          </div>
        </form>
      )}

      <div className="space-y-2">
        {tenant.admins.map((admin) => (
          <div key={admin.user_id} className="p-2.5 rounded bg-slate-900/30 border border-slate-900 flex justify-between items-center text-slate-300">
            <div>
              <span className="font-bold text-slate-200">{admin.name}</span>
              <span className="text-slate-500 block text-[9px] uppercase mt-0.5">{admin.email}</span>
            </div>
            <span className="text-[8px] bg-cyan-950/20 border border-cyan-900/40 text-cyan-400 px-1.5 py-0.5 rounded font-bold uppercase flex items-center gap-1">
              <ShieldCheck className="h-3 w-3" /> Tenant Admin
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
