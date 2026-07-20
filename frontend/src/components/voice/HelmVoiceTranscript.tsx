import React from 'react';

interface HelmVoiceTranscriptProps {
  transcript: string;
  onChange: (val: string) => void;
  onSubmit: () => void;
}

export const HelmVoiceTranscript: React.FC<HelmVoiceTranscriptProps> = ({
  transcript,
  onChange,
  onSubmit,
}) => {
  return (
    <div className="space-y-2">
      <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider block">
        Transcript Review / Text Fallback
      </label>
      <div className="flex space-x-2">
        <input
          type="text"
          value={transcript}
          onChange={(e) => onChange(e.target.value)}
          placeholder="Speak or type command..."
          className="flex-1 bg-slate-800 border border-slate-700 rounded px-3 py-2 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-indigo-500"
        />
        <button
          onClick={onSubmit}
          className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 rounded text-sm font-medium transition-colors"
        >
          Submit
        </button>
      </div>
    </div>
  );
};
