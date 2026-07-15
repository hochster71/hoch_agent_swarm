/**
 * HELM Voice Executive panel — shared client for console / founder / voice desk.
 * Doctrine: fail-closed speech, no secrets, default OFF, never invent metrics.
 */
(function (global) {
  'use strict';

  const DEFAULT_POLICY = {
    voice_enabled_default: false,
    voice_mode: 'local_tts',
    paid_providers_allowed: false,
    speak_secrets: false,
    require_operator_toggle: true,
    max_events_per_hour: 30,
    max_speech_chars: 1200,
  };

  const state = {
    enabled: false,
    muted: false,
    policy: { ...DEFAULT_POLICY },
    ttsProvider: 'local_tts', // local_tts | elevenlabs | auto
    eventCount: 0,
    windowStart: Date.now(),
    lastSpoken: '',
    lastResult: null,
    lastTtsStatus: null,
    _audio: null,
  };

  const SECRET_RES = [
    /sk-[A-Za-z0-9]{10,}/g,
    /pk_[A-Za-z0-9]{10,}/g,
    /Bearer\s+[A-Za-z0-9._\-]{8,}/gi,
    /(api[_-]?key|password|secret|token)\s*[:=]\s*\S+/gi,
    /\/Users\/[^\s]+/g,
    /-----BEGIN [A-Z ]+PRIVATE KEY-----[\s\S]*?-----END [A-Z ]+PRIVATE KEY-----/g,
  ];

  function apiBase() {
    return (global.HELM_VOICE_API_BASE != null) ? global.HELM_VOICE_API_BASE : '';
  }

  function sanitize(text) {
    let s = String(text || '');
    for (const re of SECRET_RES) s = s.replace(re, '[REDACTED]');
    s = s.replace(/\{[^{}]{40,}\}/g, '[REDACTED_JSON]');
    s = s.replace(/\s+/g, ' ').trim();
    const max = state.policy.max_speech_chars || 1200;
    if (s.length > max) s = s.slice(0, max - 1) + '…';
    return s;
  }

  function rateOk() {
    const hour = 60 * 60 * 1000;
    if (Date.now() - state.windowStart > hour) {
      state.windowStart = Date.now();
      state.eventCount = 0;
    }
    const max = state.policy.max_events_per_hour || 30;
    return state.eventCount < max;
  }

  function speakLocal(clean) {
    if (!global.speechSynthesis) return false;
    try {
      global.speechSynthesis.cancel();
      const u = new SpeechSynthesisUtterance(clean);
      u.rate = 1.0;
      u.pitch = 1.0;
      global.speechSynthesis.speak(u);
      return true;
    } catch (e) {
      return false;
    }
  }

  async function speakElevenLabs(clean) {
    const r = await fetch(apiBase() + '/api/v1/helm/voice/tts/speak', {
      method: 'POST',
      cache: 'no-store',
      headers: { 'Content-Type': 'application/json', 'Accept': 'audio/mpeg, application/json' },
      body: JSON.stringify({ text: clean, format: 'audio' }),
    });
    if (!r.ok) {
      // fail closed to local
      return speakLocal(clean);
    }
    const ct = r.headers.get('Content-Type') || '';
    if (ct.indexOf('audio') === -1) {
      return speakLocal(clean);
    }
    const blob = await r.blob();
    const url = URL.createObjectURL(blob);
    try {
      if (state._audio) {
        state._audio.pause();
        state._audio = null;
      }
      const audio = new Audio(url);
      state._audio = audio;
      audio.onended = () => { try { URL.revokeObjectURL(url); } catch (_) {} };
      await audio.play();
      return true;
    } catch (e) {
      try { URL.revokeObjectURL(url); } catch (_) {}
      return speakLocal(clean);
    }
  }

  function speak(text) {
    if (!state.enabled || state.muted) return false;
    if (!rateOk()) return false;
    const clean = sanitize(text);
    if (!clean || clean === '[REDACTED]') return false;

    const preferEl =
      state.ttsProvider === 'elevenlabs' ||
      (state.ttsProvider === 'auto' && state.policy.elevenlabs_ready) ||
      state.policy.voice_mode === 'elevenlabs';

    state.lastSpoken = clean;
    state.eventCount += 1;
    _emit();

    if (preferEl && state.policy.paid_providers_allowed && state.policy.elevenlabs_ready) {
      speakElevenLabs(clean).then((ok) => { if (!ok) speakLocal(clean); _emit(); });
      return true;
    }
    // local_tts path (default) — free, no network
    return speakLocal(clean);
  }

  async function loadTtsStatus() {
    try {
      const d = await fetchJSON('/api/v1/helm/voice/tts/status');
      state.lastTtsStatus = d;
      _emit();
      return d;
    } catch (e) {
      state.lastTtsStatus = { status: 'UNKNOWN', error: String(e.message || e) };
      _emit();
      return state.lastTtsStatus;
    }
  }

  async function fetchJSON(path, opts) {
    const r = await fetch(apiBase() + path, {
      cache: 'no-store',
      headers: { 'Accept': 'application/json', ...(opts && opts.headers || {}) },
      ...opts,
    });
    if (!r.ok) throw new Error('HTTP ' + r.status);
    return r.json();
  }

  async function loadPolicy() {
    try {
      const d = await fetchJSON('/api/v1/helm/voice/policy');
      state.policy = { ...DEFAULT_POLICY, ...(d.policy || {}) };
      if (state.policy.voice_enabled_default && !state.policy.require_operator_toggle) {
        state.enabled = true;
      }
      _emit();
      return state.policy;
    } catch (e) {
      state.policy = { ...DEFAULT_POLICY };
      _emit();
      return state.policy;
    }
  }

  async function brief(andSpeak) {
    const d = await fetchJSON('/api/v1/helm/voice/brief');
    state.lastResult = d;
    if (andSpeak && d.speech_text) speak(d.speech_text);
    _emit();
    return d;
  }

  async function command(cmd, utterance, andSpeak) {
    const d = await fetchJSON('/api/v1/helm/voice/command', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ command: cmd || null, utterance: utterance || null }),
    });
    state.lastResult = d;
    if (andSpeak && d.speech_text) speak(d.speech_text);
    _emit();
    return d;
  }

  async function listCommands() {
    return fetchJSON('/api/v1/helm/voice/commands');
  }

  function setEnabled(on) {
    state.enabled = !!on;
    if (!on && global.speechSynthesis) global.speechSynthesis.cancel();
    _emit();
  }

  function setMuted(on) {
    state.muted = !!on;
    if (on && global.speechSynthesis) global.speechSynthesis.cancel();
    _emit();
  }

  const listeners = [];
  function onChange(fn) { listeners.push(fn); }
  function _emit() { listeners.forEach((fn) => { try { fn(getState()); } catch (_) {} }); }

  function getState() {
    const mode =
      !state.enabled ? 'DISABLED'
      : state.muted ? 'MUTED'
      : (state.ttsProvider === 'elevenlabs' || state.policy.voice_mode === 'elevenlabs')
        ? (state.policy.elevenlabs_ready ? 'ELEVENLABS' : 'ELEVENLABS_BLOCKED')
        : 'LOCAL_TTS';
    return {
      enabled: state.enabled,
      muted: state.muted,
      policy: state.policy,
      ttsProvider: state.ttsProvider,
      lastSpoken: state.lastSpoken,
      lastResult: state.lastResult,
      lastTtsStatus: state.lastTtsStatus,
      eventCount: state.eventCount,
      policyStatus: mode,
    };
  }

  /**
   * Mount a compact control panel into containerEl.
   */
  function mount(containerEl, opts) {
    opts = opts || {};
    const el = typeof containerEl === 'string' ? document.querySelector(containerEl) : containerEl;
    if (!el) return;
    el.innerHTML = `
      <div class="helm-voice-panel" id="helm-voice-panel" style="
        background:var(--card,#141922);border:1px solid var(--line,#232b38);
        border-radius:8px;padding:12px;font:12px/1.5 ui-monospace,Menlo,monospace;color:var(--tx,#e6edf3)">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px">
          <strong style="letter-spacing:.1em;font-size:11px;color:var(--dim,#8b98a9)">HELM VOICE EXECUTIVE</strong>
          <span id="hv-status" style="font-size:10px;padding:1px 8px;border-radius:10px;background:rgba(139,148,158,.16)">DISABLED</span>
        </div>
        <div style="display:flex;flex-wrap:wrap;gap:10px;align-items:center;margin-bottom:8px">
          <label style="display:flex;gap:6px;align-items:center;cursor:pointer">
            <input type="checkbox" id="hv-enabled"/> Enable speech
          </label>
          <label style="display:flex;gap:6px;align-items:center;cursor:pointer">
            <input type="checkbox" id="hv-mute"/> Mute
          </label>
          <label style="display:flex;gap:6px;align-items:center;font-size:11px">
            TTS
            <select id="hv-tts" style="background:#0d1117;color:inherit;border:1px solid #30363d;border-radius:6px;padding:2px 6px">
              <option value="local_tts">Local (free)</option>
              <option value="auto">Auto (ElevenLabs if ready)</option>
              <option value="elevenlabs">ElevenLabs</option>
            </select>
          </label>
          <span id="hv-tts-ready" style="font-size:10px;color:var(--dim,#8b98a9)">tts…</span>
          <button id="hv-brief" type="button" style="cursor:pointer;padding:4px 10px;border-radius:6px;border:1px solid #30363d;background:#21262d;color:inherit">Brief</button>
          <button id="hv-approvals" type="button" style="cursor:pointer;padding:4px 10px;border-radius:6px;border:1px solid #30363d;background:#21262d;color:inherit">Approvals</button>
          <button id="hv-blocked" type="button" style="cursor:pointer;padding:4px 10px;border-radius:6px;border:1px solid #30363d;background:#21262d;color:inherit">Blocked</button>
          <button id="hv-revenue" type="button" style="cursor:pointer;padding:4px 10px;border-radius:6px;border:1px solid #30363d;background:#21262d;color:inherit">Revenue</button>
          <button id="hv-sec" type="button" style="cursor:pointer;padding:4px 10px;border-radius:6px;border:1px solid #30363d;background:#21262d;color:inherit">Sec HIGH</button>
          <label style="display:flex;gap:6px;align-items:center;cursor:pointer;font-size:11px">
            <input type="checkbox" id="hv-sec-poll"/> Poll security
          </label>
        </div>
        <div style="display:flex;gap:6px;margin-bottom:8px">
          <input id="hv-utter" type="text" placeholder="Say a command… e.g. highest priority mission"
            style="flex:1;padding:6px 8px;border-radius:6px;border:1px solid #30363d;background:#0d1117;color:inherit"/>
          <button id="hv-run" type="button" style="cursor:pointer;padding:4px 12px;border-radius:6px;border:1px solid #30363d;background:#21262d;color:inherit">Run</button>
        </div>
        <div class="k" style="color:var(--dim,#8b98a9);font-size:10px;margin-bottom:4px">LAST RESULT · labels only from Runtime Truth</div>
        <div id="hv-out" style="white-space:pre-wrap;font-size:11px;max-height:140px;overflow:auto;color:#c9d1d9">—</div>
        <div style="margin-top:6px;font-size:10px;color:var(--dim,#8b98a9)">Last spoken: <span id="hv-spoken">—</span></div>
        <div style="margin-top:4px;font-size:10px;color:var(--dim,#8b98a9)">no_fake_green · DOORSTEP never auto-executed · secrets redacted</div>
      </div>`;

    const $ = (id) => el.querySelector(id);
    const statusEl = $('#hv-status');
    const outEl = $('#hv-out');
    const spokenEl = $('#hv-spoken');

    function paint() {
      const s = getState();
      statusEl.textContent = s.policyStatus;
      statusEl.style.background = s.enabled && !s.muted
        ? 'rgba(46,160,67,.16)' : 'rgba(139,148,158,.16)';
      statusEl.style.color = s.enabled && !s.muted ? '#2ea043' : '#8b949e';
      spokenEl.textContent = s.lastSpoken || '—';
      if (s.lastResult) {
        const labels = s.lastResult.labels
          ? Object.entries(s.lastResult.labels).map(([k, v]) => k + '=' + v).join(' · ')
          : '';
        outEl.textContent =
          (s.lastResult.status || '—') +
          (s.lastResult.command ? ' · ' + s.lastResult.command : '') +
          (s.lastResult.mode ? ' · ' + s.lastResult.mode : '') +
          '\n' + (s.lastResult.speech_text || '') +
          (labels ? '\n[' + labels + ']' : '');
      }
    }

    onChange(paint);

    $('#hv-enabled').addEventListener('change', (e) => setEnabled(e.target.checked));
    $('#hv-mute').addEventListener('change', (e) => setMuted(e.target.checked));
    $('#hv-tts').addEventListener('change', (e) => {
      state.ttsProvider = e.target.value;
      _emit();
    });
    const ttsReadyEl = $('#hv-tts-ready');
    function paintTtsReady() {
      const p = state.policy || {};
      const ready = !!p.elevenlabs_ready;
      const key = !!p.elevenlabs_key_present;
      if (ready) ttsReadyEl.textContent = 'ElevenLabs READY';
      else if (key) ttsReadyEl.textContent = 'ElevenLabs key set · policy blocks paid';
      else ttsReadyEl.textContent = 'ElevenLabs BLOCKED · use Local or set key+policy';
      ttsReadyEl.style.color = ready ? '#2ea043' : '#8b949e';
    }
    onChange(paintTtsReady);
    $('#hv-brief').addEventListener('click', async () => {
      try {
        await brief(state.enabled && !state.muted);
        paint();
      } catch (e) {
        outEl.textContent = 'UNKNOWN — brief unreachable: ' + e.message;
      }
    });
    $('#hv-approvals').addEventListener('click', async () => {
      try {
        await command('founder_approvals', null, state.enabled && !state.muted);
        paint();
      } catch (e) {
        outEl.textContent = 'UNKNOWN — ' + e.message;
      }
    });
    $('#hv-blocked').addEventListener('click', async () => {
      try {
        await command('blocked_factories', null, state.enabled && !state.muted);
        paint();
      } catch (e) {
        outEl.textContent = 'UNKNOWN — ' + e.message;
      }
    });
    $('#hv-revenue').addEventListener('click', async () => {
      try {
        const d = await fetchJSON('/api/v1/helm/voice/revenue');
        state.lastResult = d;
        if (state.enabled && !state.muted && d.speech_text) speak(d.speech_text);
        paint();
      } catch (e) {
        outEl.textContent = 'UNKNOWN — ' + e.message;
      }
    });
    let secTimer = null;
    async function pollSecurity(andAck) {
      try {
        const q = andAck ? '?mark_spoken=true' : '';
        const d = await fetchJSON('/api/v1/helm/voice/security/events' + q);
        state.lastResult = d;
        if (state.enabled && !state.muted && d.emit_count > 0 && d.speech_text) {
          speak(d.speech_text);
          // advance cursor so we don't re-speak the same HIGH forever
          if (!andAck) await fetchJSON('/api/v1/helm/voice/security/events?mark_spoken=true');
        }
        paint();
      } catch (e) {
        outEl.textContent = 'UNKNOWN — ' + e.message;
      }
    }
    $('#hv-sec').addEventListener('click', () => pollSecurity(false));
    $('#hv-sec-poll').addEventListener('change', (e) => {
      if (secTimer) { clearInterval(secTimer); secTimer = null; }
      if (e.target.checked) {
        pollSecurity(false);
        secTimer = setInterval(() => pollSecurity(false), 60000);
      }
    });
    $('#hv-run').addEventListener('click', async () => {
      const u = $('#hv-utter').value.trim();
      if (!u) return;
      try {
        await command(null, u, state.enabled && !state.muted);
        paint();
      } catch (e) {
        outEl.textContent = 'UNKNOWN — ' + e.message;
      }
    });

    loadPolicy().then(() => { paint(); paintTtsReady(); loadTtsStatus(); });
    paint();
  }

  global.HELMVoice = {
    sanitize,
    speak,
    brief,
    command,
    listCommands,
    loadPolicy,
    loadTtsStatus,
    setEnabled,
    setMuted,
    getState,
    mount,
    onChange,
  };
})(typeof window !== 'undefined' ? window : globalThis);
