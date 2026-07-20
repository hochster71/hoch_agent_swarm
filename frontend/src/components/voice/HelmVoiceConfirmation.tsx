import React from 'react';

interface HelmVoiceConfirmationProps {
  challengeId: string;
  code: string;
  onChange: (val: string) => void;
  onConfirm: () => void;
  onCancel: () => void;
}

export const HelmVoiceConfirmation: React.FC<HelmVoiceConfirmationProps> = ({
  challengeId,
  code,
  onChange,
  onConfirm,
  onCancel,
}) => {
  return (
    <div className="p-4 bg-amber-950/40 border border-amber-800/60 rounded-lg space-y-4">
      <div className="flex items-center space-x-2 text-amber-500">
        <svg
          className="w-5 h-5"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
          xmlns="http://www.w3.org/2000/svg"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
          />
        </svg>
        <span className="text-sm font-semibold">Verification Required: Challenge {challengeId}</span>
      </div>
      
      <p className="text-xs text-slate-300">
        Enter the 3-digit confirmation code generated in your session to proceed with command execution.
      </p>

      <div className="flex space-x-2">
        <input
          type="text"
          maxLength={3}
          value={code}
          onChange={(e) => onChange(e.target.value.replace(/\D/g, ''))}
          placeholder="000"
          className="w-20 bg-slate-800 border border-slate-700 rounded px-3 py-2 text-center text-lg font-bold tracking-widest text-slate-100 placeholder-slate-600 focus:outline-none focus:border-amber-500"
        />
        <button
          onClick={onConfirm}
          className="px-4 py-2 bg-amber-600 hover:bg-amber-500 rounded text-sm font-medium transition-colors text-white"
        >
          Confirm
        </button>
        <button
          onClick={onCancel}
          className="px-4 py-2 bg-slate-800 hover:bg-slate-700 rounded text-sm font-medium transition-colors text-slate-300"
        >
          Cancel
        </button>
      </div>
    </div>
  );
};
