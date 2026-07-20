import React from 'react';

interface HelmVoiceSessionHistoryProps {
  history: any[];
}

export const HelmVoiceSessionHistory: React.FC<HelmVoiceSessionHistoryProps> = ({ history }) => {
  return (
    <div className="space-y-2">
      <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-wider block">
        Auditable Events Session History
      </h3>
      {history.length === 0 ? (
        <p className="text-xs text-slate-500 italic">No events recorded in this session.</p>
      ) : (
        <div className="border border-slate-700 rounded divide-y divide-slate-800 bg-slate-850 max-h-48 overflow-y-auto">
          {history.map((event, idx) => (
            <div key={idx} className="p-3 flex justify-between items-center text-xs">
              <div>
                <p className="font-semibold text-slate-200">{event.action}</p>
                <p className="text-slate-500 font-mono text-[10px]">{event.id}</p>
              </div>
              <div className="text-right">
                <span
                  className={`inline-block px-2 py-0.5 rounded font-medium text-[10px] ${
                    event.status === 'ALLOW' || event.status === 'SUCCESS'
                      ? 'bg-green-950/40 text-green-400 border border-green-800/40'
                      : 'bg-amber-950/40 text-amber-400 border border-amber-800/40'
                  }`}
                >
                  {event.status}
                </span>
                <p className="text-[10px] text-slate-500 mt-1">{event.timestamp}</p>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
