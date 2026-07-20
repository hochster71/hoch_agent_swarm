import React from 'react';

interface HelmVoiceTruthBadgeProps {
  status: 'TEST' | 'LIVE' | 'OFFLINE' | 'UNKNOWN';
}

export const HelmVoiceTruthBadge: React.FC<HelmVoiceTruthBadgeProps> = ({ status }) => {
  const badgeConfig = {
    TEST: {
      text: 'TEST / LOCAL ONLY',
      bg: 'bg-blue-950/40 text-blue-400 border-blue-800/40',
    },
    LIVE: {
      text: 'LIVE INTEGRATION',
      bg: 'bg-green-950/40 text-green-400 border-green-800/40',
    },
    OFFLINE: {
      text: 'GATEWAY OFFLINE',
      bg: 'bg-red-950/40 text-red-400 border-red-800/40',
    },
    UNKNOWN: {
      text: 'UNKNOWN STATUS',
      bg: 'bg-slate-850 text-slate-400 border-slate-700/40',
    },
  };

  const config = badgeConfig[status] || badgeConfig.UNKNOWN;

  return (
    <span
      className={`px-2.5 py-1 text-[10px] font-bold rounded border uppercase tracking-widest ${config.bg}`}
    >
      {config.text}
    </span>
  );
};
export default HelmVoiceTruthBadge;
