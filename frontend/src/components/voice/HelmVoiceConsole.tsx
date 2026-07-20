import React, { useState, useEffect } from 'react';
import { HelmVoiceButton } from './HelmVoiceButton';
import { HelmVoiceTranscript } from './HelmVoiceTranscript';
import { HelmVoiceConfirmation } from './HelmVoiceConfirmation';
import { HelmVoiceSessionHistory } from './HelmVoiceSessionHistory';
import { HelmVoiceTruthBadge } from './HelmVoiceTruthBadge';

export const HelmVoiceConsole: React.FC = () => {
  const [status, setStatus] = useState<'TEST' | 'LIVE' | 'OFFLINE' | 'UNKNOWN'>('TEST');
  const [transcript, setTranscript] = useState<string>('');
  const [isRecording, setIsRecording] = useState<boolean>(false);
  const [challengeId, setChallengeId] = useState<string | null>(null);
  const [confirmationCode, setConfirmationCode] = useState<string>('');
  const [history, setHistory] = useState<any[]>([]);

  useEffect(() => {
    // Fetch initial status from health check
    fetch('/api/v1/helm/voice/health')
      .then((res) => res.json())
      .then((data) => {
        if (data.SIRI === 'TEST' && data.ALEXA === 'TEST') {
          setStatus('TEST');
        } else {
          setStatus('LIVE');
        }
      })
      .catch(() => setStatus('UNKNOWN'));
  }, []);

  const handleTranscriptSubmit = (finalText: string) => {
    setTranscript(finalText);
    
    // Simulate sending transcript to FastAPI backend PTT endpoint
    fetch('/api/v1/helm/voice/web/transcript', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        transcript: finalText,
        session_id: 'sess-web-ui',
        actor_id: 'founder'
      })
    })
      .then((res) => res.json())
      .then((data) => {
        setHistory((prev) => [
          {
            id: data.request_id || 'REQ-PTT',
            action: finalText,
            status: data.status,
            timestamp: new Date().toLocaleTimeString()
          },
          ...prev
        ]);
        
        if (data.confirmation_required) {
          setChallengeId(data.challenge_id);
        } else {
          setTranscript('');
        }
      })
      .catch((err) => {
        console.error('PTT Submission error:', err);
        setStatus('UNKNOWN');
      });
  };

  const handleConfirmCode = (code: string) => {
    fetch('/api/v1/helm/voice/confirm', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        session_id: 'sess-web-ui',
        code: code
      })
    })
      .then((res) => {
        if (res.ok) {
          setChallengeId(null);
          setTranscript('');
          setConfirmationCode('');
        } else {
          alert('Invalid confirmation challenge code.');
        }
      });
  };

  return (
    <div className="p-6 bg-slate-900 text-slate-100 rounded-lg shadow-xl max-w-2xl mx-auto space-y-6">
      <div className="flex justify-between items-center border-b border-slate-700 pb-4">
        <h1 className="text-xl font-bold tracking-tight">HELM Voice Gateway Control Console</h1>
        <HelmVoiceTruthBadge status={status} />
      </div>

      <div className="flex flex-col items-center justify-center py-8 space-y-4 bg-slate-800/50 rounded-lg border border-slate-700">
        <HelmVoiceButton
          isRecording={isRecording}
          onStart={() => {
            setIsRecording(true);
            setTranscript('Listening...');
          }}
          onStop={() => {
            setIsRecording(false);
            handleTranscriptSubmit('status summary');
          }}
        />
        <p className="text-sm text-slate-400">
          {isRecording ? 'Recording audio... Release to submit.' : 'Push and hold to talk.'}
        </p>
      </div>

      <HelmVoiceTranscript
        transcript={transcript}
        onChange={(val) => setTranscript(val)}
        onSubmit={() => handleTranscriptSubmit(transcript)}
      />

      {challengeId && (
        <HelmVoiceConfirmation
          challengeId={challengeId}
          code={confirmationCode}
          onChange={setConfirmationCode}
          onConfirm={() => handleConfirmCode(confirmationCode)}
          onCancel={() => setChallengeId(null)}
        />
      )}

      <HelmVoiceSessionHistory history={history} />
    </div>
  );
};
