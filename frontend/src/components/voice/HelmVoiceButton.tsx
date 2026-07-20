import React from 'react';

interface HelmVoiceButtonProps {
  isRecording: boolean;
  onStart: () => void;
  onStop: () => void;
}

export const HelmVoiceButton: React.FC<HelmVoiceButtonProps> = ({ isRecording, onStart, onStop }) => {
  return (
    <button
      onMouseDown={onStart}
      onMouseUp={onStop}
      onTouchStart={onStart}
      onTouchEnd={onStop}
      className={`w-20 h-20 rounded-full flex items-center justify-center transition-all duration-300 transform active:scale-95 ${
        isRecording
          ? 'bg-red-600 shadow-lg shadow-red-500/50 animate-pulse'
          : 'bg-indigo-600 hover:bg-indigo-500 shadow-md shadow-indigo-500/30'
      }`}
      aria-label="Push to Talk"
    >
      <svg
        className="w-8 h-8 text-white"
        fill="none"
        stroke="currentColor"
        viewBox="0 0 24 24"
        xmlns="http://www.w3.org/2000/svg"
      >
        {isRecording ? (
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
          />
        ) : (
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z"
          />
        )}
      </svg>
    </button>
  );
};
