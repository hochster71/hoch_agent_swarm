import React from 'react';
import { Shield } from 'lucide-react';

interface InternalAccessBannerProps {
  mode: 'paid_customer' | 'internal_preview' | 'stripe_test' | 'founder_override' | null;
}

export function InternalAccessBanner({ mode }: InternalAccessBannerProps) {
  if (!mode || mode === 'paid_customer') return null;

  // Format mode names nicely
  const modeLabels: Record<string, string> = {
    founder_override: 'Founder Override',
    internal_preview: 'Internal Preview Mode',
    stripe_test: 'Stripe Test Mode',
  };

  const label = modeLabels[mode] || mode;

  return (
    <div 
      id="internal-access-banner"
      className="bg-yellow-950/80 border-b border-yellow-700/50 text-yellow-200 px-4 py-2 text-xs font-mono flex items-center justify-between gap-2 shadow-md backdrop-blur-sm z-50 w-full"
    >
      <div className="flex items-center gap-2">
        <Shield className="w-4 h-4 text-yellow-400 animate-pulse" />
        <span>
          <strong>Internal Preview Mode</strong> — No customer payment required
        </span>
      </div>
      <div className="flex items-center gap-3">
        <span className="bg-yellow-800/60 px-2 py-0.5 rounded border border-yellow-600/30 text-[10px] uppercase tracking-wider text-yellow-100 font-bold">
          Source: {mode}
        </span>
      </div>
    </div>
  );
}
