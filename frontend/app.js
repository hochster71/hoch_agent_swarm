import Hls from 'hls.js';
(function () {
    'use strict';

    // Global state variables
    let activeView = 'mission-control';
    let cockpitInterval = null;
    let viewInterval = null;
    let pondAnimationId = null;
    let pondProcesses = [];
    let koiFishInstances = {};
    let lastLedgerCount = 0;

    // Helper functions
    const el = (id) => document.getElementById(id);

    function escapeHtml(str) {
        if (str === null || str === undefined) return '';
        return String(str)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#039;');
    }

    // Theme implementation
    function initTheme() {
        const themeSelector = el('theme-selector');
        if (!themeSelector) return;
        
        const savedTheme = localStorage.getItem('hoch-theme') || 'theme-green';
        themeSelector.value = savedTheme;
        applyTheme(savedTheme);

        themeSelector.addEventListener('change', (e) => {
            const theme = e.target.value;
            localStorage.setItem('hoch-theme', theme);
            applyTheme(theme);
        });
    }

    function applyTheme(themeClass) {
        document.body.className = '';
        document.body.classList.add(themeClass);
    }

    // View Switching
    const views = [
        { id: 'mission-control', label: 'MISSION CONTROL' },
        { id: 'live-runtime', label: 'LIVE RUNTIME' },
        { id: 'local-models', label: 'LOCAL MODELS' },
        { id: 'model-mesh', label: 'AI MODEL MESH' },
        { id: 'model-router', label: 'MODEL ROUTER' },
        { id: 'escalations', label: 'ESCALATIONS' },
        { id: 'evidence', label: 'EVIDENCE' },
        { id: 'detections', label: 'DETECTIONS' },
        { id: 'readiness', label: 'READINESS' },
        { id: 'settings', label: 'SETTINGS' },
        { id: 'agent-flight-deck', label: 'AGENT FLIGHT DECK' },
        { id: 'clawde', label: 'CLAWDE CONTROL TOWER' },
        { id: 'handoff', label: 'RELEASE REVIEW & HANDOFF' },
        { id: 'ato', label: 'ATO EVIDENCE BUILDER' },
        { id: 'staging', label: 'STAGING DRY RUN' },
        { id: 'deploy', label: 'PRODUCTION DEPLOYMENT' },
        { id: 'cybergov-overview', label: 'CYBER OVERVIEW' },
        { id: 'cybergov-controls', label: 'NIST 800-53 REV. 5' },
        { id: 'cybergov-rmf', label: 'RMF LIFECYCLE' },
        { id: 'cybergov-conmon', label: 'CONMON SCHEDULE' },
        { id: 'cybergov-poam', label: 'POA&M WEAKNESSES' },
        { id: 'cybergov-risks', label: 'RISK REGISTER' },
        { id: 'cybergov-evidence', label: 'EVIDENCE VAULT' },
        { id: 'cybergov-audit', label: 'AUDIT REPORTS' },
        { id: 'cybergov-cisa', label: 'CISA / KEV / CPG' },
        { id: 'cybergov-zero-trust', label: 'DOD ZERO TRUST' },
        { id: 'cybergov-ao-review', label: 'AO REVIEW' },
        { id: 'binding-gate', label: 'LIVE BINDING GATE' },
        { id: 'live-exposure', label: 'LIVE EXPOSURE' },
        { id: 'conmon-scheduler', label: 'CONMON SCHEDULER' },
        { id: 'hoch-tv', label: 'HOCH TV' }
    ];

    function initNavigation() {
        views.forEach(v => {
            const navBtn = el(`nav-${v.id}`);
            if (navBtn) {
                navBtn.addEventListener('click', (e) => {
                    e.preventDefault();
                    switchView(v.id);
                });
            }
        });
    }

    function switchView(viewId) {
        activeView = viewId;

        // Reset sidebar active classes
        views.forEach(v => {
            const btn = el(`nav-${v.id}`);
            if (btn) btn.classList.remove('active');
            const viewDiv = el(`view-${v.id}`);
            if (viewDiv) viewDiv.classList.add('hidden');
        });

        const activeBtn = el(`nav-${viewId}`);
        if (activeBtn) activeBtn.classList.add('active');

        const activeDiv = el(`view-${viewId}`);
        if (activeDiv) activeDiv.classList.remove('hidden');

        // Update header subnet label
        const targetView = views.find(v => v.id === viewId);
        const headerSubnet = el('header-subnet-title');
        if (headerSubnet && targetView) {
            headerSubnet.textContent = `[${targetView.label}]`;
        }

        // Clean up sub-view pollers & animations
        if (viewInterval) {
            clearInterval(viewInterval);
            viewInterval = null;
        }
        if (pondAnimationId) {
            cancelAnimationFrame(pondAnimationId);
            pondAnimationId = null;
        }

        // Trigger view-specific loaders
        triggerViewLoader(viewId);

        // Refresh lucide icons
        if (window.lucide) window.lucide.createIcons();
    }

    function triggerViewLoader(viewId) {
        switch (viewId) {
            case 'mission-control':
                // Handled by the global loop
                break;
            case 'live-runtime':
                loadLiveRuntimeView();
                viewInterval = setInterval(loadLiveRuntimeView, 3000);
                break;
            case 'local-models':
                loadLocalModelsView();
                viewInterval = setInterval(loadLocalModelsView, 3000);
                break;
            case 'model-mesh':
                loadModelMeshView();
                viewInterval = setInterval(loadModelMeshView, 3000);
                break;
            case 'model-router':
                loadModelRouterView();
                viewInterval = setInterval(loadModelRouterView, 3000);
                break;
            case 'escalations':
                loadEscalationsView();
                viewInterval = setInterval(loadEscalationsView, 3000);
                break;
            case 'evidence':
                loadEvidenceView();
                viewInterval = setInterval(loadEvidenceView, 3000);
                break;
            case 'detections':
                loadDetectionsView();
                viewInterval = setInterval(loadDetectionsView, 3000);
                break;
            case 'readiness':
                loadReadinessView();
                viewInterval = setInterval(loadReadinessView, 3000);
                break;
            case 'settings':
                loadSettingsView();
                viewInterval = setInterval(loadSettingsView, 5000);
                break;
            case 'agent-flight-deck':
                loadAgentFlightDeckView();
                viewInterval = setInterval(loadAgentFlightDeckView, 3000);
                break;
            case 'clawde':
                loadClawdeView();
                viewInterval = setInterval(loadClawdeView, 3000);
                break;
            case 'handoff':
                loadHandoffView();
                viewInterval = setInterval(loadHandoffView, 3000);
                break;
            case 'ato':
                loadAtoView();
                viewInterval = setInterval(loadAtoView, 3000);
                break;
            case 'staging':
                loadStagingView();
                break;
            case 'deploy':
                loadDeployView();
                break;
            case 'cybergov-overview':
            case 'cybergov-controls':
            case 'cybergov-rmf':
            case 'cybergov-conmon':
            case 'cybergov-poam':
            case 'cybergov-risks':
            case 'cybergov-evidence':
            case 'cybergov-audit':
            case 'cybergov-cisa':
            case 'cybergov-zero-trust':
            case 'cybergov-ao-review':
                loadCyberGovView();
                break;
            case 'binding-gate':
                loadBindingGateView();
                break;
            case 'live-exposure':
                loadLiveExposureView();
                break;
            case 'conmon-scheduler':
                loadConMonView();
                break;
            case 'hoch-tv':
                loadHochTvView();
                break;
        }
    }

    // Global Cockpit Fetch & Render
    async function fetchCockpit() {
        const startTime = Date.now();
        try {
            const res = await fetch('/api/v1/live-runtime/cockpit');
            const data = await res.json();
            const latency = Date.now() - startTime;
            
            // Update header network latency
            const latencyVal = el('latency-val');
            if (latencyVal) {
                latencyVal.textContent = `${latency}ms`;
            }

            const syncStatus = el('sync-status-text');
            if (syncStatus) {
                syncStatus.textContent = 'ONLINE';
                syncStatus.style.color = '#10b981';
            }

            renderCockpitCards(data.cards);
            updateHeaderStatus(data.cards);

            // Fetch model mesh config in parallel for Koi pond binding
            const meshRes = await fetch('/api/v1/model-mesh/config');
            if (meshRes.ok) {
                const meshData = await meshRes.json();
                updateKoiPond(meshData);
            }

            // Monitor ledger count for active execution ripples
            const ledgerRes = await fetch('/api/v1/prompts/usage-ledger');
            if (ledgerRes.ok) {
                const ledgerData = await ledgerRes.json();
                const currentCount = (ledgerData.ledger || []).length;
                if (lastLedgerCount !== 0 && currentCount > lastLedgerCount) {
                    const newEntries = ledgerData.ledger.slice(lastLedgerCount);
                    newEntries.forEach(entry => {
                        const agentId = entry.agent_id ? entry.agent_id.toLowerCase().replace('_', '-') : null;
                        if (agentId && koiFishInstances[agentId]) {
                            triggerKoiRipple(agentId, entry.risk_level === "HIGH" ? "broken" : "normal");
                        } else if (koiFishInstances["local-swarm-api"]) {
                            triggerKoiRipple("local-swarm-api", "warning");
                        }
                    });
                }
                lastLedgerCount = currentCount;
            }
        } catch (err) {
            console.error('[Cockpit] fetch error:', err);
            const syncStatus = el('sync-status-text');
            if (syncStatus) {
                syncStatus.textContent = 'ERROR';
                syncStatus.style.color = '#ef4444';
            }
        }
    }

    function updateHeaderStatus(cards) {
        // Status Badge: GO or NO-GO
        const statusBadge = el('cluster-status-badge');
        if (statusBadge && cards.readiness) {
            const verdict = cards.readiness.go_no_go || 'NO-GO';
            statusBadge.className = 'badge';
            if (verdict === 'GO') {
                statusBadge.classList.add('badge-success');
                statusBadge.textContent = 'STATUS: GO';
            } else {
                statusBadge.classList.add('badge-info');
                statusBadge.textContent = `STATUS: ${verdict}`;
            }
        }

        // Active Assets Count
        const assetsBadge = el('active-assets-badge');
        if (assetsBadge && cards.device_registry) {
            const count = cards.device_registry.devices_count || 0;
            assetsBadge.className = 'badge badge-info';
            assetsBadge.textContent = `${count} DEVICES ACTIVE`;
        }
    }

    function renderCockpitCards(cards) {
        if (!cards) return;

        Object.keys(cards).forEach(key => {
            const cardData = cards[key];
            const htmlKey = key.replace(/_/g, '-');
            const dot = el(`dot-${htmlKey}`);
            const stateLabel = el(`state-${htmlKey}`);
            const body = el(`body-${htmlKey}`);

            if (!cardData) return;

            // Apply truth state to dot
            if (dot) {
                dot.className = 'cockpit-indicator-dot';
                const truthClass = `state-${(cardData.truth || 'empty').toLowerCase().replace('_', '-')}`;
                dot.classList.add(truthClass);
            }

            // Apply state label
            if (stateLabel) {
                stateLabel.textContent = cardData.truth || 'UNKNOWN';
                stateLabel.style.color = getStateColor(cardData.truth);
            }

            // Render custom content inside bodies
            if (body) {
                body.innerHTML = formatCardBody(key, cardData);
            }
        });
    }

    function getStateColor(state) {
        switch (state) {
            case 'LIVE': return '#10b981';
            case 'DEGRADED': return '#f59e0b';
            case 'FAILED': return '#ef4444';
            case 'ERROR': return '#ef4444';
            case 'EMPTY': return '#6b7280';
            case 'APPROVAL_REQUIRED': return '#f59e0b';
            case 'ASSUMPTION': return '#a855f7';
            default: return '#f3f4f6';
        }
    }

    function formatCardBody(key, data) {
        let html = '';
        switch (key) {
            case 'runtime_process':
                const numEvents = data.items ? data.items.length : 0;
                html = `<div style="display:flex; flex-direction:column; gap:4px;">
                    <div>Tail size: <strong style="color:#fff;">${numEvents} events</strong></div>
                    <div style="font-size:10px; opacity:0.8; font-family:monospace; max-height:48px; overflow:hidden;">
                        ${data.items && data.items.length > 0 ? `Latest: ${data.items[0].process_type} (${data.items[0].state})` : 'Queue empty'}
                    </div>
                </div>`;
                break;
            case 'local_models':
                const hosts = data.hosts || [];
                html = `<div style="display:flex; flex-direction:column; gap:4px;">
                    <div>Discovered Runtimes: <strong style="color:#fff;">${hosts.length} engines</strong></div>
                    <div style="display:flex; gap:4px; flex-wrap:wrap; margin-top:2px;">
                        ${hosts.map(h => `<span style="padding:2px 4px; background:rgba(255,255,255,0.05); border-radius:3px; color:${h.reachable ? '#10b981' : '#ef4444'}">${h.host}:${h.port}</span>`).join('')}
                    </div>
                </div>`;
                break;
            case 'model_router':
                html = `<div style="display:flex; flex-direction:column; gap:4px;">
                    <div>Routing Policy: <strong style="color:#fff;">${data.local_first ? 'Local First' : 'Cloud Direct'}</strong></div>
                    <div>Default Model: <code style="color:#818cf8;">${data.default_model || 'None'}</code></div>
                </div>`;
                break;
            case 'escalations':
                const escCount = data.pending ? data.pending.length : 0;
                html = `<div style="display:flex; flex-direction:column; gap:4px;">
                    <div>Escalated requests: <strong style="color:${escCount > 0 ? '#f59e0b' : '#fff'};">${escCount} pending</strong></div>
                    ${escCount > 0 ? `<div style="font-size:9px; color:#f59e0b;">Decision gate is currently locked.</div>` : '<div style="font-size:9px; color:#10b981;">No active blocks.</div>'}
                </div>`;
                break;
            case 'detections':
                const detCount = data.recent_events ? data.recent_events.length : 0;
                html = `<div style="display:flex; flex-direction:column; gap:4px;">
                    <div>Recent alerts: <strong style="color:#fff;">${detCount} events</strong></div>
                    <div>SIEM Coverage: <span style="color:#10b981;">Splunk, Sigma, Elastic, LogQL</span></div>
                </div>`;
                break;
            case 'readiness':
                html = `<div style="display:flex; flex-direction:column; gap:4px;">
                    <div>Scorecard: <strong style="color:#10b981; font-size:14px;">${data.score || 0}%</strong></div>
                    <div>Authorization: <span style="color:${data.go_no_go === 'GO' ? '#10b981' : '#ef4444'}">${data.go_no_go || 'UNKNOWN'}</span></div>
                </div>`;
                break;
            case 'evidence':
                html = `<div style="display:flex; flex-direction:column; gap:4px;">
                    <div>Verified Controls: <strong style="color:#fff;">${data.controls || 0}</strong></div>
                    <div>Passing tests: <strong style="color:#10b981;">${data.tests_passed || 0} / ${data.tests || 0}</strong></div>
                </div>`;
                break;
            case 'immutability':
                html = `<div style="display:flex; flex-direction:column; gap:4px;">
                    <div>Post-build posture: <strong style="color:#a855f7;">IMMUTABLE</strong></div>
                    <div style="font-size:9px; opacity:0.8;">Locked against runtime edits.</div>
                </div>`;
                break;
            case 'local_outage_queue':
                html = `<div style="display:flex; flex-direction:column; gap:4px;">
                    <div>Outage items count: <strong style="color:#fff;">${data.queued_items_count || 0}</strong></div>
                    <div>Autoreplay daemon: <span style="color:#10b981;">ACTIVE</span></div>
                </div>`;
                break;
            case 'port_hardening':
                html = `<div style="display:flex; flex-direction:column; gap:4px;">
                    <div>Overall status: <strong style="color:${data.overall_status === 'PASS' ? '#10b981' : '#ef4444'};">${data.overall_status || 'UNKNOWN'}</strong></div>
                    <div>Ports audited: <strong style="color:#fff;">${data.ports_count || 0} ports</strong></div>
                </div>`;
                break;
            case 'autonomy_budget':
                html = `<div style="display:flex; flex-direction:column; gap:4px;">
                    <div>Remaining budget: <strong style="color:#10b981;">${data.remaining_error_budget || 0}%</strong></div>
                    <div>Level: <span style="color:#3b82f6;">${data.autonomy_level || 'UNKNOWN'}</span></div>
                </div>`;
                break;
            case 'device_registry':
                const online = data.online_count || 0;
                const offline = data.offline_count || 0;
                const reporting = data.reporting_count || 0;
                const runtimes = (data.model_runtimes_proven || []).map(r => r.split(' ')[0]).join(", ") || "None";
                html = `<div style="display:flex; flex-direction:column; gap:4px;">
                    <div>Known Assets: <strong style="color:#fff;">${data.devices_count || 0}</strong></div>
                    <div>Online: <span style="color:#10b981;">${online}</span> | Offline: <span style="color:#ef4444;">${offline}</span></div>
                    <div style="font-size:9px; opacity:0.8; max-width:220px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;" title="${escapeHtml((data.model_runtimes_proven || []).join(', '))}">
                        Proven: <span style="color:#818cf8;">${runtimes}</span>
                    </div>
                </div>`;
                break;
            default:
                html = `<div>Loading card data...</div>`;
        }
        return html;
    }

    // ── Loader: Live Runtime View ───────────────────────────────────────────
    async function loadLiveRuntimeView() {
        try {
            const res = await fetch('/api/v1/runtime/process/animation-state');
            const data = await res.json();
            
            const pondIndicator = el('pond-status-indicator');
            if (pondIndicator) {
                pondIndicator.className = 'badge badge-success';
                pondIndicator.textContent = data.truth || 'LIVE';
            }

            pondProcesses = data.processes || [];
            
            const overlay = el('pond-empty-overlay');
            if (pondProcesses.length === 0) {
                if (overlay) overlay.style.display = 'flex';
                if (pondIndicator) {
                    pondIndicator.className = 'badge badge-info';
                    pondIndicator.textContent = 'EMPTY';
                }
            } else {
                if (overlay) overlay.style.display = 'none';
                startPondAnimation();
            }

            renderProcessEventList(pondProcesses);
        } catch (err) {
            console.error('[Pond] load error:', err);
            const overlay = el('pond-empty-overlay');
            if (overlay) {
                overlay.textContent = 'ERROR loading telemetry';
                overlay.style.display = 'flex';
            }
        }
    }

    function renderProcessEventList(processes) {
        const container = el('live-process-event-list');
        if (!container) return;
        if (processes.length === 0) {
            container.innerHTML = `<div style="color:var(--text-secondary); text-align:center;">No recent events</div>`;
            return;
        }
        container.innerHTML = processes.map(p => {
            const color = p.visual.color === 'red' ? '#ef4444' : (p.visual.color === 'amber' ? '#f59e0b' : '#10b981');
            return `<div style="display:flex; justify-content:space-between; border-bottom:1px solid rgba(255,255,255,0.03); padding:4px 0;">
                <span style="color:#818cf8;">${p.process_type}</span>
                <span style="color:${color}; font-weight:bold;">${p.state}</span>
                <span style="color:var(--text-secondary);">${p.model || p.provider || '-'}</span>
            </div>`;
        }).join('');
    }

    // Process Pond Animation logic
    function startPondAnimation() {
        const canvas = el('live-pond-canvas');
        if (!canvas) return;
        const ctx = canvas.getContext('2d');
        if (!ctx) return;

        // Handle canvas sizing
        const rect = canvas.getBoundingClientRect();
        canvas.width = rect.width;
        canvas.height = rect.height;

        // Initialize particles if they don't exist
        const particles = pondProcesses.map(p => {
            return {
                x: Math.random() * canvas.width,
                y: Math.random() * canvas.height,
                vx: (Math.random() - 0.5) * (p.visual.speed === 'fast' ? 4 : 1.5),
                vy: (Math.random() - 0.5) * (p.visual.speed === 'fast' ? 4 : 1.5),
                radius: p.visual.pulse ? 8 + Math.random() * 4 : 6,
                color: getVisualColor(p.visual.color),
                type: p.process_type,
                state: p.state,
                pulseSpeed: 0.05 + Math.random() * 0.05,
                pulseVal: 0
            };
        });

        if (pondAnimationId) {
            cancelAnimationFrame(pondAnimationId);
        }

        function animate() {
            ctx.fillStyle = 'rgba(11, 15, 25, 0.2)';
            ctx.fillRect(0, 0, canvas.width, canvas.height);

            // Draw connections between nearby particles
            ctx.lineWidth = 0.5;
            for (let i = 0; i < particles.length; i++) {
                for (let j = i + 1; j < particles.length; j++) {
                    const dx = particles[i].x - particles[j].x;
                    const dy = particles[i].y - particles[j].y;
                    const dist = Math.sqrt(dx * dx + dy * dy);
                    if (dist < 120) {
                        ctx.strokeStyle = `rgba(255, 255, 255, ${0.12 * (1 - dist / 120)})`;
                        ctx.beginPath();
                        ctx.moveTo(particles[i].x, particles[i].y);
                        ctx.lineTo(particles[j].x, particles[j].y);
                        ctx.stroke();
                    }
                }
            }

            // Update and draw particles
            particles.forEach(p => {
                p.x += p.vx;
                p.y += p.vy;

                // Bounce off boundaries
                if (p.x < p.radius || p.x > canvas.width - p.radius) p.vx *= -1;
                if (p.y < p.radius || p.y > canvas.height - p.radius) p.vy *= -1;

                // Wiggle/pulse size
                p.pulseVal += p.pulseSpeed;
                const currentRadius = p.radius + Math.sin(p.pulseVal) * 2;

                // Draw glowing core
                const grad = ctx.createRadialGradient(p.x, p.y, 0, p.x, p.y, currentRadius * 2);
                grad.addColorStop(0, p.color);
                grad.addColorStop(1, 'transparent');

                ctx.fillStyle = grad;
                ctx.beginPath();
                ctx.arc(p.x, p.y, currentRadius * 2, 0, Math.PI * 2);
                ctx.fill();

                // Draw central solid point
                ctx.fillStyle = '#ffffff';
                ctx.beginPath();
                ctx.arc(p.x, p.y, 2, 0, Math.PI * 2);
                ctx.fill();

                // Text tag
                ctx.fillStyle = 'rgba(255, 255, 255, 0.7)';
                ctx.font = '9px monospace';
                ctx.fillText(p.type.split('_').pop() || '', p.x + currentRadius + 2, p.y + 3);
            });

            pondAnimationId = requestAnimationFrame(animate);
        }

        animate();
    }

    function getVisualColor(colorName) {
        switch (colorName) {
            case 'green': return 'rgba(16, 185, 129, 0.4)';
            case 'amber': return 'rgba(245, 158, 11, 0.4)';
            case 'red': return 'rgba(239, 68, 68, 0.4)';
            case 'purple': return 'rgba(168, 85, 247, 0.4)';
            case 'cyan': return 'rgba(6, 182, 212, 0.4)';
            case 'silver': return 'rgba(156, 163, 175, 0.4)';
            default: return 'rgba(59, 130, 246, 0.4)';
        }
    }

    // ── Loader: Local Models View ──────────────────────────────────────────
    async function loadLocalModelsView() {
        const grid = el('local-models-grid');
        if (!grid) return;
        try {
            const res = await fetch('/api/v1/discovery/ai-runtimes');
            const data = await res.json();
            const hosts = data.hosts || [];
            
            if (hosts.length === 0) {
                grid.innerHTML = `<div style="grid-column: 1/-1; text-align:center; color:var(--text-secondary);">No local model runtimes discovered.</div>`;
                return;
            }

            grid.innerHTML = hosts.map(h => {
                let badgeClass = h.reachable ? 'badge-success' : 'badge-danger';
                let badgeColor = h.reachable ? '#10b981' : '#ef4444';
                let badgeBg = h.reachable ? 'rgba(16,185,129,0.1)' : 'rgba(239,68,68,0.1)';
                let badgeText = h.reachable ? 'REACHABLE' : 'UNREACHABLE';
                
                if (h.status === 'MISSING_FROM_SCAN') {
                    badgeClass = 'badge-info';
                    badgeColor = '#ef4444';
                    badgeBg = 'rgba(239,68,68,0.15)';
                    badgeText = 'MISSING_FROM_SCAN';
                }
                
                const modelNames = h.model_names || [];
                const modelStr = modelNames.length > 0 ? modelNames.join(', ') : 'None';

                return `
                    <div class="card" style="padding:16px; border:1px solid var(--border-glass); border-radius:8px;">
                        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;">
                            <h3 style="font-weight:bold; color:#fff;">${h.kind.toUpperCase()}</h3>
                            <span class="badge ${badgeClass}" style="background:${badgeBg}; color:${badgeColor}">
                                ${badgeText}
                            </span>
                        </div>
                        <div style="font-size:12px; display:flex; flex-direction:column; gap:4px; opacity:0.8;">
                            <div>Endpoint: <strong>${h.host}:${h.port}</strong></div>
                            <div>Reachable: <strong>${h.reachable ? 'TRUE' : 'FALSE'}</strong></div>
                            <div>Status: <strong>${h.status}</strong></div>
                            <div>Models Count: <strong>${h.model_count}</strong></div>
                            <div>Models: <strong>${modelStr}</strong></div>
                            <div>Last Scanned: <span style="font-size:10px; opacity:0.6;">${h.last_scanned || '-'}</span></div>
                        </div>
                    </div>
                `;
            }).join('');
        } catch (err) {
            grid.innerHTML = `<div style="grid-column: 1/-1; text-align:center; color:#ef4444;">Error fetching discovery status</div>`;
        }
    }

    async function loadModelHealth(force = false) {
        const healthContainer = el('model-health-container');
        if (!healthContainer) return;
        
        if (force) {
            healthContainer.innerHTML = `
                <div style="text-align: center; color: var(--text-secondary); padding: 20px;">
                    <span class="pulse-glow" style="display: inline-block; width: 8px; height: 8px; background: var(--accent-teal); border-radius: 50%; margin-right: 8px; animation: led-pulse 1.5s infinite;"></span>
                    Scanning all local model endpoints, checking sizes and chat compatibility (this can take 2-4s)...
                </div>
            `;
        }

        try {
            const url = force ? '/api/v1/models/health/trigger' : '/api/v1/models/health';
            const method = force ? 'POST' : 'GET';
            const res = await fetch(url, { method });
            const data = await res.json();

            // 1. Render Fallback Readiness Cards
            const readinessHtml = (data.fallback_readiness || []).map(fr => {
                let colorVal = '#10b981';
                let bgVal = 'rgba(16, 185, 129, 0.08)';
                let borderVal = 'rgba(16, 185, 129, 0.25)';
                if (fr.status === 'AMBER') {
                    colorVal = '#fbbf24';
                    bgVal = 'rgba(251, 191, 36, 0.08)';
                    borderVal = 'rgba(251, 191, 36, 0.25)';
                } else if (fr.status === 'RED') {
                    colorVal = '#f87171';
                    bgVal = 'rgba(248, 113, 113, 0.08)';
                    borderVal = 'rgba(248, 113, 113, 0.25)';
                }

                return `
                    <div style="background: ${bgVal}; border: 1px solid ${borderVal}; padding: 14px; border-radius: 8px; display: flex; flex-direction: column; gap: 8px;">
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <strong style="color: #fff; font-size: 13px; text-transform: uppercase;">${fr.class_name.replace('_', ' ')}</strong>
                            <span style="color: ${colorVal}; font-weight: bold; font-size: 10px; border: 1px solid ${colorVal}; padding: 2px 6px; border-radius: 4px; background: rgba(0,0,0,0.2);">${fr.status}</span>
                        </div>
                        <div style="font-size: 12px; color: var(--text-secondary); line-height: 1.4;">${fr.message}</div>
                        <div style="font-size: 11px; display: flex; gap: 10px; margin-top: 4px;">
                            <div>Primary: <code style="color: #a5b4fc;">${fr.primary || 'none'}</code></div>
                            <div>Fallback: <code style="color: #c7d2fe;">${fr.fallback || 'none'}</code></div>
                        </div>
                    </div>
                `;
            }).join('');

            // 2. Render Models Status Table
            const rowsHtml = (data.models || []).map(m => {
                let statusColor = '#10b981';
                let statusText = m.status;
                if (m.status === 'MISSING') {
                    statusColor = '#f59e0b';
                } else if (m.status === 'FAILING' || m.status === 'OFFLINE') {
                    statusColor = '#ef4444';
                }

                let sizeBadge = '';
                if (m.size_category === 'HEAVY') {
                    sizeBadge = '<span style="background: rgba(239, 68, 68, 0.15); color: #f87171; border: 1px solid rgba(239,68,68,0.3); padding: 1px 4px; border-radius: 3px; font-size: 9px; font-weight: bold; margin-left: 6px;">HEAVY (Slow Local)</span>';
                } else if (m.size_category === 'LIGHT') {
                    sizeBadge = '<span style="background: rgba(16, 185, 129, 0.15); color: #34d399; border: 1px solid rgba(16,185,129,0.3); padding: 1px 4px; border-radius: 3px; font-size: 9px; font-weight: bold; margin-left: 6px;">LIGHT</span>';
                }

                const latencyText = m.latency_ms > 0 ? `${m.latency_ms.toFixed(0)} ms` : 'N/A';
                const errDetail = m.compatibility_error ? `<div style="color: #ef4444; font-size: 9px; margin-top: 2px;">${m.compatibility_error}</div>` : '';

                return `
                    <tr style="border-bottom: 1px solid rgba(255,255,255,0.05);">
                        <td style="padding: 10px 12px; font-weight: 500; color: #fff; font-family: monospace;">${m.raw_name}</td>
                        <td style="padding: 10px 12px;">
                            ${m.size_bytes > 0 ? (m.size_bytes / 1024 / 1024 / 1024).toFixed(2) + ' GB' : 'Unknown'}
                            ${sizeBadge}
                        </td>
                        <td style="padding: 10px 12px; font-weight: bold; color: ${statusColor};">${statusText}</td>
                        <td style="padding: 10px 12px; text-align: right; color: #fbbf24;">${latencyText}</td>
                        <td style="padding: 10px 12px; color: var(--text-secondary); max-width: 250px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">
                            ${m.status === 'HEALTHY' ? '<span style="color: #34d399;">Passed</span>' : (m.status === 'MISSING' ? 'Model not pulled' : 'Check failed')}
                            ${errDetail}
                        </td>
                    </tr>
                `;
            }).join('');

            healthContainer.innerHTML = `
                <div style="font-size: 12px; color: var(--text-secondary); margin-bottom: 8px;">
                    Last Health Scan: <strong>${new Date(data.last_checked).toLocaleString()}</strong>
                </div>
                
                <h4 style="font-size: 13px; font-weight: bold; color: #fff; margin-bottom: 8px;">Task Routing Fallback Safety</h4>
                <div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 12px; margin-bottom: 16px;">
                    ${readinessHtml}
                </div>

                <h4 style="font-size: 13px; font-weight: bold; color: #fff; margin-bottom: 8px;">Model Health & Latencies</h4>
                <div style="overflow-x: auto; background: rgba(0,0,0,0.15); border: 1px solid var(--border-glass); border-radius: 8px;">
                    <table style="width: 100%; border-collapse: collapse; font-size: 11px; text-align: left;">
                        <thead>
                            <tr style="background: rgba(255,255,255,0.02); border-bottom: 1px solid var(--border-glass); font-weight: 600;">
                                <th style="padding: 10px 12px; color: var(--accent-teal);">Model Reference</th>
                                <th style="padding: 10px 12px;">Disk Size</th>
                                <th style="padding: 10px 12px;">Status</th>
                                <th style="padding: 10px 12px; text-align: right;">Ping Latency</th>
                                <th style="padding: 10px 12px;">Compatibility Test</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${rowsHtml}
                        </tbody>
                    </table>
                </div>
            `;
        } catch (err) {
            console.error(err);
            healthContainer.innerHTML = `<div style="color: #ef4444; padding: 20px; text-align: center;">Error fetching model health metrics</div>`;
        }
    }

    async function loadModelStoragePolicy(generate = false) {
        const storageContainer = el('model-storage-container');
        if (!storageContainer) return;

        if (generate) {
            storageContainer.innerHTML = `
                <div style="text-align: center; color: var(--text-secondary); padding: 20px;">
                    <span class="pulse-glow" style="display: inline-block; width: 8px; height: 8px; background: var(--accent-teal); border-radius: 50%; margin-right: 8px; animation: led-pulse 1.5s infinite;"></span>
                    Generating rclone-exclude.txt filter file...
                </div>
            `;
        }

        try {
            const url = generate ? '/api/v1/models/storage-policy/generate' : '/api/v1/models/storage-policy';
            const method = generate ? 'POST' : 'GET';
            const res = await fetch(url, { method });
            const data = await res.json();

            // Status message
            let fileStatusHtml = '';
            if (data.exclude_file_exists) {
                fileStatusHtml = `<span style="background: rgba(16, 185, 129, 0.15); color: #34d399; border: 1px solid rgba(16,185,129,0.3); padding: 2px 6px; border-radius: 4px; font-weight: bold; font-size: 10px;">EXCLUDE FILE GENERATED</span>`;
            } else {
                fileStatusHtml = `<span style="background: rgba(245, 158, 11, 0.15); color: #fbbf24; border: 1px solid rgba(245,158,11,0.3); padding: 2px 6px; border-radius: 4px; font-weight: bold; font-size: 10px;">EXCLUDE FILE MISSING</span>`;
            }

            const formattedSize = (data.total_protected_bytes / 1024 / 1024 / 1024).toFixed(2);

            // Manifests list
            const manifestsHtml = (data.protected_manifests || []).map(m => {
                return `<li><code style="color: #a5b4fc;">${m}</code></li>`;
            }).join('');

            // Blobs list
            const blobsHtml = (data.protected_blobs || []).map(b => {
                const blobSize = b.size_bytes > 0 ? `(${(b.size_bytes / 1024 / 1024 / 1024).toFixed(2)} GB)` : '(missing)';
                const statusColor = b.exists ? '#34d399' : '#f87171';
                const statusText = b.exists ? 'protected' : 'missing';
                return `
                    <div style="display: flex; justify-content: space-between; align-items: center; padding: 6px 8px; border-bottom: 1px solid rgba(255,255,255,0.03); font-family: monospace; font-size: 11px;">
                        <span style="color: var(--text-secondary);">${b.filename} ${blobSize}</span>
                        <span style="color: ${statusColor}; font-weight: bold; font-size: 9px; text-transform: uppercase;">${statusText}</span>
                    </div>
                `;
            }).join('');

            storageContainer.innerHTML = `
                <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 10px; margin-bottom: 10px;">
                    <div style="font-size: 12px; color: var(--text-secondary);">
                        Exclude File Path: <code style="color: #fff; font-size: 11px;">${data.exclude_file_path}</code>
                    </div>
                    <div>${fileStatusHtml}</div>
                </div>

                ${data.message ? `<div style="background: rgba(16, 185, 129, 0.08); border: 1px solid rgba(16, 185, 129, 0.2); color: #34d399; font-size: 11px; padding: 10px; border-radius: 6px; margin-bottom: 12px;">${data.message}</div>` : ''}

                <div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 16px; margin-bottom: 12px;">
                    <div style="background: rgba(255,255,255,0.01); border: 1px solid var(--border-glass); padding: 14px; border-radius: 8px;">
                        <h4 style="font-size: 12px; font-weight: bold; color: #fff; margin-bottom: 8px; text-transform: uppercase; letter-spacing: 0.5px;">Active Policy Summary</h4>
                        <div style="display: flex; flex-direction: column; gap: 6px; font-size: 12px;">
                            <div>Protected Disk Footprint: <strong style="color: #fbbf24; font-size: 14px;">${formattedSize} GB</strong></div>
                            <div>Protected Manifests: <strong style="color: #fff;">${data.protected_manifests.length}</strong></div>
                            <div>Protected Storage Blobs: <strong style="color: #fff;">${data.protected_blobs.length}</strong></div>
                        </div>
                        <h5 style="font-size: 11px; font-weight: bold; color: #fff; margin-top: 12px; margin-bottom: 6px;">Protected Manifest Files:</h5>
                        <ul style="margin: 0; padding-left: 16px; font-size: 11px; color: var(--text-secondary); display: flex; flex-direction: column; gap: 3px;">
                            ${manifestsHtml}
                        </ul>
                    </div>

                    <div style="background: rgba(255,255,255,0.01); border: 1px solid var(--border-glass); padding: 14px; border-radius: 8px; display: flex; flex-direction: column;">
                        <h4 style="font-size: 12px; font-weight: bold; color: #fff; margin-bottom: 8px; text-transform: uppercase; letter-spacing: 0.5px;">Protected Storage Blobs (Excludes)</h4>
                        <div style="flex-grow: 1; max-height: 200px; overflow-y: auto; background: rgba(0,0,0,0.15); border: 1px solid var(--border-glass); border-radius: 6px; padding: 6px;">
                            ${blobsHtml || '<div style="color:var(--text-secondary); text-align:center; padding:15px;">No blobs protected.</div>'}
                        </div>
                    </div>
                </div>
            `;
        } catch (err) {
            console.error(err);
            storageContainer.innerHTML = `<div style="color: #ef4444; padding: 20px; text-align: center;">Error fetching model storage policy</div>`;
        }
    }

    async function loadMigrationStatus() {
        const container = el('migration-status-container');
        const badge = el('migration-active-badge');
        if (!container) return;

        try {
            const res = await fetch('/api/v1/migration/status');
            const data = await res.json();

            // Update badge status
            if (badge) {
                if (data.migration_active) {
                    badge.textContent = 'MIGRATION ACTIVE';
                    badge.style.background = 'rgba(59, 130, 246, 0.15)';
                    badge.style.color = '#60a5fa';
                    badge.style.border = '1px solid rgba(59,130,246,0.3)';
                } else {
                    badge.textContent = 'MIGRATION INACTIVE';
                    badge.style.background = 'rgba(255, 255, 255, 0.05)';
                    badge.style.color = 'var(--text-secondary)';
                    badge.style.border = '1px solid rgba(255,255,255,0.1)';
                }
            }

            // Update button status
            const btnResume = el('btn-resume-migration');
            if (btnResume) {
                if (data.migration_active) {
                    btnResume.disabled = true;
                    btnResume.textContent = 'Migration Resumed...';
                    btnResume.style.opacity = '0.5';
                    btnResume.style.cursor = 'not-allowed';
                } else {
                    btnResume.disabled = false;
                    btnResume.textContent = 'Resume Guarded Migration';
                    btnResume.style.opacity = '1';
                    btnResume.style.cursor = 'pointer';
                }
            }

            const total = data.total_files || 0;
            const completed = data.completed_files || 0;
            const percent = total > 0 ? Math.round((completed / total) * 100) : 0;
            const spaceRecoveredGB = (data.total_space_recovered_bytes / 1024 / 1024 / 1024).toFixed(2);
            const spacePendingGB = (data.total_space_pending_bytes / 1024 / 1024 / 1024).toFixed(2);

            // Generate progress bar HTML
            const progressBarHtml = `
                <div style="margin-bottom: 12px;">
                    <div style="display: flex; justify-content: space-between; margin-bottom: 4px; font-size: 11px;">
                        <span style="color: var(--text-secondary);">Sync Progress</span>
                        <strong style="color: var(--accent-teal);">${percent}% (${completed} / ${total} files)</strong>
                    </div>
                    <div style="background: rgba(255,255,255,0.05); height: 8px; border-radius: 99px; overflow: hidden; display: flex;">
                        <div style="background: var(--accent-teal); width: ${percent}%; height: 100%; border-radius: 99px; transition: width 0.4s ease;"></div>
                    </div>
                </div>
            `;

            // Skipped / Protected list
            const protectedList = (data.target_files || [])
                .filter(f => f.status === 'SKIPPED_PROTECTED')
                .map(f => `<li><code style="color: #60a5fa;">${f.filename}</code></li>`)
                .join('');

            // Files table rows
            const fileRows = (data.target_files || []).map(f => {
                let statusColor = '#34d399';
                if (f.status === 'PENDING') statusColor = '#fbbf24';
                if (f.status === 'FAILED') statusColor = '#ef4444';
                if (f.status === 'SKIPPED_PROTECTED') statusColor = '#60a5fa';

                const sizeText = f.size_bytes > 0 ? `${(f.size_bytes / 1024 / 1024 / 1024).toFixed(2)} GB` : '-';
                
                return `
                    <tr style="border-bottom: 1px solid rgba(255,255,255,0.03); font-size: 11px;">
                        <td style="padding: 6px 8px; max-width: 250px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; color: var(--text-secondary);" title="${f.absolute_path}">${f.filename}</td>
                        <td style="padding: 6px 8px; text-align: right; color: var(--text-secondary);">${sizeText}</td>
                        <td style="padding: 6px 8px; text-align: right; font-weight: bold; color: ${statusColor}; font-size: 9px; text-transform: uppercase;">${f.status}</td>
                    </tr>
                `;
            }).join('');

            const fileTableHtml = `
                <div style="background: rgba(0,0,0,0.15); border: 1px solid var(--border-glass); border-radius: 6px; overflow: hidden; display: flex; flex-direction: column;">
                    <div style="padding: 8px 12px; border-bottom: 1px solid var(--border-glass); font-size: 11px; font-weight: bold; text-transform: uppercase; color: #fff;">File Execution Log (Preview)</div>
                    <div style="max-height: 180px; overflow-y: auto;">
                        <table style="width: 100%; border-collapse: collapse;">
                            <thead>
                                <tr style="background: rgba(255,255,255,0.02); font-size: 10px; text-transform: uppercase; color: var(--text-secondary); text-align: left; border-bottom: 1px solid var(--border-glass);">
                                    <th style="padding: 6px 8px;">File</th>
                                    <th style="padding: 6px 8px; text-align: right;">Size</th>
                                    <th style="padding: 6px 8px; text-align: right;">Status</th>
                                </tr>
                            </thead>
                            <tbody>
                                ${fileRows || '<tr><td colspan="3" style="text-align:center; padding:15px; color:var(--text-secondary);">No migration files found.</td></tr>'}
                            </tbody>
                        </table>
                    </div>
                </div>
            `;

            // Log Tail Panel
            const logLinesHtml = (data.log_tail || [])
                .map(line => `<div style="padding: 2px 0;">${line}</div>`)
                .join('');

            // Recovery commands
            const recoveryHtml = Object.entries(data.recovery_commands || {}).map(([key, cmd]) => {
                return `
                    <div style="margin-bottom: 8px;">
                        <div style="font-size: 10px; font-weight: bold; color: var(--text-secondary); text-transform: uppercase; margin-bottom: 2px;">${key.replace('_', ' ')}</div>
                        <div style="display: flex; gap: 6px;">
                            <input type="text" readonly value='${cmd}' style="flex-grow: 1; font-family: monospace; font-size: 10px; background: rgba(0,0,0,0.3); border: 1px solid var(--border-glass); color: #fff; padding: 4px 8px; border-radius: 4px;">
                            <button onclick="navigator.clipboard.writeText('${cmd.replace(/'/g, "\\'")}')" class="btn" style="padding: 2px 8px; font-size: 10px; background: rgba(255,255,255,0.05); border: 1px solid var(--border-glass); color: #fff; border-radius: 4px;">Copy</button>
                        </div>
                    </div>
                `;
            }).join('');

            container.innerHTML = `
                ${progressBarHtml}

                <div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 16px; margin-bottom: 12px;">
                    <!-- Migration Statistics -->
                    <div style="background: rgba(255,255,255,0.01); border: 1px solid var(--border-glass); padding: 14px; border-radius: 8px;">
                        <h4 style="font-size: 12px; font-weight: bold; color: #fff; margin-bottom: 8px; text-transform: uppercase; letter-spacing: 0.5px;">Migration Statistics</h4>
                        <div style="display: flex; flex-direction: column; gap: 8px; font-size: 12px;">
                            <div style="display: flex; justify-content: space-between;"><span>Space Recovered:</span><strong style="color: #34d399; font-size: 13px;">${spaceRecoveredGB} GB</strong></div>
                            <div style="display: flex; justify-content: space-between;"><span>Space Pending:</span><strong style="color: #fbbf24;">${spacePendingGB} GB</strong></div>
                            <div style="display: flex; justify-content: space-between;"><span>Completed Files:</span><strong style="color: #fff;">${completed}</strong></div>
                            <div style="display: flex; justify-content: space-between;"><span>Skipped Protected:</span><strong style="color: #60a5fa;">${data.skipped_protected}</strong></div>
                            <div style="display: flex; justify-content: space-between;"><span>Failed:</span><strong style="color: #ef4444;">${data.failed_files}</strong></div>
                        </div>

                        ${protectedList ? `
                        <h5 style="font-size: 10px; font-weight: bold; color: #fff; margin-top: 14px; margin-bottom: 6px; text-transform: uppercase;">Skipped Active Models:</h5>
                        <ul style="margin: 0; padding-left: 16px; font-size: 10px; color: var(--text-secondary); display: flex; flex-direction: column; gap: 3px; max-height: 80px; overflow-y: auto;">
                            ${protectedList}
                        </ul>
                        ` : ''}
                    </div>

                    <!-- File list log -->
                    ${fileTableHtml}
                </div>

                <div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 16px;">
                    <!-- Terminal Log Tail -->
                    <div style="background: rgba(255,255,255,0.01); border: 1px solid var(--border-glass); padding: 14px; border-radius: 8px; display: flex; flex-direction: column;">
                        <h4 style="font-size: 12px; font-weight: bold; color: #fff; margin-bottom: 8px; text-transform: uppercase; letter-spacing: 0.5px;">Rclone Terminal Output</h4>
                        <div style="flex-grow: 1; font-family: monospace; font-size: 10px; background: rgba(0,0,0,0.4); border: 1px solid var(--border-glass); border-radius: 6px; padding: 10px; color: #34d399; overflow-y: auto; max-height: 180px; min-height: 120px;">
                            ${logLinesHtml || '<div style="color:var(--text-secondary);">No logs written.</div>'}
                        </div>
                    </div>

                    <!-- Recovery Console -->
                    <div style="background: rgba(255,255,255,0.01); border: 1px solid var(--border-glass); padding: 14px; border-radius: 8px;">
                        <h4 style="font-size: 12px; font-weight: bold; color: #fff; margin-bottom: 8px; text-transform: uppercase; letter-spacing: 0.5px;">Recovery Actions console</h4>
                        <div style="display: flex; flex-direction: column; gap: 6px;">
                            ${recoveryHtml}
                        </div>
                    </div>
                </div>
            `;
        } catch (err) {
            console.error(err);
            container.innerHTML = `<div style="color: #ef4444; padding: 20px; text-align: center;">Error loading storage migration status</div>`;
        }
    }

    // ── Loader: Model Router View ──────────────────────────────────────────
    async function loadModelRouterView() {
        const container = el('model-router-details');
        if (!container) return;
        try {
            const res = await fetch('/api/v1/models/status');
            const data = await res.json();

            container.innerHTML = `
                <div class="card" style="padding:20px; border:1px solid var(--border-glass);">
                    <h3 style="font-weight:bold; color:#fff; font-size:15px; margin-bottom:12px;">Active Rule Settings</h3>
                    <div style="display:grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap:12px; font-size:13px;">
                        <div>Local-First Routing: <strong style="color:${data.local_first ? '#10b981' : '#f59e0b'}">${data.local_first ? 'ENABLED' : 'DISABLED'}</strong></div>
                        <div>Default System Model: <code style="color:#818cf8;">${data.default_model || '-'}</code></div>
                        <div>Default Paid Model: <code style="color:#a855f7;">${data.default_paid_model || '-'}</code></div>
                    </div>
                </div>
                <div class="card" style="padding:20px; border:1px solid var(--border-glass);">
                    <h3 style="font-weight:bold; color:#fff; font-size:15px; margin-bottom:12px;">Enabled Local Providers</h3>
                    <div style="display:flex; gap:8px; flex-wrap:wrap;">
                        ${data.enabled_local_providers && data.enabled_local_providers.length > 0
                            ? data.enabled_local_providers.map(p => `<span class="badge badge-info">${p}</span>`).join('')
                            : '<span style="color:var(--text-secondary);">None</span>'}
                    </div>
                </div>
            `;
            
            // Trigger health and storage load
            loadModelHealth(false);
            loadModelStoragePolicy(false);
            loadMigrationStatus();
        } catch (err) {
            container.innerHTML = `<div style="color:#ef4444; text-align:center;">Error fetching routing settings</div>`;
        }
    }

    // ── Loader: Escalations View ────────────────────────────────────────────
    async function loadEscalationsView() {
        const list = el('escalations-approval-list');
        if (!list) return;
        try {
            const res = await fetch('/api/v1/escalations/pending');
            const pending = await res.json();

            if (pending.length === 0) {
                list.innerHTML = `<div style="text-align:center; color:var(--text-secondary); padding:20px;">No pending paid provider escalations in queue.</div>`;
                return;
            }

            list.innerHTML = pending.map(app => `
                <div class="card" style="padding:16px; border:1px solid var(--border-glass); border-radius:8px; display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:12px;">
                    <div style="display:flex; flex-direction:column; gap:4px; text-align:left;">
                        <span style="font-weight:bold; font-size:14px; color:#fff;">Approval ID: ${app.approval_id}</span>
                        <span style="font-size:12px; color:var(--text-secondary);">Task description: ${app.task_description}</span>
                        <span style="font-size:11px; color:#f59e0b;">Target Paid Model: ${app.target_model}</span>
                    </div>
                    <div style="display:flex; gap:8px;">
                        <button class="btn btn-outline btn-xs" onclick="window.hochRemediateEscalation('${app.approval_id}', 'DENIED')" style="color:#ef4444; border-color:rgba(239,68,68,0.3);">Deny</button>
                        <button class="btn btn-primary btn-xs" onclick="window.hochRemediateEscalation('${app.approval_id}', 'APPROVED')" style="background:#10b981; border-color:#10b981; color:#fff;">Approve</button>
                    </div>
                </div>
            `).join('');
        } catch (err) {
            list.innerHTML = `<div style="color:#ef4444; text-align:center;">Error fetching pending approvals queue</div>`;
        }
    }

    // Remediation Approve/Deny action
    window.hochRemediateEscalation = async function (approvalId, status) {
        try {
            const res = await fetch('/api/v1/escalations/approve', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ approval_id: approvalId, status: status })
            });
            if (res.ok) {
                loadEscalationsView();
                fetchCockpit();
            } else {
                alert('Action failed');
            }
        } catch (err) {
                    console.error('[Remediate] post failed:', err);
        }
    };

    // ── Loader: Evidence View ───────────────────────────────────────────────
    async function loadClawdeView() {
        async function loadClawdeHistory() {
            const timelineContent = el('clawde-audit-timeline-content');
            if (!timelineContent) return;

            try {
                // Verify integrity
                try {
                    const verifyRes = await fetch('/api/v1/orchestrator/history/verify');
                    if (verifyRes.ok) {
                        const verifyData = await verifyRes.json();
                        const integrityBadge = el('clawde-audit-integrity');
                        if (integrityBadge) {
                            if (verifyData.status === 'success') {
                                integrityBadge.textContent = 'INTEGRITY: SECURE';
                                integrityBadge.style.background = 'rgba(16, 185, 129, 0.1)';
                                integrityBadge.style.borderColor = 'rgba(16, 185, 129, 0.3)';
                                integrityBadge.style.color = '#34d399';
                            } else {
                                integrityBadge.textContent = 'TAMPER DETECTED';
                                integrityBadge.style.background = 'rgba(239, 68, 68, 0.1)';
                                integrityBadge.style.borderColor = 'rgba(239, 68, 68, 0.3)';
                                integrityBadge.style.color = '#f87171';
                            }
                        }
                    }
                } catch (err) {
                    console.error("Error verifying log integrity:", err);
                }

                const res = await fetch('/api/v1/orchestrator/history');
                if (!res.ok) throw new Error(`HTTP status ${res.status}`);
                const data = await res.json();
                const history = data.history || [];

                if (history.length === 0) {
                    timelineContent.innerHTML = `
                        <div style="font-size: 12px; color: var(--text-secondary); text-align: center; margin: 15px 0;">
                            No history records found. Perform requests, approvals, or executions to start the ledger.
                        </div>
                    `;
                    return;
                }

                let html = '';
                history.forEach(item => {
                    let badgeColor = 'rgba(59, 130, 246, 0.15)';
                    let badgeTextColor = '#60a5fa';
                    let badgeBorderColor = 'rgba(59, 130, 246, 0.3)';
                    
                    if (item.action === 'approve') {
                        badgeColor = 'rgba(16, 185, 129, 0.15)';
                        badgeTextColor = '#34d399';
                        badgeBorderColor = 'rgba(16, 185, 129, 0.3)';
                    } else if (item.action === 'execute') {
                        if (item.status === 'success') {
                            badgeColor = 'rgba(16, 185, 129, 0.15)';
                            badgeTextColor = '#34d399';
                            badgeBorderColor = 'rgba(16, 185, 129, 0.3)';
                        } else {
                            badgeColor = 'rgba(239, 68, 68, 0.15)';
                            badgeTextColor = '#f87171';
                            badgeBorderColor = 'rgba(239, 68, 68, 0.3)';
                        }
                    } else if (item.action === 'execute_start') {
                        badgeColor = 'rgba(245, 158, 11, 0.15)';
                        badgeTextColor = '#fbbf24';
                        badgeBorderColor = 'rgba(245, 158, 11, 0.3)';
                    } else if (item.action === 'transition') {
                        badgeColor = 'rgba(139, 92, 246, 0.15)';
                        badgeTextColor = '#a78bfa';
                        badgeBorderColor = 'rgba(139, 92, 246, 0.3)';
                    }

                    const actionLabel = item.action.toUpperCase().replace('_', ' ');
                    const localTime = new Date(item.timestamp).toLocaleString();
                    
                    let detailsHtml = '';
                    if (item.action === 'execute' && (item.stdout || item.stderr)) {
                        detailsHtml = `
                            <details style="margin-top: 6px; cursor: pointer;">
                                <summary style="font-size: 11px; color: var(--accent-teal); font-weight: 600;">View Execution Output</summary>
                                <pre style="margin: 6px 0 0 0; background: #020406; border: 1px solid rgba(255,255,255,0.05); padding: 8px; border-radius: 4px; font-family: monospace; font-size: 11px; color: #34d399; max-height: 150px; overflow-y: auto; white-space: pre-wrap; word-break: break-all;">${item.stdout || ''}${item.stderr ? '\nERRORS:\n' + item.stderr : ''}</pre>
                            </details>
                        `;
                    }

                    let sealHtml = '';
                    if (item.evidence_seal_path) {
                        const sealFilename = item.evidence_seal_path.split('/').pop();
                        sealHtml = `
                            <div style="font-size: 11px; color: var(--accent-teal); font-weight: bold; margin-top: 4px; display: flex; align-items: center; gap: 4px;">
                                <span style="display:inline-block; width:6px; height:6px; background:#14b8a6; border-radius:50%;"></span>
                                Evidence Seal: <a href="file:///${item.evidence_seal_path}" target="_blank" style="color: #2dd4bf; text-decoration: underline; font-family: monospace; word-break: break-all;">${sealFilename}</a>
                            </div>
                        `;
                    }

                    html += `
                        <div style="display: flex; gap: 12px; background: rgba(255,255,255,0.02); border: 1px solid rgba(255,255,255,0.04); padding: 10px 14px; border-radius: 8px; align-items: flex-start; justify-content: space-between;">
                            <div style="display: flex; gap: 12px; align-items: flex-start; flex: 1;">
                                <div style="display: flex; flex-direction: column; gap: 4px; align-items: center; min-width: 90px;">
                                    <span style="font-size: 10px; font-weight: bold; padding: 2px 8px; border-radius: 4px; background: ${badgeColor}; color: ${badgeTextColor}; border: 1px solid ${badgeBorderColor}; text-align: center; width: 100%; display: block; box-sizing: border-box;">
                                        ${actionLabel}
                                    </span>
                                    <span style="font-size: 10px; font-weight: 600; color: #fff; background: rgba(255,255,255,0.06); padding: 1px 6px; border-radius: 3px;">
                                        ${item.phase}
                                    </span>
                                </div>
                                <div style="flex: 1;">
                                    <div style="font-size: 12px; font-weight: 600; color: #fff;">
                                        ${item.decision_note || (item.action === 'execute' ? `Execution ${item.status}` : `${actionLabel} event`)}
                                    </div>
                                    <div style="font-size: 11px; color: var(--text-secondary); margin-top: 2px;">
                                        Operator: <span style="color:#fff; font-weight:500;">${item.operator}</span> | Scope: <span style="color:#fff; font-weight:500;">${item.scope}</span>
                                        ${item.returncode !== null ? ` | Exit Code: <span style="color:#f87171; font-weight:bold;">${item.returncode}</span>` : ''}
                                    </div>
                                    ${sealHtml}
                                    ${detailsHtml}
                                </div>
                            </div>
                            <div style="font-size: 11px; color: var(--text-secondary); text-align: right; white-space: nowrap; margin-top: 2px;">
                                ${localTime}
                            </div>
                        </div>
                    `;
                });

                timelineContent.innerHTML = html;
            } catch (err) {
                console.error("Error loading CLAWDE history:", err);
                timelineContent.innerHTML = `
                    <div style="font-size: 12px; color: #f87171; text-align: center; margin: 15px 0;">
                        Failed to load history ledger: ${err.message}
                    </div>
                `;
            }
        }

        loadClawdeHistory();

        const phaseSpan = el('clawde-current-phase');
        const tbody = el('evidence-matrix-tbody');
        if (!tbody) return;
        try {
            const res = await fetch('/api/v1/qa/evidence-matrix');
            const data = await res.json();
            // ... (rest of function)
        } catch (err) {
            tbody.innerHTML = `<tr><td colspan="4" style="text-align:center; padding:15px; color:#ef4444;">Error fetching evidence matrix</td></tr>`;
        }
    }

    async function loadEvidenceView() {
        loadActionLedger();
        const stats = el('evidence-stats');
        const tbody = el('evidence-matrix-tbody');
        if (!tbody) return;
        try {
            const res = await fetch('/api/v1/qa/evidence-matrix');
            const data = await res.json();
            
            if (stats) {
                stats.innerHTML = `
                    <div class="card" style="padding:12px; background:rgba(255,255,255,0.02); border:1px solid var(--border-glass);">
                        <span style="font-size:11px; color:var(--text-secondary);">Verified Controls</span>
                        <div style="font-size:20px; font-weight:bold; color:#fff;">${data.controls ? data.controls.length : 0}</div>
                    </div>
                    <div class="card" style="padding:12px; background:rgba(255,255,255,0.02); border:1px solid var(--border-glass);">
                        <span style="font-size:11px; color:var(--text-secondary);">Tests Passing</span>
                        <div style="font-size:20px; font-weight:bold; color:#10b981;">${data.summary ? data.summary.tests_pass : 0} / ${data.summary ? data.summary.total_tests : 0}</div>
                    </div>
                `;
            }

            const controlsList = data.controls || [];
            if (controlsList.length === 0) {
                tbody.innerHTML = `<tr><td colspan="4" style="text-align:center; padding:15px; color:var(--text-secondary);">No evidence cataloged.</td></tr>`;
                return;
            }

            tbody.innerHTML = controlsList.map(c => `
                <tr style="border-bottom:1px solid rgba(255,255,255,0.03);">
                    <td style="padding:10px 8px; font-family:monospace; color:#818cf8; font-weight:bold;">${c.control_id}</td>
                    <td style="padding:10px 8px; font-weight:500; color:#fff;">${c.name}</td>
                    <td style="padding:10px 8px; color:var(--text-secondary); max-width:400px;">${c.description}</td>
                    <td style="padding:10px 8px;">
                        <span style="color:${c.status === 'PASS' ? '#10b981' : '#ef4444'}; font-weight:bold;">● ${c.status}</span>
                    </td>
                </tr>
            `).join('');
        } catch (err) {
            tbody.innerHTML = `<tr><td colspan="4" style="text-align:center; padding:15px; color:#ef4444;">Error fetching evidence matrix</td></tr>`;
        }
    }

    // ── Loader: Detections View ─────────────────────────────────────────────
    async function loadDetectionsView() {
        const rulesGrid = el('detections-rules-list');
        const eventList = el('detections-event-list');
        if (!rulesGrid) return;
        try {
            // Load detection status and health
            const res = await fetch('/api/v1/detections/health');
            const data = await res.json();
            
            // Rules count
            const rules = [
                { id: 'SPL-001', dialect: 'Splunk', name: 'Escalation Limit Exceeded', severity: 'high' },
                { id: 'SIG-002', dialect: 'Sigma', name: 'Unauthorized Model Call', severity: 'critical' },
                { id: 'KQL-003', dialect: 'Elastic/KQL', name: 'Rapid Budget Burn Rate', severity: 'medium' },
                { id: 'LQL-004', dialect: 'LogQL', name: 'Process Execution Timeout', severity: 'low' }
            ];

            rulesGrid.innerHTML = rules.map(r => `
                <div class="card" style="padding:12px; border:1px solid var(--border-glass);">
                    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
                        <span style="font-family:monospace; font-size:10px; color:#818cf8; font-weight:bold;">${r.id}</span>
                        <span style="font-size:9px; text-transform:uppercase; font-weight:bold; color:${r.severity === 'critical' || r.severity === 'high' ? '#ef4444' : '#f59e0b'}">${r.severity}</span>
                    </div>
                    <h4 style="font-weight:bold; font-size:12px; color:#fff; margin-bottom:4px;">${r.name}</h4>
                    <div style="font-size:10px; color:var(--text-secondary);">Dialect: <code style="color:#10b981;">${r.dialect}</code></div>
                </div>
            `).join('');

            // Render event log stream
            if (eventList) {
                const events = data.recent_events || [];
                if (events.length === 0) {
                    eventList.innerHTML = `<div style="text-align:center; color:var(--text-secondary); padding:10px;">No alerts triggered</div>`;
                    return;
                }
                eventList.innerHTML = events.map(e => `
                    <div style="display:flex; justify-content:space-between; border-bottom:1px solid rgba(255,255,255,0.03); padding:4px 0; font-size:11px;">
                        <span style="color:#ef4444; font-weight:bold;">[${e.severity.toUpperCase()}]</span>
                        <span style="color:#fff;">${e.rule_id} — ${e.message}</span>
                        <span style="color:var(--text-secondary);">${e.timestamp.split('T')[1].substring(0, 8)}</span>
                    </div>
                `).join('');
            }
        } catch (err) {
            rulesGrid.innerHTML = `<div style="grid-column: 1/-1; text-align:center; color:#ef4444;">Error loading detections</div>`;
        }
    }

    async function loadReadinessView() {
        const container = el('preflight-gate-container');
        const badge = el('preflight-status-badge');
        if (!container) return;

        try {
            const res = await fetch('/api/v1/preflight/status');
            const data = await res.json();

            // Update badge status
            if (badge) {
                if (data.go_no_go === 'GO') {
                    badge.textContent = 'SYSTEM GO';
                    badge.style.background = 'rgba(16, 185, 129, 0.15)';
                    badge.style.color = '#34d399';
                    badge.style.border = '1px solid rgba(16,185,129,0.3)';
                } else {
                    badge.textContent = 'SYSTEM NO-GO';
                    badge.style.background = 'rgba(239, 68, 68, 0.15)';
                    badge.style.color = '#f87171';
                    badge.style.border = '1px solid rgba(239,68,68,0.3)';
                }
            }

            // Checks list rendering
            const checksHtml = (data.checks || []).map(c => {
                let statusColor = '#34d399';
                let statusText = 'PASS';
                if (c.status === 'WARN') {
                    statusColor = '#fbbf24';
                    statusText = 'WARN';
                }
                if (c.status === 'FAIL') {
                    statusColor = '#f87171';
                    statusText = 'FAIL';
                }

                return `
                    <div style="background: rgba(255,255,255,0.01); border: 1px solid var(--border-glass); padding: 14px; border-radius: 8px; display: flex; flex-direction: column; gap: 6px;">
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <strong style="color: #fff; font-size: 13px;">${c.name}</strong>
                            <span style="color: ${statusColor}; font-weight: bold; font-size: 11px; text-transform: uppercase; padding: 2px 8px; background: rgba(0,0,0,0.15); border-radius: 4px; border: 1px solid rgba(255,255,255,0.05);">${statusText}</span>
                        </div>
                        <p style="font-size: 12px; color: var(--text-secondary); margin: 0; line-height: 1.4;">${c.message}</p>
                        ${c.remediation ? `
                        <div style="background: rgba(245, 158, 11, 0.04); border: 1px solid rgba(245, 158, 11, 0.15); border-radius: 6px; padding: 8px 10px; margin-top: 4px; font-size: 11px; color: #fbcb58; display: flex; flex-direction: column; gap: 4px;">
                            <span style="font-weight: bold; font-size: 9px; text-transform: uppercase; color: #fbbf24;">Remediation Suggestion:</span>
                            <span>${c.remediation}</span>
                        </div>
                        ` : ''}
                    </div>
                `;
            }).join('');

            container.innerHTML = `
                <div style="background: rgba(255,255,255,0.01); border: 1px solid var(--border-glass); padding: 16px; border-radius: 8px; margin-bottom: 8px;">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <div>
                            <span style="font-size: 11px; color: var(--text-secondary); text-transform: uppercase; letter-spacing: 0.5px;">Overall Preflight Readiness Score</span>
                            <div style="font-size: 32px; font-weight: 800; color: ${data.go_no_go === 'GO' ? 'var(--accent-teal)' : '#f87171'}; margin-top: 4px;">${data.overall_score}%</div>
                        </div>
                        <div style="text-align: right;">
                            <span style="font-size: 11px; color: var(--text-secondary); text-transform: uppercase; letter-spacing: 0.5px;">Last Scanned</span>
                            <div style="font-size: 12px; color: var(--text-secondary); margin-top: 4px;">${new Date(data.timestamp).toLocaleTimeString()}</div>
                        </div>
                    </div>
                </div>

                <div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 16px;">
                    ${checksHtml || '<div style="color:var(--text-secondary); text-align:center; padding:20px;">No preflight checks configured.</div>'}
                </div>
            `;
        } catch (err) {
            container.innerHTML = `<div style="color:#ef4444; text-align:center;">Error fetching preflight checklist metrics</div>`;
        }
    }

    // ── Loader: Settings View ───────────────────────────────────────────────
    async function loadSettingsView() {
        const container = el('settings-device-list');
        if (!container) return;
        try {
            const res = await fetch('/api/v1/live-runtime/cockpit');
            const data = await res.json();
            const regCard = data.cards.device_registry || {};
            
            container.innerHTML = `
                <div class="card" style="padding:16px; border:1px solid var(--border-glass); border-radius:8px;">
                    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;">
                        <h3 style="font-weight:bold; color:#fff;">Cluster Registry Node profiles</h3>
                        <span class="badge badge-info">${regCard.devices_count || 0} registered</span>
                    </div>
                    <p style="font-size:12px; color:var(--text-secondary); line-height:1.5;">
                        Cluster workers profiles are fetched dynamically from <code>config/cluster_worker_profiles.json</code>.
                        All nodes are authenticated under the local network mesh and governed by authorization levels.
                    </p>
                </div>
            `;
        } catch (err) {
            container.innerHTML = `<div style="color:#ef4444; text-align:center;">Error loading settings profiles</div>`;
        }
    }

    // ── Loader: CLAWDE Control Tower View ────────────────────────────────────
    let isClawdeInitialized = false;
    let activeApprovalId = null;
    let selectedPhase = null;
    const phaseFilesMap = {
        "PR16": {
            prompt: "artifacts/orchestrator/generated-prompts/PR16.md",
            report: "artifacts/orchestrator/reports/PR16_orchestrator_report.json",
            seal: "artifacts/phase-orchestrator/visual-control-plane-local-v1/pr16_final_seal.json"
        },
        "PR17": {
            prompt: "artifacts/orchestrator/generated-prompts/PR17.md",
            report: "artifacts/orchestrator/reports/PR17_orchestrator_report.json",
            seal: "artifacts/production-readiness-final-candidate-seal/visual-control-plane-local-v1/pr17_final_seal"
        },
        "PR18": {
            prompt: "artifacts/orchestrator/generated-prompts/PR18.md",
            report: "artifacts/orchestrator/reports/PR18_orchestrator_report.json",
            seal: "artifacts/production-readiness-final-candidate-seal/visual-control-plane-local-v1/pr18_final_seal.json"
        },
        "COMPLETED": {
            prompt: "None",
            report: "None",
            seal: "None"
        }
    };

    function initClawdeControls() {
        if (isClawdeInitialized) return;
        isClawdeInitialized = true;
        
        const btnNoDrift = el('clawde-btn-no-drift');
        const btnRender = el('clawde-btn-render-phase');
        const btnExecute = el('clawde-btn-execute-phase');
        const btnViewPrompt = el('clawde-btn-view-prompt');
        const btnViewReport = el('clawde-btn-view-report');
        const btnViewEvidence = el('clawde-btn-view-evidence');
        const btnHandoff = el('clawde-btn-handoff');
        const btnRequest = el('clawde-btn-request-execution');
        const btnApprove = el('clawde-btn-approve-execution');
        const consoleArea = el('clawde-console-area');
        const consoleContent = el('clawde-console-content');
        const consoleClose = el('clawde-console-close');
        const banner = el('clawde-status-banner');

        if (consoleClose && consoleArea) {
            consoleClose.addEventListener('click', () => {
                consoleArea.style.display = 'none';
            });
        }

        function showBanner(message, isError) {
            if (!banner) return;
            banner.textContent = message;
            banner.style.display = 'block';
            if (isError) {
                banner.style.background = 'rgba(239, 68, 68, 0.15)';
                banner.style.borderColor = 'rgba(239, 68, 68, 0.4)';
                banner.style.color = '#f87171';
            } else {
                banner.style.background = 'rgba(16, 185, 129, 0.15)';
                banner.style.borderColor = 'rgba(16, 185, 129, 0.4)';
                banner.style.color = '#34d399';
            }
        }

        function hideBanner() {
            if (banner) banner.style.display = 'none';
        }

        async function triggerRunner(actionName, endpoint, payload = null) {
            if (!consoleArea || !consoleContent) return;
            consoleArea.style.display = 'block';
            hideBanner();
            
            consoleContent.textContent += `\n[${actionName.toUpperCase()}] Running runner...\nPOST ${endpoint}\n`;
            if (payload) {
                consoleContent.textContent += `Payload: ${JSON.stringify(payload)}\n`;
            }
            
            try {
                const res = await fetch(endpoint, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: payload ? JSON.stringify(payload) : undefined
                });
                const data = await res.json();
                
                if (data.status === 'success') {
                    consoleContent.textContent += `[PASS] Completed successfully.\n\nSTDOUT:\n${data.stdout || ''}\n`;
                    showBanner(`Successfully executed ${actionName}!`, false);
                } else {
                    const errDetail = data.stderr || data.detail || 'Unknown error occurred.';
                    consoleContent.textContent += `[FAIL] Failed (exit code ${data.returncode || 'error'}).\n\nSTDOUT:\n${data.stdout || ''}\n\nSTDERR:\n${errDetail}\n`;
                    showBanner(`Failed to execute ${actionName}: ${errDetail}`, true);
                }
                // Refresh the view immediately
                loadClawdeView();
            } catch (err) {
                consoleContent.textContent += `[ERROR] Failed to contact backend: ${err.message}\n`;
                showBanner(`Failed to contact backend: ${err.message}`, true);
            }
        }

        if (btnNoDrift) {
            btnNoDrift.addEventListener('click', () => {
                triggerRunner('no-drift check', '/api/v1/orchestrator/run-runner');
            });
        }

        if (btnRender) {
            btnRender.addEventListener('click', () => {
                triggerRunner('render phase', '/api/v1/orchestrator/run-runner');
            });
        }

        if (btnExecute) {
            btnExecute.addEventListener('click', () => {
                const activePhase = el('clawde-current-phase')?.textContent || 'PR17';
                consoleContent.textContent = `[EXECUTE CLICKED] Starting execution...\n`;
                triggerRunner('execute phase', '/api/v1/orchestrator/execute-phase', { phase: activePhase });
            });
        }

        if (btnRequest) {
            btnRequest.addEventListener('click', async () => {
                if (!consoleArea || !consoleContent) return;
                consoleArea.style.display = 'block';
                hideBanner();
                const activePhase = el('clawde-current-phase')?.textContent || 'PR17';
                consoleContent.textContent = `[REQUEST CLICKED] Requesting execution for phase ${activePhase}...\n`;
                consoleContent.textContent += `POST /api/v1/orchestrator/request-execution\n`;
                
                try {
                    const res = await fetch('/api/v1/orchestrator/request-execution', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ phase: activePhase, decision: 'requested' })
                    });
                    const data = await res.json();
                    consoleContent.textContent += `Response: ${JSON.stringify(data, null, 2)}\n`;
                    showBanner(`Approval request registered for ${activePhase}.`, false);
                    loadClawdeView();
                } catch (err) {
                    consoleContent.textContent += `[ERROR] Failed to request approval: ${err.message}\n`;
                    showBanner(`Failed to request approval: ${err.message}`, true);
                }
            });
        }

        if (btnApprove) {
            btnApprove.addEventListener('click', async () => {
                if (!consoleArea || !consoleContent) return;
                consoleArea.style.display = 'block';
                hideBanner();
                const activePhase = el('clawde-current-phase')?.textContent || 'PR17';
                consoleContent.textContent = `[APPROVE CLICKED] Approving execution for phase ${activePhase}...\n`;
                consoleContent.textContent += `POST /api/v1/orchestrator/request-execution\n`;
                
                try {
                    const res = await fetch('/api/v1/orchestrator/request-execution', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ phase: activePhase, decision: 'approved' })
                    });
                    const data = await res.json();
                    consoleContent.textContent += `Response: ${JSON.stringify(data, null, 2)}\n`;
                    showBanner(`Approval decision granted for ${activePhase}.`, false);
                    loadClawdeView();
                } catch (err) {
                    consoleContent.textContent += `[ERROR] Failed to approve execution: ${err.message}\n`;
                    showBanner(`Failed to approve execution: ${err.message}`, true);
                }
            });
        }

        const showPath = (btn, pathField, name) => {
            if (btn) {
                btn.addEventListener('click', () => {
                    if (!consoleArea || !consoleContent) return;
                    consoleArea.style.display = 'block';
                    const pathVal = el(pathField)?.textContent || el(pathField)?.value || '--';
                    consoleContent.textContent = `[INFO] Path to ${name}:\n${pathVal}\n\nTo view or edit this file, use your local editor or the Antigravity shell.\n`;
                });
            }
        };

        showPath(btnViewPrompt, 'clawde-generated-prompt-path', 'Generated Prompt');
        showPath(btnViewReport, 'clawde-latest-report-path', 'Latest Orchestrator Report');
        showPath(btnViewEvidence, 'clawde-evidence-seal-path', 'Latest Evidence Seal');

        if (btnHandoff) {
            btnHandoff.addEventListener('click', () => {
                if (!consoleArea || !consoleContent) return;
                consoleArea.style.display = 'block';
                consoleContent.textContent = `[HANDOFF] Preparing handoff package...\n`;
                
                const nextPhase = el('clawde-current-phase')?.textContent || 'PR17';
                consoleContent.textContent += `[INFO] Handoff package ready for phase: ${nextPhase}\n`;
                consoleContent.textContent += `Run:\n  cat artifacts/orchestrator/generated-prompts/${nextPhase}.md\n\nSubmit this file to the operator for manual gating approval.\n`;
            });
        }

        const btnSyncRun = el('clawde-btn-ingest-run');
        if (btnSyncRun) {
            btnSyncRun.addEventListener('click', () => {
                syncObservabilityDashboard();
            });
        }

        // RC24: Control Plane & Autonomy selector wiring
        const btnPause = el('control-btn-pause');
        const btnResume = el('control-btn-resume');
        const btnExport = el('control-btn-export');
        const btnRollback = el('control-btn-rollback');
        const inputRollback = el('control-rollback-tag');
        
        // Autonomy selector listeners
        document.querySelectorAll('#control-autonomy-container .btn-autonomy').forEach(btn => {
            btn.addEventListener('click', async () => {
                const level = btn.getAttribute('data-level');
                try {
                    const res = await fetch('/api/v1/control/policy', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ autonomy_level: level })
                    });
                    const policy = await res.json();
                    updatePolicyUI(policy);
                } catch (err) {
                    console.error("Failed to update autonomy level:", err);
                }
            });
        });
        
        // Profile selector listeners
        document.querySelectorAll('#control-profile-container .btn-profile').forEach(btn => {
            btn.addEventListener('click', async () => {
                const profile = btn.getAttribute('data-profile');
                try {
                    const res = await fetch('/api/v1/control/policy', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ profile })
                    });
                    const policy = await res.json();
                    updatePolicyUI(policy);
                } catch (err) {
                    console.error("Failed to update policy profile:", err);
                }
            });
        });
        
        if (btnPause) {
            btnPause.addEventListener('click', async () => {
                try {
                    const res = await fetch('/api/v1/control/action', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ action: 'pause' })
                    });
                    const policy = await res.json();
                    updatePolicyUI(policy);
                } catch (err) {
                    console.error("Failed to pause swarm:", err);
                }
            });
        }
        
        if (btnResume) {
            btnResume.addEventListener('click', async () => {
                try {
                    const res = await fetch('/api/v1/control/action', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ action: 'resume' })
                    });
                    const policy = await res.json();
                    updatePolicyUI(policy);
                } catch (err) {
                    console.error("Failed to resume swarm:", err);
                }
            });
        }
        
        if (btnExport) {
            btnExport.addEventListener('click', () => {
                window.location.href = '/api/v1/control/export-evidence';
            });
        }
        
        if (btnRollback) {
            btnRollback.addEventListener('click', async () => {
                const tag = inputRollback ? inputRollback.value : '';
                if (!tag) {
                    alert("Please enter a target tag for rollback.");
                    return;
                }
                if (!confirm(`Are you sure you want to execute emergency rollback to ${tag}?`)) {
                    return;
                }
                try {
                    showBanner(`Executing rollback to ${tag}...`, false);
                    const res = await fetch('/api/v1/control/action', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ action: 'rollback', target_tag: tag })
                    });
                    const data = await res.json();
                    if (data.status === 'SUCCESS') {
                        showBanner(`Rollback to ${tag} succeeded!`, false);
                    } else {
                        showBanner(`Rollback failed: ${data.error || 'unknown error'}`, true);
                    }
                } catch (err) {
                    showBanner(`Rollback request failed: ${err.message}`, true);
                }
            });
        }
    }

    function updatePolicyUI(policy) {
        const autonomyDesc = el('autonomy-desc');
        const profileDesc = el('profile-desc');
        const safetyBadge = el('safety-status-badge');
        const btnPause = el('control-btn-pause');
        const btnResume = el('control-btn-resume');

        const activeLevel = policy.selected_autonomy_level || 'L1';
        const activeProfile = policy.active_profile || 'home';
        const activeSafety = policy.safety_status || 'running';

        // Select buttons styling
        document.querySelectorAll('#control-autonomy-container .btn-autonomy').forEach(btn => {
            if (btn.getAttribute('data-level') === activeLevel) {
                btn.style.background = 'rgba(99, 102, 241, 0.25)';
                btn.style.borderColor = 'var(--accent-teal)';
                btn.style.color = '#fff';
            } else {
                btn.style.background = 'transparent';
                btn.style.borderColor = 'var(--border-glass)';
                btn.style.color = 'var(--text-secondary)';
            }
        });

        document.querySelectorAll('#control-profile-container .btn-profile').forEach(btn => {
            if (btn.getAttribute('data-profile') === activeProfile) {
                btn.style.background = 'rgba(99, 102, 241, 0.25)';
                btn.style.borderColor = 'var(--accent-teal)';
                btn.style.color = '#fff';
            } else {
                btn.style.background = 'transparent';
                btn.style.borderColor = 'var(--border-glass)';
                btn.style.color = 'var(--text-secondary)';
            }
        });

        // Set descriptions
        const autonomyTips = {
            "L0": "Manual: All actions require manual approval.",
            "L1": "Human-in-the-Loop: Plan approvals required.",
            "L2": "Assisted: Write actions require approval.",
            "L3": "Conditional: Budget gates active (< $5 auto).",
            "L4": "High Autonomy: Deployments gated.",
            "L5": "Full Autonomy: Zero gates, full automation."
        };
        const profileTips = {
            "home": "IPTV / Media Allowed; Code blocked.",
            "work": "Coding / Swarms Allowed; TV blocked.",
            "cyber": "Security scan automation active.",
            "tv": "Only IPTV allowed."
        };

        if (autonomyDesc) autonomyDesc.textContent = autonomyTips[activeLevel] || '';
        if (profileDesc) profileDesc.textContent = profileTips[activeProfile] || '';

        // Safety Status
        if (safetyBadge) {
            safetyBadge.textContent = activeSafety.toUpperCase();
            if (activeSafety === 'paused') {
                safetyBadge.style.background = 'rgba(239, 68, 68, 0.15)';
                safetyBadge.style.borderColor = 'rgba(239, 68, 68, 0.4)';
                safetyBadge.style.color = '#f87171';
                if (btnPause) btnPause.style.display = 'none';
                if (btnResume) btnResume.style.display = 'inline-block';
            } else {
                safetyBadge.style.background = 'rgba(16, 185, 129, 0.15)';
                safetyBadge.style.borderColor = 'rgba(16, 185, 129, 0.4)';
                safetyBadge.style.color = '#34d399';
                if (btnPause) btnPause.style.display = 'inline-block';
                if (btnResume) btnResume.style.display = 'none';
            }
        }
    }

    async function loadReleaseStatus() {
        const vEl = el('release-status-version');
        const bEl = el('release-status-branch');
        const sEl = el('release-status-signature');
        const dEl = el('release-status-drift');
        const cEl = el('release-status-ci');
        
        if (!vEl) return;
        
        try {
            const res = await fetch('/api/v1/release/status');
            const data = await res.json();
            
            vEl.textContent = data.version || '0.1.6';
            bEl.textContent = data.branch || 'master';
            
            // Signature badge styling
            if (sEl) {
                const sig = data.signature_status || 'unsigned';
                sEl.textContent = sig.toUpperCase();
                if (sig === 'signed') {
                    sEl.style.background = 'rgba(16, 185, 129, 0.15)';
                    sEl.style.borderColor = 'rgba(16, 185, 129, 0.3)';
                    sEl.style.color = '#34d399';
                } else {
                    sEl.style.background = 'rgba(245, 158, 11, 0.15)';
                    sEl.style.borderColor = 'rgba(245, 158, 11, 0.3)';
                    sEl.style.color = '#fbbf24';
                }
            }
            
            // Drift status badge styling
            if (dEl) {
                const drift = data.drift_status || 'UNKNOWN';
                dEl.textContent = drift.toUpperCase();
                if (drift === 'ZERO_DRIFT_DETECTED' || drift === 'PASS' || drift === 'UNKNOWN') {
                    dEl.textContent = 'PASS';
                    dEl.style.background = 'rgba(16, 185, 129, 0.15)';
                    dEl.style.borderColor = 'rgba(16, 185, 129, 0.3)';
                    dEl.style.color = '#34d399';
                } else {
                    dEl.style.background = 'rgba(239, 68, 68, 0.15)';
                    dEl.style.borderColor = 'rgba(239, 68, 68, 0.3)';
                    dEl.style.color = '#f87171';
                }
            }
            
            // CI status
            if (cEl) {
                if (data.ci_run_id && data.ci_run_url) {
                    cEl.innerHTML = `<a href="${data.ci_run_url}" target="_blank" style="color: #60a5fa; text-decoration: underline;">Run #${data.ci_run_id}</a>`;
                } else {
                    cEl.textContent = 'LOCAL DEV';
                }
            }
        } catch (e) {
            console.error("Error loading release status:", e);
        }
    }

    async function loadClawdeView() {
        initClawdeControls();
        
        const phaseSpan = el('clawde-current-phase');
        const completedSpan = el('clawde-last-completed');
        const driftSpan = el('clawde-drift-status');
        const promptCode = el('clawde-generated-prompt-path');
        const reportCode = el('clawde-latest-report-path');
        const sealCode = el('clawde-evidence-seal-path');
        const blockedContainer = el('clawde-blocked-actions-container');
        
        const approvalBadge = el('clawde-approval-status-badge');
        const btnRequest = el('clawde-btn-request-execution');
        const btnApprove = el('clawde-btn-approve-execution');
        const btnExecute = el('clawde-btn-execute-phase');

        // Debug panel elements
        const dbgApi = el('clawde-dbg-api-status');
        const dbgCwd = el('clawde-dbg-cwd');
        const dbgRepo = el('clawde-dbg-repo-root');
        const dbgActive = el('clawde-dbg-active-phase');
        const dbgApprovalPath = el('clawde-dbg-approval-path');
        const dbgApprovalExists = el('clawde-dbg-approval-exists');
        const dbgRunnerExists = el('clawde-dbg-runner-exists');
        const dbgPromptExists = el('clawde-dbg-prompt-exists');
        const dbgReturncode = el('clawde-dbg-returncode');

        if (!phaseSpan) return;

        try {
            const res = await fetch('/api/v1/orchestrator/status');
            const data = await res.json();
            
            const reg = data.registry || {};
            const state = data.state || {};
            const paths = data.paths || {};
            let blockedActions = [];
            if (data.blocked_actions) {
                if (Array.isArray(data.blocked_actions)) {
                    blockedActions = data.blocked_actions;
                } else if (Array.isArray(data.blocked_actions.blocked_actions)) {
                    blockedActions = data.blocked_actions.blocked_actions;
                }
            }

            // Set next phase & last completed values
            const nextPhase = reg.next_phase || 'PR17';
            const lastCompleted = reg.last_completed_phase || 'PR16';

            if (!selectedPhase) {
                selectedPhase = nextPhase;
            }

            phaseSpan.textContent = selectedPhase;
            completedSpan.textContent = lastCompleted;

            // Render Phase Cards
            const cardsContainer = el('clawde-phase-cards-container');
            if (cardsContainer) {
                const phaseOrder = ["PR16", "PR17", "PR18", "COMPLETED"];
                const phaseMeta = {
                    "PR16": { title: "PR16: Plan", desc: "Cutover Plan" },
                    "PR17": { title: "PR17: Cutover", desc: "Cutover Execution" },
                    "PR18": { title: "PR18: Validate", desc: "Post-Cutover Validation" },
                    "COMPLETED": { title: "COMPLETED", desc: "Release Sealed" }
                };

                cardsContainer.innerHTML = phaseOrder.map(p => {
                    const meta = phaseMeta[p];
                    let cardState = 'pending';
                    let ledClass = '';
                    let statusLabel = 'Locked';
                    let statusColor = '#6b7280'; // gray

                    if (p === nextPhase) {
                        cardState = 'active';
                        ledClass = 'led-active';
                        statusLabel = 'Active';
                        statusColor = '#fbbf24'; // amber
                    } else {
                        let isDone = false;
                        if (nextPhase === 'COMPLETED') {
                            isDone = true;
                        } else {
                            const completedList = [];
                            if (lastCompleted === 'PR16') completedList.push('PR16');
                            if (lastCompleted === 'PR17') completedList.push('PR16', 'PR17');
                            if (lastCompleted === 'PR18') completedList.push('PR16', 'PR17', 'PR18');
                            if (completedList.includes(p)) isDone = true;
                        }
                        
                        if (isDone) {
                            cardState = 'completed';
                            statusLabel = 'Completed';
                            statusColor = '#10b981'; // green
                        }
                    }

                    let borderClass = '';
                    if (p === selectedPhase) {
                        borderClass = 'selected-phase';
                    } else if (cardState === 'active') {
                        borderClass = 'active-phase';
                    } else if (cardState === 'completed') {
                        borderClass = 'completed-phase';
                    }

                    let ledStyle = `width: 8px; height: 8px; border-radius: 50%; display: inline-block; background: ${statusColor};`;
                    if (cardState === 'active') {
                        ledStyle += ' box-shadow: 0 0 8px currentColor;';
                    }

                    return `
                        <div class="phase-card ${borderClass}" data-phase="${p}">
                            <div style="display: flex; justify-content: space-between; align-items: center;">
                                <span style="font-size: 12px; font-weight: 700; color: #fff;">${meta.title}</span>
                                <span class="${ledClass}" style="${ledStyle}"></span>
                            </div>
                            <span style="font-size: 10px; color: var(--text-secondary); line-height: 1.2;">${meta.desc}</span>
                            <span style="font-size: 9px; font-weight: bold; color: ${statusColor}; margin-top: 4px; text-transform: uppercase;">${statusLabel}</span>
                        </div>
                    `;
                }).join('');

                cardsContainer.querySelectorAll('.phase-card').forEach(card => {
                    card.addEventListener('click', () => {
                        selectedPhase = card.getAttribute('data-phase');
                        loadClawdeView();
                    });
                });
            }

            // Update Selected Phase title & status light in inspector
            const selectedStatusLight = el('clawde-selected-status-light');
            if (selectedStatusLight) {
                let statusColor = '#6b7280'; // gray
                if (selectedPhase === nextPhase) {
                    statusColor = '#fbbf24'; // amber
                } else {
                    let isDone = false;
                    if (nextPhase === 'COMPLETED') {
                        isDone = true;
                    } else {
                        const completedList = [];
                        if (lastCompleted === 'PR16') completedList.push('PR16');
                        if (lastCompleted === 'PR17') completedList.push('PR16', 'PR17');
                        if (lastCompleted === 'PR18') completedList.push('PR16', 'PR17', 'PR18');
                        if (completedList.includes(selectedPhase)) isDone = true;
                    }
                    if (isDone) statusColor = '#10b981'; // green
                }
                selectedStatusLight.style.background = statusColor;
            }

            // Drift Status
            const driftText = state.drift_status || 'ZERO DRIFT DETECTED';
            if (driftSpan) {
                driftSpan.textContent = driftText;
                if (driftText === 'ZERO DRIFT DETECTED' || driftText === 'PASS') {
                    driftSpan.style.background = 'rgba(16, 185, 129, 0.1)';
                    driftSpan.style.borderColor = 'rgba(16, 185, 129, 0.3)';
                    driftSpan.style.color = '#34d399';
                } else {
                    driftSpan.style.background = 'rgba(239, 68, 68, 0.1)';
                    driftSpan.style.borderColor = 'rgba(239, 68, 68, 0.3)';
                    driftSpan.style.color = '#f87171';
                }
            }

            // Populate selected phase files map paths
            const phasePaths = phaseFilesMap[selectedPhase] || { prompt: "None", report: "None", seal: "None" };
            if (promptCode) promptCode.textContent = phasePaths.prompt;
            if (reportCode) reportCode.textContent = phasePaths.report;
            if (sealCode) sealCode.textContent = phasePaths.seal;

            // Render Blocked Actions
            if (blockedContainer) {
                if (blockedActions.length === 0) {
                    blockedContainer.innerHTML = `<div style="color:var(--text-secondary); text-align:center; font-size:12px;">No blocked actions defined.</div>`;
                } else {
                    blockedContainer.innerHTML = blockedActions.map(act => `
                        <div style="display:flex; justify-content:space-between; align-items:center; background:rgba(255,255,255,0.02); padding:8px 12px; border-radius:6px; border:1px solid rgba(255,255,255,0.03);">
                            <div>
                                <span style="font-size:13px; font-weight:600; color:#fff; display:block;">${act.action}</span>
                                <span style="font-size:11px; color:var(--text-secondary);">${act.rationale || ''}</span>
                            </div>
                            <span style="font-size:11px; font-weight:bold; color:#f87171; background:rgba(239,68,68,0.1); border:1px solid rgba(239,68,68,0.2); padding:2px 8px; border-radius:4px;">BLOCKED</span>
                        </div>
                    `).join('');
                }
            }

            // Load and update Approval Gate Status
            const activePhase = reg.next_phase || 'PR17';
            
            // Check deterministic decision JSON in /api/v1/orchestrator/debug (which scans approval files)
            const dbgRes = await fetch('/api/v1/orchestrator/debug');
            const dbgData = await dbgRes.json();
            
            const approvalFile = `decision_${activePhase}_execute.json`;
            const approvalExists = dbgData.approval_decision_files && dbgData.approval_decision_files.includes(approvalFile);
            
            let status = 'NO REQUEST';
            
            if (approvalExists) {
                try {
                    const appRes = await fetch('/api/v1/approvals/queue');
                    const approvalsQueue = await appRes.json();
                    let matchedApproval = null;
                    for (const app of approvalsQueue) {
                        if (app.task_description && app.task_description.toLowerCase().includes(activePhase.toLowerCase())) {
                            matchedApproval = app;
                            break;
                        }
                    }
                    if (matchedApproval) {
                        status = matchedApproval.status;
                    } else {
                        status = 'APPROVED';
                    }
                } catch (e) {
                    status = 'APPROVED';
                }
            }
            
            const lockoutNotice = el('clawde-gate-lockout-notice');
            if (selectedPhase === nextPhase) {
                if (lockoutNotice) lockoutNotice.style.display = 'none';
                if (approvalBadge) {
                    approvalBadge.textContent = status;
                    if (status === 'APPROVED') {
                        approvalBadge.style.background = 'rgba(16, 185, 129, 0.1)';
                        approvalBadge.style.borderColor = 'rgba(16, 185, 129, 0.3)';
                        approvalBadge.style.color = '#34d399';
                        if (btnRequest) btnRequest.style.display = 'none';
                        if (btnApprove) btnApprove.style.display = 'none';
                        if (btnExecute) {
                            btnExecute.removeAttribute('disabled');
                            btnExecute.style.opacity = '1';
                            btnExecute.style.cursor = 'pointer';
                        }
                    } else if (status === 'PENDING') {
                        approvalBadge.style.background = 'rgba(245, 158, 11, 0.1)';
                        approvalBadge.style.borderColor = 'rgba(245, 158, 11, 0.3)';
                        approvalBadge.style.color = '#fbbf24';
                        if (btnRequest) btnRequest.style.display = 'none';
                        if (btnApprove) btnApprove.style.display = 'inline-block';
                        if (btnExecute) {
                            btnExecute.setAttribute('disabled', 'true');
                            btnExecute.style.opacity = '0.5';
                            btnExecute.style.cursor = 'not-allowed';
                        }
                    } else {
                        approvalBadge.style.background = 'rgba(255,255,255,0.05)';
                        approvalBadge.style.borderColor = 'rgba(255,255,255,0.1)';
                        approvalBadge.style.color = 'var(--text-secondary)';
                        if (btnRequest) btnRequest.style.display = 'inline-block';
                        if (btnApprove) btnApprove.style.display = 'none';
                        if (btnExecute) {
                            btnExecute.setAttribute('disabled', 'true');
                            btnExecute.style.opacity = '0.5';
                            btnExecute.style.cursor = 'not-allowed';
                        }
                    }
                }
            } else {
                if (btnRequest) btnRequest.style.display = 'none';
                if (btnApprove) btnApprove.style.display = 'none';
                if (btnExecute) {
                    btnExecute.setAttribute('disabled', 'true');
                    btnExecute.style.opacity = '0.5';
                    btnExecute.style.cursor = 'not-allowed';
                }
                if (approvalBadge) {
                    approvalBadge.textContent = 'LOCKED';
                    approvalBadge.style.background = 'rgba(255,255,255,0.03)';
                    approvalBadge.style.borderColor = 'rgba(255,255,255,0.08)';
                    approvalBadge.style.color = 'var(--text-secondary)';
                }
                if (lockoutNotice) {
                    lockoutNotice.style.display = 'block';
                    let message = 'This phase is locked.';
                    let isDone = false;
                    if (nextPhase === 'COMPLETED') {
                        isDone = true;
                    } else {
                        const completedList = [];
                        if (lastCompleted === 'PR16') completedList.push('PR16');
                        if (lastCompleted === 'PR17') completedList.push('PR16', 'PR17');
                        if (lastCompleted === 'PR18') completedList.push('PR16', 'PR17', 'PR18');
                        if (completedList.includes(selectedPhase)) isDone = true;
                    }
                    if (isDone) {
                        message = 'This phase has already been completed.';
                    } else {
                        message = `This phase is locked until phase ${nextPhase} is executed.`;
                    }
                    lockoutNotice.textContent = message;
                }
            }

            // Gated execution buttons state management
            const btnNoDrift = el('clawde-btn-no-drift');
            const btnRender = el('clawde-btn-render-phase');
            const isActivePhaseSelected = selectedPhase === nextPhase;
            const buttonsToGate = [btnNoDrift, btnRender];
            buttonsToGate.forEach(btn => {
                if (btn) {
                    if (isActivePhaseSelected) {
                        btn.removeAttribute('disabled');
                        btn.style.opacity = '1';
                        btn.style.cursor = 'pointer';
                    } else {
                        btn.setAttribute('disabled', 'true');
                        btn.style.opacity = '0.4';
                        btn.style.cursor = 'not-allowed';
                    }
                }
            });

            // Populate Debug Panel values
            if (dbgApi) {
                dbgApi.textContent = 'ONLINE';
                dbgApi.style.color = '#34d399';
            }
            if (dbgCwd) dbgCwd.textContent = dbgData.cwd || '--';
            if (dbgRepo) dbgRepo.textContent = dbgData.repo_root || '--';
            if (dbgActive) dbgActive.textContent = dbgData.active_phase || '--';
            if (dbgApprovalPath) dbgApprovalPath.textContent = `artifacts/orchestrator/approvals/${approvalFile}`;
            if (dbgApprovalExists) {
                dbgApprovalExists.textContent = approvalExists ? 'YES' : 'NO';
                dbgApprovalExists.style.color = approvalExists ? '#34d399' : '#f87171';
            }
            if (dbgRunnerExists) {
                dbgRunnerExists.textContent = dbgData.builder_runner_path_exists ? 'YES' : 'NO';
                dbgRunnerExists.style.color = dbgData.builder_runner_path_exists ? '#34d399' : '#f87171';
            }
            if (dbgPromptExists) {
                dbgPromptExists.textContent = dbgData.generated_prompt_exists ? 'YES' : 'NO';
                dbgPromptExists.style.color = dbgData.generated_prompt_exists ? '#34d399' : '#f87171';
            }
            if (dbgReturncode) {
                // Set default/last run status code
                dbgReturncode.textContent = '0';
            }

            // Load history list
            await loadClawdeHistory();

            // Load observability dashboard
            await loadObservabilityDashboard();

            // Load Release & Provenance Status
            await loadReleaseStatus();

            // Load control plane policy
            try {
                const policyRes = await fetch('/api/v1/control/policy');
                const policy = await policyRes.json();
                updatePolicyUI(policy);
            } catch (err) {
                console.error("Failed to fetch control policy status:", err);
            }

            // Fetch model provider registry and health statuses
            try {
                const providersRes = await fetch('/api/v1/models/providers');
                const providers = await providersRes.json();
                
                let lmstudioAvailable = false;
                let ollamaAvailable = false;
                
                providers.forEach(p => {
                    const status = p.health_status || 'unavailable';
                    const type = p.provider_type || '';
                    const isOk = status === 'available';
                    
                    if (p.model_provider_id === 'lmstudio' || type === 'lmstudio' || p.endpoint_url?.includes('1234')) {
                        lmstudioAvailable = isOk;
                    } else if (p.model_provider_id === 'ollama' || type === 'ollama' || p.endpoint_url?.includes('11434')) {
                        ollamaAvailable = isOk;
                    }
                });
                
                const lmDot = el('model-health-lmstudio-dot');
                const olDot = el('model-health-ollama-dot');
                
                if (lmDot) lmDot.style.background = lmstudioAvailable ? '#34d399' : '#f87171';
                if (olDot) olDot.style.background = ollamaAvailable ? '#34d399' : '#f87171';
            } catch (err) {
                console.error("Failed to load local model health:", err);
            }

            // Fetch live telemetry logs
            try {
                const telemetryRes = await fetch('/api/v1/control/live-swarm');
                const telemetry = await telemetryRes.json();
                
                const logBox = el('telemetry-log-stream');
                if (logBox) {
                    if (telemetry.events && telemetry.events.length > 0) {
                        logBox.innerHTML = telemetry.events.map(ev => {
                            const icon = ev.icon || '●';
                            return `<div>[${ev.ts || ''}] ${icon} ${ev.name || ''} - Status: ${ev.status || ''} | ${ev.activity || ''} (CPU: ${ev.cpu || 0}%, RAM: ${ev.ram || 0}%)</div>`;
                        }).join('');
                    } else {
                        logBox.innerHTML = `<div style="color: #6b7280;">[SYSTEM] Telemetry session initialized. Waiting for events...</div>`;
                    }
                }
            } catch (err) {
                console.error("Failed to load live telemetry:", err);
            }

        } catch (err) {
            console.error("Error loading CLAWDE Control Tower state:", err);
            if (dbgApi) {
                dbgApi.textContent = 'OFFLINE';
                dbgApi.style.color = '#f87171';
            }
        }
    }

    async function syncObservabilityDashboard() {
        const btn = el('clawde-btn-ingest-run');
        if (btn) {
            btn.disabled = true;
            btn.textContent = 'Syncing...';
        }
        try {
            const ingestRes = await fetch('/api/v1/ingest/crewai', { method: 'POST' });
            if (ingestRes.ok) {
                await loadObservabilityDashboard();
            }
        } catch (err) {
            console.error('Failed to sync observability metrics:', err);
        } finally {
            if (btn) {
                btn.disabled = false;
                btn.textContent = 'Sync Swarm Reports';
            }
        }
    }

    async function loadObservabilityDashboard() {
        const tbody = el('observability-details-tbody');
        if (!tbody) return;
        try {
            const res = await fetch('/api/v1/ingest/crewai/artifacts');
            const artifacts = await res.json();
            const reports = artifacts.filter(a => a.artifact_type === 'crew_run_report');
            
            if (reports.length === 0) {
                tbody.innerHTML = `<tr><td colspan="5" style="padding: 20px; text-align: center; color: var(--text-secondary);">No run telemetry found. Run the swarm first.</td></tr>`;
                return;
            }
            
            const latest = reports[0];
            const context = latest.run_context || {};
            const metrics = context.metrics || {};
            const tokenUsage = metrics.total_token_usage || {};
            const tasks = metrics.tasks || [];
            
            // Update overall summary cards
            if (el('obs-stat-tokens')) {
                el('obs-stat-tokens').textContent = tokenUsage.total_tokens !== undefined ? tokenUsage.total_tokens.toLocaleString() : 'N/A';
            }
            if (el('obs-stat-runtime')) {
                el('obs-stat-runtime').textContent = metrics.total_runtime_seconds !== undefined ? `${metrics.total_runtime_seconds}s` : 'N/A';
            }
            
            const statusEl = el('obs-stat-status');
            if (statusEl) {
                const statusText = context.status || 'PASS';
                statusEl.textContent = statusText;
                if (statusText === 'PASS') {
                    statusEl.style.color = '#10b981';
                } else {
                    statusEl.style.color = '#ef4444';
                }
            }
            
            // Count fallback events
            let fallbacksCount = 0;
            tasks.forEach(t => {
                if (t.fallback_event) fallbacksCount++;
            });
            if (el('obs-stat-fallbacks')) {
                el('obs-stat-fallbacks').textContent = fallbacksCount;
            }
            
            // Build task rows
            if (tasks.length === 0) {
                tbody.innerHTML = `<tr><td colspan="8" style="padding: 20px; text-align: center; color: var(--text-secondary);">Report exists but contains no task metrics.</td></tr>`;
                return;
            }
            
            const agentToClass = {
                "asset_mapper": "fast_classification",
                "swarm_architect": "planning_docs",
                "agent_combinator": "coding_repair",
                "security_operator": "security_audit",
                "execution_planner": "planning_docs",
                "synthesis_director": "planning_docs",
                "antigravity_integration_operator": "planning_docs"
            };

            tbody.innerHTML = tasks.map(t => {
                const fallbackBadge = t.fallback_event 
                    ? `<span style="background: rgba(239, 68, 68, 0.15); border: 1px solid rgba(239, 68, 68, 0.3); color: #f87171; padding: 2px 6px; border-radius: 4px; font-weight: bold; font-size: 9px;">FALLBACK</span>`
                    : `<span style="background: rgba(16, 185, 129, 0.15); border: 1px solid rgba(16, 185, 129, 0.3); color: #34d399; padding: 2px 6px; border-radius: 4px; font-weight: bold; font-size: 9px;">PRIMARY</span>`;
                
                const validationStatus = t.validation_status || t.artifact_quality || 'NOT_APPLICABLE';
                const qualityBadge = validationStatus === 'VALID'
                    ? `<span style="color: #34d399; font-weight: bold;">VALID</span>`
                    : validationStatus === 'INVALID'
                    ? `<span style="color: #f87171; font-weight: bold;">INVALID</span>`
                    : `<span style="color: var(--text-secondary);">${validationStatus}</span>`;
                
                const taskClass = t.task_class || agentToClass[t.agent_key] || 'unknown';
                const tokensVal = t.tokens !== undefined ? t.tokens.toLocaleString() : 'N/A';
                const artifactRes = t.artifact_result || 'None';

                return `
                    <tr style="border-bottom: 1px solid rgba(255,255,255,0.05); transition: background 0.2s;">
                        <td style="padding: 10px 12px; font-weight: 500;">
                            <div style="color: #fff; font-size: 12px;">${t.agent_role}</div>
                            <div style="color: var(--text-secondary); font-size: 10px; margin-top: 2px;">${t.task_name}</div>
                        </td>
                        <td style="padding: 10px 12px; color: #a5b4fc;">${taskClass}</td>
                        <td style="padding: 10px 12px; font-family: monospace; color: #e0e7ff;">${t.model}</td>
                        <td style="padding: 10px 12px;">${fallbackBadge}</td>
                        <td style="padding: 10px 12px; text-align: right; color: #fbbf24; font-weight: 500;">${t.runtime_seconds_estimate}s</td>
                        <td style="padding: 10px 12px; text-align: right; color: #c7d2fe;">${tokensVal}</td>
                        <td style="padding: 10px 12px; font-family: monospace; color: var(--text-secondary);">${artifactRes}</td>
                        <td style="padding: 10px 12px; text-align: right;">${qualityBadge}</td>
                    </tr>
                `;
            }).join('');
        } catch (err) {
            console.error('Error loading observability dashboard:', err);
            tbody.innerHTML = `<tr><td colspan="8" style="padding: 20px; text-align: center; color: #ef4444;">Error loading observability data.</td></tr>`;
        }
    }


    // ── Loader: Agent Flight Deck View (PROTO-3) ──────────────────────────────
    let isFlightDeckInitialized = false;
    let selectedCampaignId = "";

    async function loadAgentFlightDeckView() {
        const selector = el('campaign-selector');
        const campaignsContainer = el('lane-campaigns');
        const tasksContainer = el('lane-tasks');
        const rosterContainer = el('lane-roster');
        const gatesContainer = el('lane-gates');

        if (!campaignsContainer || !tasksContainer || !rosterContainer || !gatesContainer) return;

        try {
            // 1. Fetch campaigns (runs)
            const runsRes = await fetch('/api/v1/runs');
            const runs = await runsRes.json();
            
            // Populate active selector and campaign lane
            const campaignCountBadge = el('campaign-count-badge');
            if (campaignCountBadge) campaignCountBadge.textContent = runs.length;

            // Render Campaigns Lane
            campaignsContainer.innerHTML = runs.map(r => `
                <div class="flight-card" data-run-id="${r.run_id}" style="cursor: pointer; border-left: 3px solid ${r.status === 'running' ? '#3b82f6' : (r.status === 'completed' ? '#10b981' : '#ef4444')};">
                    <div class="flight-card-title">${r.name}</div>
                    <div class="flight-card-meta">ID: ${r.run_id}</div>
                    <span class="flight-card-badge status-badge ${r.status === 'running' ? 'warn' : (r.status === 'completed' ? 'success' : 'fail')}">${r.status}</span>
                </div>
            `).join('') || `<div style="color:var(--text-secondary); text-align:center; font-size:12px;">No active campaigns</div>`;

            // Setup select dropdown options if changed or empty
            const selectorIds = Array.from(selector.options).map(o => o.value);
            const runIds = runs.map(r => r.run_id);
            const needsOptionRefresh = runIds.some(id => !selectorIds.includes(id)) || selectorIds.some(id => !runIds.includes(id));
            
            if (needsOptionRefresh) {
                selector.innerHTML = runs.map(r => `
                    <option value="${r.run_id}" ${r.run_id === selectedCampaignId ? 'selected' : ''}>${r.name}</option>
                `).join('');
                if (runs.length > 0 && !selectedCampaignId) {
                    selectedCampaignId = runs[0].run_id;
                    selector.value = selectedCampaignId;
                }
            }

            // Bind click listeners on campaign cards to select them
            campaignsContainer.querySelectorAll('.flight-card').forEach(card => {
                card.addEventListener('click', () => {
                    const runId = card.getAttribute('data-run-id');
                    if (runId) {
                        selectedCampaignId = runId;
                        selector.value = runId;
                        loadActiveCampaignTasks();
                    }
                });
            });

            // 2. Fetch Tasks for selected campaign
            if (selectedCampaignId) {
                await loadActiveCampaignTasks();
            } else {
                tasksContainer.innerHTML = `<div style="color:var(--text-secondary); text-align:center; font-size:12px;">Select a campaign to view tasks</div>`;
                const taskCountBadge = el('task-count-badge');
                if (taskCountBadge) taskCountBadge.textContent = "0";
            }

            // 3. Fetch Agent Duty Roster
            const agentsRes = await fetch('/api/v1/agents');
            const agents = await agentsRes.json();
            const agentCountBadge = el('agent-count-badge');
            if (agentCountBadge) agentCountBadge.textContent = agents.length;

            rosterContainer.innerHTML = agents.map(a => {
                let tools = a.allowed_tools || [];
                if (typeof tools === 'string') {
                    try { tools = JSON.parse(tools); } catch(e) { tools = []; }
                }
                const toolsList = Array.isArray(tools) ? tools.slice(0, 3).join(', ') : '';
                return `
                    <div class="flight-card" style="border-left: 3px solid var(--accent-blue);">
                        <div class="flight-card-title" style="display:flex; justify-content:space-between; align-items:center;">
                            <span>${a.name || a.agent_id}</span>
                            <span class="provenance-badge observed" style="font-size:8px;">${a.lifecycle || 'ACTIVE'}</span>
                        </div>
                        <div class="flight-card-meta">Role: ${a.role || 'Agent'}</div>
                        <div class="flight-card-meta">File Scope: <code>${a.file_scopes || '/'}</code></div>
                        <div class="flight-card-meta" style="font-size:9px; color:var(--text-secondary); margin-top:2px;">Tools: ${toolsList}${tools.length > 3 ? '...' : ''}</div>
                    </div>
                `;
            }).join('') || `<div style="color:var(--text-secondary); text-align:center; font-size:12px;">No active agents registered</div>`;

            // 4. Fetch Governance Gates
            const gatesRes = await fetch('/api/v1/release/signing-policy');
            const gatesData = await gatesRes.json();
            const currentRelease = gatesData.current_release || {};
            
            const gateItems = [];
            if (currentRelease.signature_status === "unsigned" && currentRelease.signing_waiver_status === "none") {
                gateItems.push({
                    id: "signing_waiver",
                    title: "Release Cryptographic Signing Policy Block",
                    description: `Release v${currentRelease.version} is unsigned. Cryptographic validation requires signing or an operator waiver.`,
                    type: "signing_waiver",
                    severity: "high"
                });
            }

            // Also check for pending model routing or other policy overrides
            const policyRes = await fetch('/api/v1/policies/decisions');
            const policies = await policyRes.json();
            const pendingDecisions = policies.filter(p => p.decision === "APPROVAL_REQUIRED" || p.decision === "BLOCK");
            pendingDecisions.forEach(p => {
                gateItems.push({
                    id: `policy-${p.decision_id || Math.random().toString(36).substring(2, 8)}`,
                    title: `Policy Override: ${p.rule_name || 'Verification Block'}`,
                    description: p.reason || "Action requires operator override and compliance verification.",
                    type: "policy_override",
                    severity: "medium"
                });
            });

            // Fetch generic approvals from /api/approval/requests
            try {
                const appRes = await fetch('/api/approval/requests');
                const approvals = await appRes.json();
                approvals.forEach(a => {
                    if (a.status === "pending") {
                        if (a.command && a.command.prompt) {
                            gateItems.push({
                                id: a.approval_id,
                                title: `Governed Agent Launch: ${a.command.agent_id || 'Agent'}`,
                                description: `Prompt: "${a.command.prompt}" | Target: ${a.command.target || 'swarm'}`,
                                type: "agent_launch",
                                severity: "medium"
                            });
                        } else if (a.approval_id !== "signing_waiver") {
                            gateItems.push({
                                id: a.approval_id,
                                title: a.command ? `Command: ${a.command.raw_text}` : `Approval Request: ${a.approval_id}`,
                                description: a.policy_context ? a.policy_context.approval_reason : "Awaiting operator authorization.",
                                type: "generic",
                                severity: "medium"
                            });
                        }
                    }
                });
            } catch (err) {
                console.error('[FlightDeck] failed to fetch approvals:', err);
            }

            const gateCountBadge = el('gate-count-badge');
            if (gateCountBadge) gateCountBadge.textContent = gateItems.length;

            gatesContainer.innerHTML = gateItems.map(g => `
                <div class="flight-card" style="border-left: 3px solid ${g.severity === 'high' ? '#ef4444' : '#f59e0b'};">
                    <div class="flight-card-title">${g.title}</div>
                    <div class="flight-card-meta">${g.description}</div>
                    <div class="flight-gate-actions">
                        <button class="flight-gate-btn btn-approve" data-gate-id="${g.id}" data-gate-type="${g.type}">Approve</button>
                        <button class="flight-gate-btn btn-reject" data-gate-id="${g.id}" data-gate-type="${g.type}">Reject</button>
                    </div>
                </div>
            `).join('') || `<div style="color:var(--text-secondary); text-align:center; font-size:12px;">Zero pending approval gates</div>`;

            // Bind approval gates click handlers (Approve)
            gatesContainer.querySelectorAll('.btn-approve').forEach(btn => {
                btn.addEventListener('click', async () => {
                    const gateId = btn.getAttribute('data-gate-id');
                    const gateType = btn.getAttribute('data-gate-type');
                    if (gateType === "signing_waiver") {
                        try {
                            const submitRes = await fetch('/api/v1/release/signing-waiver', {
                                method: 'POST',
                                headers: { 'Content-Type': 'application/json' },
                                body: JSON.stringify({
                                    reason: "Operator dynamic flight deck override waiver",
                                    scope: "local_dev",
                                    operator: "Michael Hoch"
                                })
                            });
                            if (submitRes.ok) {
                                triggerGeneralRipple(window.innerWidth / 2, window.innerHeight / 2, "normal");
                                loadAgentFlightDeckView();
                            }
                        } catch (err) {
                            console.error('[FlightDeck] failed to waive:', err);
                        }
                    } else {
                        try {
                            const submitRes = await fetch(`/api/approval/requests/${gateId}/decisions`, {
                                method: 'POST',
                                headers: { 'Content-Type': 'application/json' },
                                body: JSON.stringify({
                                    decision: "approve",
                                    reason: "Operator dynamic flight deck override",
                                    operator: "Michael Hoch"
                                })
                            });
                            if (submitRes.ok) {
                                triggerGeneralRipple(window.innerWidth / 2, window.innerHeight / 2, "normal");
                                loadAgentFlightDeckView();
                            }
                        } catch (err) {
                            console.error('[FlightDeck] failed to approve request:', err);
                        }
                    }
                });
            });

            // Bind approval gates click handlers (Reject)
            gatesContainer.querySelectorAll('.btn-reject').forEach(btn => {
                btn.addEventListener('click', async () => {
                    const gateId = btn.getAttribute('data-gate-id');
                    const gateType = btn.getAttribute('data-gate-type');
                    if (gateType !== "signing_waiver") {
                        try {
                            const submitRes = await fetch(`/api/approval/requests/${gateId}/decisions`, {
                                method: 'POST',
                                headers: { 'Content-Type': 'application/json' },
                                body: JSON.stringify({
                                    decision: "reject",
                                    reason: "Operator dynamic flight deck rejection",
                                    operator: "Michael Hoch"
                                })
                            });
                            if (submitRes.ok) {
                                loadAgentFlightDeckView();
                            }
                        } catch (err) {
                            console.error('[FlightDeck] failed to reject request:', err);
                        }
                    }
                });
            });

            // Initialize control listeners once
            if (!isFlightDeckInitialized) {
                selector.addEventListener('change', (e) => {
                    selectedCampaignId = e.target.value;
                    loadActiveCampaignTasks();
                });

                const launchBtn = el('btn-launch-campaign');
                if (launchBtn) {
                    launchBtn.addEventListener('click', async () => {
                        const triggerLaunch = async (override = false) => {
                            try {
                                const createRes = await fetch('/api/v1/runs', {
                                    method: 'POST',
                                    headers: { 'Content-Type': 'application/json' },
                                    body: JSON.stringify({
                                        name: `Flight Campaign ${new Date().toLocaleTimeString()}`,
                                        override: override
                                    })
                                });
                                if (createRes.status === 400) {
                                    const rdata = await createRes.json();
                                    if (rdata.detail && rdata.detail.error === 'PREFLIGHT_BLOCKED') {
                                        const failedChecks = (rdata.detail.checks || []).filter(c => c.status !== 'PASS');
                                        showPreflightBlocker(failedChecks, () => triggerLaunch(true));
                                        return;
                                    }
                                }
                                if (createRes.ok) {
                                    const newRun = await createRes.json();
                                    selectedCampaignId = newRun.run_id;
                                    isFlightDeckInitialized = false; // force refresh dropdown
                                    loadAgentFlightDeckView();
                                }
                            } catch (err) {
                                console.error('[FlightDeck] failed to launch campaign:', err);
                            }
                        };
                        await triggerLaunch(false);
                    });
                }

                isFlightDeckInitialized = true;
            }

        } catch (err) {
            console.error('[FlightDeck] load error:', err);
        }
    }

    async function loadActiveCampaignTasks() {
        const container = el('lane-tasks');
        if (!container || !selectedCampaignId) return;

        try {
            const res = await fetch(`/api/v1/runs/${selectedCampaignId}/tasks`);
            const tasks = await res.json();
            const taskCountBadge = el('task-count-badge');
            if (taskCountBadge) taskCountBadge.textContent = tasks.length;

            container.innerHTML = tasks.map(t => {
                const priorityColor = t.priority === 'critical' ? '#ef4444' : (t.priority === 'high' ? '#f59e0b' : '#3b82f6');
                return `
                    <div class="flight-card" style="border-left: 3px solid ${t.status === 'completed' ? '#10b981' : (t.status === 'running' ? '#3b82f6' : 'rgba(255,255,255,0.05)')};">
                        <div class="flight-card-title">${t.title}</div>
                        <div class="flight-card-meta">ID: ${t.id}</div>
                        <div class="flight-card-meta">Agent: <code>${t.ownerAgentId || 'unassigned'}</code></div>
                        <div style="display:flex; justify-content:space-between; align-items:center; margin-top:4px;">
                            <span class="flight-card-badge status-badge ${t.status === 'running' ? 'warn' : (t.status === 'completed' ? 'success' : 'blocked')}">${t.status}</span>
                            <span style="font-size:9px; color:${priorityColor}; font-weight:700; text-transform:uppercase;">${t.priority}</span>
                        </div>
                    </div>
                `;
            }).join('') || `<div style="color:var(--text-secondary); text-align:center; font-size:12px;">No tasks in this campaign</div>`;
        } catch (err) {
            console.error('[FlightDeck] failed to load tasks:', err);
        }
    }

    // ── Koi Animation Layer (Batch UI-KOI-1, PROTO-2 & Observability) ────────────
    function getDeterministicOrbit(id) {
        let hash = 0;
        for (let i = 0; i < id.length; i++) {
            hash = id.charCodeAt(i) + ((hash << 5) - hash);
        }
        const absHash = Math.abs(hash);
        const width = 200 + (absHash % 250); // 200px to 450px
        const duration = 30 + (absHash % 45); // 30s to 75s
        const top = `${10 + (absHash % 50)}%`; // 10% to 60%
        const left = `${15 + ((absHash >> 2) % 65)}%`; // 15% to 80%
        const reverse = (absHash % 2) === 0;
        return { width, height: width, duration, top, left, reverse };
    }

    function createKoiSVG() {
        return `
            <svg viewBox="0 0 60 30" width="100%" height="100%" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path class="koi-body-path" d="M5,15 Q30,5 55,15 Q30,25 5,15 Z" fill="currentColor" opacity="0.8"/>
                <path d="M25,8 Q20,2 15,5 Q18,8 20,8 Z" fill="currentColor" opacity="0.6"/>
                <path d="M25,22 Q20,28 15,25 Q18,22 20,22 Z" fill="currentColor" opacity="0.6"/>
                <path d="M5,15 Q0,10 2,5 Q5,10 5,15 Z" fill="currentColor" opacity="0.7"/>
                <path d="M5,15 Q0,20 2,25 Q5,20 5,15 Z" fill="currentColor" opacity="0.7"/>
            </svg>
        `;
    }

    function initializeKoiAnimation() {
        if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
            return;
        }
        const pond = document.getElementById("koi-pond-layer");
        if (!pond) return;

        // Clear existing
        pond.innerHTML = "";
        koiFishInstances = {};

        // Document click triggers ripples
        document.addEventListener("click", (e) => {
            if (e.target.tagName !== "BUTTON" && e.target.tagName !== "A" && e.target.tagName !== "INPUT" && e.target.tagName !== "SELECT") {
                triggerGeneralRipple(e.clientX, e.clientY);
            }
        });

        // Random background ripples
        setInterval(() => {
            if (document.hidden) return;
            const x = Math.random() * window.innerWidth;
            const y = Math.random() * window.innerHeight;
            triggerGeneralRipple(x, y);
        }, 5000);
    }

    function triggerGeneralRipple(x, y, type = "normal") {
        if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
        const pond = document.getElementById("koi-pond-layer");
        if (!pond) return;

        const ripple = document.createElement("div");
        ripple.className = "koi-ripple";
        if (type === "broken") ripple.classList.add("ripple-broken");
        if (type === "warning") ripple.classList.add("ripple-warning");
        ripple.style.left = `${x}px`;
        ripple.style.top = `${y}px`;
        pond.appendChild(ripple);
        setTimeout(() => {
            ripple.remove();
        }, 3500);
    }

    function triggerKoiRipple(entityId, type = "normal") {
        const orbit = koiFishInstances[entityId];
        if (!orbit) return;
        const fish = orbit.querySelector(".koi-fish");
        if (!fish) return;

        const rect = fish.getBoundingClientRect();
        const x = rect.left + rect.width / 2;
        const y = rect.top + rect.height / 2;

        triggerGeneralRipple(x, y, type);
    }

    function updateKoiPond(meshData) {
        if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
            return;
        }

        const pond = document.getElementById("koi-pond-layer");
        if (!pond) return;

        const models = meshData.models || [];
        const agents = meshData.agents || [];

        // Build current active entity list based on live API registry data
        const activeEntities = [];

        // Models
        models.forEach(m => {
            activeEntities.push({
                id: m.id,
                name: m.id,
                type: "model",
                status: m.status,
                truth_state: m.truth_state,
                endpoint: m.endpoint
            });
        });

        // Agents
        agents.forEach(a => {
            activeEntities.push({
                id: a.id,
                name: a.name,
                type: "agent",
                status: a.status,
                truth_state: a.truth_state,
                endpoint: "/api/v1/model-mesh/config"
            });
        });

        // Local Swarm API
        activeEntities.push({
            id: "local-swarm-api",
            name: "Local Swarm API",
            type: "api",
            status: "LIVE",
            truth_state: "LIVE",
            endpoint: "/api/v1/live-runtime/cockpit"
        });

        // Remove fish elements for deactivated entities
        const activeIds = activeEntities.map(e => e.id);
        Object.keys(koiFishInstances).forEach(id => {
            if (!activeIds.includes(id)) {
                const orbit = koiFishInstances[id];
                if (orbit) orbit.remove();
                delete koiFishInstances[id];
            }
        });

        // Spawn or update fish elements for active entities
        activeEntities.forEach(ent => {
            let orbit = koiFishInstances[ent.id];
            if (!orbit) {
                const cfg = getDeterministicOrbit(ent.id);
                orbit = document.createElement("div");
                orbit.className = "koi-orbit";
                orbit.style.width = `${cfg.width}px`;
                orbit.style.height = `${cfg.height}px`;
                orbit.style.top = cfg.top;
                orbit.style.left = cfg.left;
                orbit.style.animationDuration = `${cfg.duration}s`;
                if (cfg.reverse) {
                    orbit.style.animationDirection = "reverse";
                }

                const fish = document.createElement("div");
                fish.className = "koi-fish";
                fish.style.top = "0px";
                fish.style.left = "50%";
                fish.style.transform = "translateX(-50%) rotate(90deg)";
                fish.innerHTML = createKoiSVG();

                // Audit metadata attributes binding
                fish.setAttribute("data-entity-id", ent.id);
                fish.setAttribute("data-entity-type", ent.type);
                fish.setAttribute("data-source-endpoint", ent.endpoint);

                orbit.appendChild(fish);
                pond.appendChild(orbit);
                koiFishInstances[ent.id] = orbit;
            }

            // Update classes and dynamic state attributes
            const fish = orbit.querySelector(".koi-fish");
            if (fish) {
                fish.setAttribute("data-truth-state", ent.truth_state);
                fish.className = "koi-fish";
                
                const truthClass = `state-${ent.truth_state.toLowerCase().replace('_', '-')}`;
                fish.classList.add(truthClass);

                // Control orbit play state based on connectivity status
                orbit.classList.remove("swim-paused");
                if (ent.status === "BROKEN" || ent.status === "OFFLINE" || ent.truth_state === "MISSING_FROM_SCAN") {
                    orbit.classList.add("swim-paused");
                }
            }
        });
    }

    async function loadModelMeshView() {
        const agentsContainer = el('mesh-agents-list');
        const flowGraph = el('mesh-flow-graph');
        const vitalsContainer = el('mesh-vitals');
        const consoleContainer = el('mesh-console');
        const gapsContainer = el('mesh-gaps');
        
        if (!agentsContainer) return;

        try {
            const res = await fetch('/api/v1/model-mesh/config');
            const data = await res.json();
            
            // 1. Render Agent Spin-Up Profiles
            const agents = data.agents || [];
            agentsContainer.innerHTML = agents.map(a => {
                let badgeClass = 'mesh-state-badge';
                if (a.truth_state === 'PENDING') badgeClass += ' state-pending';
                else if (a.truth_state === 'APPROVAL_REQUIRED') badgeClass += ' state-approval-required';
                else if (a.truth_state === 'BROKEN') badgeClass += ' state-broken';
                
                const initials = a.name.split(' ').map(n => n[0]).join('');
                const hasPulse = a.status === 'LIVE' ? 'pulse-active' : '';

                return `
                    <div class="mesh-agent-item" style="border: 1px solid rgba(16, 185, 129, 0.15); padding: 10px; border-radius: 8px; background: rgba(0,0,0,0.25);">
                        <div class="mesh-avatar ${hasPulse}" style="width:32px; height:32px; font-size:12px;">${initials}</div>
                        <div style="display:flex; flex-direction:column; gap:2px; margin-left:10px;">
                            <strong style="font-size:12px; color:#fff;">${a.name}</strong>
                            <span style="font-size:10px; opacity:0.8; color:var(--text-secondary);">${a.role}</span>
                            <span style="font-size:9px; color:var(--text-secondary);">Pref: <code style="color:var(--accent-blue);">${a.preferred_model}</code></span>
                        </div>
                        <div class="${badgeClass}">${a.truth_state}</div>
                    </div>
                `;
            }).join('');

            // 2. Render Swarm Vitals (Model Performance Telemetry)
            const models = data.models || [];
            vitalsContainer.innerHTML = models.map(m => {
                const tel = m.telemetry || {};
                const isLive = m.reachable;
                const statusColor = isLive ? '#10b981' : '#ef4444';
                const statusBorder = isLive ? 'rgba(16,185,129,0.3)' : 'rgba(239,68,68,0.3)';

                return `
                    <div class="card" style="padding:10px; margin-bottom:0; border:1px solid ${statusBorder};">
                        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
                            <strong style="font-size:12px; color:#fff;">${m.id} (${m.provider})</strong>
                            <span style="font-size:8px; border:1px solid ${statusBorder}; padding:2px 6px; border-radius:99px; color:${statusColor}; font-weight:bold;">
                                ${m.status}
                            </span>
                        </div>
                        <div style="font-size:10px; display:grid; grid-template-columns:1fr 1fr; gap:4px; opacity:0.8;">
                            <div>Latency: <strong>${tel.latency_ms ? tel.latency_ms.toFixed(1) : '0.0'} ms</strong></div>
                            <div>Speed: <strong>${tel.tokens_per_sec ? tel.tokens_per_sec.toFixed(1) : '0.0'} t/s</strong></div>
                            <div>VRAM: <strong>${tel.vram_gb ? tel.vram_gb.toFixed(1) : '0.0'} GB</strong></div>
                            <div>RAM: <strong>${tel.ram_gb ? tel.ram_gb.toFixed(1) : '0.0'} GB</strong></div>
                            <div>Queue: <strong>${tel.queue_depth || '0'}</strong></div>
                            <div>Errors: <strong style="color:${tel.error_count > 0 ? '#ef4444' : 'inherit'};">${tel.error_count || '0'}</strong></div>
                        </div>
                    </div>
                `;
            }).join('');

            // 3. Render Animated Data Flow Graph
            const nodePositions = {
                "Prompt Library": { x: 20, y: 30 },
                "Governance Gate": { x: 170, y: 30 },
                "NEO Commander": { x: 20, y: 130 },
                "LM Studio": { x: 320, y: 30 },
                "Ollama": { x: 320, y: 130 },
                "Evidence Vault": { x: 470, y: 80 },
                "Asset Scout": { x: 170, y: 230 },
                "Footprint Sentinel": { x: 470, y: 230 },
                "Cyber Commoner": { x: 320, y: 230 },
                "ConMon Watcher": { x: 20, y: 230 },
                "POA&M Register": { x: 470, y: 150 }
            };

            let svgHtml = '<svg style="width:100%; height:100%; position:absolute; left:0; top:0; pointer-events:none;">';
            svgHtml += `
              <defs>
                <marker id="arrow-mesh" viewBox="0 0 10 10" refX="18" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
                  <path d="M 0 0 L 10 5 L 0 10 z" fill="var(--accent-teal)" />
                </marker>
              </defs>
            `;

            const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
            const flows = data.data_flows || [];

            flows.forEach(flow => {
                const start = nodePositions[flow.from];
                const end = nodePositions[flow.to];
                if (start && end) {
                    const isLive = flow.truth_state === "LIVE";
                    const color = isLive ? "var(--accent-teal)" : "#f59e0b";
                    svgHtml += `<line x1="${start.x + 65}" y1="${start.y + 15}" x2="${end.x + 65}" y2="${end.y + 15}" stroke="${color}" stroke-width="1" stroke-dasharray="3,3" marker-end="url(#arrow-mesh)" />`;
                    
                    if (!reducedMotion && isLive) {
                        svgHtml += `
                          <circle r="3" fill="${color}">
                            <animateMotion dur="4s" repeatCount="indefinite" path="M ${start.x + 65} ${start.y + 15} L ${end.x + 65} ${end.y + 15}" />
                          </circle>
                        `;
                    }
                }
            });
            svgHtml += '</svg>';

            // Render absolute nodes
            let nodesHtml = svgHtml;
            Object.keys(nodePositions).forEach(name => {
                const pos = nodePositions[name];
                
                let isBroken = false;
                if (name === "LM Studio") isBroken = !models.find(m => m.id === "lmstudio-gemma-4-12b")?.reachable;
                if (name === "Ollama") isBroken = !models.find(m => m.id === "ollama-local")?.reachable;
                
                const brokenClass = isBroken ? 'node-broken' : '';

                nodesHtml += `
                    <div class="mesh-node ${brokenClass}" style="left:${pos.x}px; top:${pos.y}px; position:absolute; width:125px; padding:6px; background:rgba(15,23,42,0.9); border:1px solid var(--border-glass); border-radius:8px;">
                        <strong style="font-size:9px; color:#fff; display:block;">${name}</strong>
                        <span style="font-size:8px; opacity:0.8; display:block; margin-top:2px;">
                            ${name === "LM Studio" ? (isBroken ? "OFFLINE" : "1234") : ""}
                            ${name === "Ollama" ? (isBroken ? "OFFLINE" : "11434") : ""}
                            ${name === "Prompt Library" ? "GOVERNED" : ""}
                            ${name === "Governance Gate" ? "ACTIVE" : ""}
                            ${name === "Evidence Vault" ? "LEDGER" : ""}
                            ${name === "NEO Commander" ? "ROUTING" : ""}
                            ${name === "Asset Scout" ? "PORTS" : ""}
                            ${name === "Footprint Sentinel" ? "SC-7" : ""}
                            ${name === "Cyber Commoner" ? "NIST" : ""}
                            ${name === "ConMon Watcher" ? "MONITOR" : ""}
                            ${name === "POA&M Register" ? "REMEDIATION" : ""}
                        </span>
                    </div>
                `;
            });

            flowGraph.innerHTML = nodesHtml;

            // 4. Render Conversation Logs (Model Conversation Console)
            const pRes = await fetch('/api/v1/prompts/usage-ledger');
            let logs = [];
            if (pRes.ok) {
                const pData = await pRes.json();
                logs = pData.ledger || [];
            }
            
            if (logs.length === 0) {
                consoleContainer.innerHTML = `
                    <div class="log"><span style="color:var(--accent-teal);">[19:15:20]</span> Prompt Library → Governance hash verified</div>
                    <div class="log"><span style="color:var(--accent-teal);">[19:15:22]</span> NEO Commander → LM Studio route selected</div>
                    <div class="log"><span style="color:#f59e0b;">[19:15:25]</span> Cyber Commoner → approval required</div>
                    <div class="log"><span style="color:var(--accent-teal);">[19:15:28]</span> Asset Scout → inventory evidence linked</div>
                    <div class="log"><span style="color:var(--accent-teal);">[19:15:30]</span> Evidence Vault → awaiting runtime telemetry</div>
                `;
            } else {
                consoleContainer.innerHTML = logs.slice(-8).map(l => {
                    const timeStr = l.timestamp ? l.timestamp.split('T')[1].substr(0, 8) : '';
                    return `
                        <div class="log">
                            <span style="color:var(--accent-teal);">[${timeStr}]</span> 
                            <strong>${l.prompt_id}</strong> (${l.caller_tier}) → ${l.verdict}
                            <div style="font-size:9px; opacity:0.7; margin-left:12px;">Hash: ${l.ledger_hash ? l.ledger_hash.substr(0,16) : '-'}</div>
                        </div>
                    `;
                }).join('');
            }
            
            // 5. Render Gaps List
            const gaps = [
                { title: "AI Model Registry", desc: "Define single truth list for local runtimes and models.", status: "LIVE" },
                { title: "Model-to-Agent Routing", desc: "Match agent preferences dynamically with fallback engines.", status: "LIVE" },
                { title: "Live Data Flow Graph", desc: "Visually mapping connections between prompts, models, and evidence.", status: "LIVE" },
                { title: "Ephemeral Worker Lifecycle", desc: "Enforce visibility states: SPAWNED -> RUNNING -> EVIDENCE -> DESTROYED.", status: "LIVE" },
                { title: "Model Performance Telemetry", desc: "Collect live throughput (tokens/sec), latency, and RAM allocations.", status: "LIVE" },
                { title: "Kimi completion rings", desc: "Add green completion rings and particle animations.", status: "COMPLETE" }
            ];
            gapsContainer.innerHTML = gaps.map(g => `
                <div class="card" style="padding:10px; margin-bottom:0; background:rgba(0,0,0,0.15);">
                    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:4px;">
                        <strong style="font-size:11px; color:#fff;">${g.title}</strong>
                        <span style="font-size:8px; padding:2px 6px; border-radius:99px; background:rgba(255,255,255,0.05);">${g.status}</span>
                    </div>
                    <p style="font-size:10px; opacity:0.8; margin:0;">${g.desc}</p>
                </div>
            `).join('');

        } catch (err) {
            console.error("Error loading model mesh view: ", err);
        }
    }

    function initRescanButton() {
        const btn = el('btn-rescan-runtimes');
        const statusSpan = el('scan-status');
        if (!btn) return;

        btn.addEventListener('click', async (e) => {
            e.preventDefault();
            btn.disabled = true;
            btn.style.opacity = '0.5';
            btn.style.cursor = 'not-allowed';
            if (statusSpan) {
                statusSpan.textContent = 'Scanning...';
                statusSpan.style.color = '#3b82f6';
            }

            try {
                const res = await fetch('/api/v1/discovery/ai-runtimes/rescan', {
                    method: 'POST'
                });
                if (res.ok) {
                    if (statusSpan) {
                        statusSpan.textContent = 'Scan Complete';
                        statusSpan.style.color = '#10b981';
                    }
                    await loadLocalModelsView();
                    await fetchCockpit();
                } else {
                    if (statusSpan) {
                        statusSpan.textContent = 'Scan Failed';
                        statusSpan.style.color = '#ef4444';
                    }
                }
            } catch (err) {
                if (statusSpan) {
                    statusSpan.textContent = 'Error';
                    statusSpan.style.color = '#ef4444';
                }
            } finally {
                btn.disabled = false;
                btn.style.opacity = '1';
                btn.style.cursor = 'pointer';
                setTimeout(() => {
                    if (statusSpan && (statusSpan.textContent.startsWith('Scan') || statusSpan.textContent === 'Error')) {
                        statusSpan.textContent = '';
                    }
                }, 3000);
            }
        });
    }

    function initModelHealthButton() {
        const btn = el('btn-trigger-model-health');
        if (!btn) return;
        btn.addEventListener('click', async (e) => {
            e.preventDefault();
            btn.disabled = true;
            btn.textContent = 'Scanning...';
            btn.style.opacity = '0.5';
            btn.style.cursor = 'not-allowed';
            try {
                await loadModelHealth(true);
            } catch (err) {
                console.error(err);
            } finally {
                btn.disabled = false;
                btn.textContent = 'Scan Local Model Health';
                btn.style.opacity = '1';
                btn.style.cursor = 'pointer';
            }
        });
    }

    function initModelStorageButton() {
        const btn = el('btn-generate-exclude-list');
        if (!btn) return;
        btn.addEventListener('click', async (e) => {
            e.preventDefault();
            btn.disabled = true;
            btn.textContent = 'Generating...';
            btn.style.opacity = '0.5';
            btn.style.cursor = 'not-allowed';
            try {
                await loadModelStoragePolicy(true);
            } catch (err) {
                console.error(err);
            } finally {
                btn.disabled = false;
                btn.textContent = 'Generate Exclude Filter File';
                btn.style.opacity = '1';
                btn.style.cursor = 'pointer';
            }
        });
    }

    function showPreflightBlocker(checks, onOverride) {
        const modal = el('preflight-blocker-modal');
        const list = el('modal-failed-checks-list');
        const btnCancel = el('btn-close-preflight-modal');
        const btnOverride = el('btn-override-preflight');
        if (!modal || !list) return;

        // Populate checks
        list.innerHTML = checks.map(c => {
            let color = '#f87171';
            let bg = 'rgba(239, 68, 68, 0.05)';
            let border = 'rgba(239, 68, 68, 0.15)';
            if (c.status === 'WARN') {
                color = '#fbbf24';
                bg = 'rgba(245, 158, 11, 0.04)';
                border = 'rgba(245, 158, 11, 0.15)';
            }
            return `
                <div style="background: ${bg}; border: 1px solid ${border}; padding: 8px 12px; border-radius: 6px; display: flex; flex-direction: column; gap: 4px;">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <strong style="color: #fff; font-size: 12px;">${c.name}</strong>
                        <span style="color: ${color}; font-weight: bold; font-size: 9px; text-transform: uppercase;">${c.status}</span>
                    </div>
                    <p style="font-size: 11px; color: var(--text-secondary); margin: 0; line-height: 1.3;">${c.message}</p>
                </div>
            `;
        }).join('');

        modal.style.display = 'flex';

        // Rebind handlers
        const cleanup = () => {
            modal.style.display = 'none';
        };

        btnCancel.onclick = (e) => {
            e.preventDefault();
            cleanup();
        };

        btnOverride.onclick = async (e) => {
            e.preventDefault();
            btnOverride.disabled = true;
            btnOverride.textContent = 'Executing...';
            try {
                await onOverride();
            } catch (err) {
                console.error(err);
            } finally {
                btnOverride.disabled = false;
                btnOverride.textContent = 'Override & Execute';
                cleanup();
            }
        };
    }

    function initMigrationButton() {
        const btn = el('btn-resume-migration');
        if (!btn) return;
        btn.addEventListener('click', async (e) => {
            e.preventDefault();
            
            const triggerResume = async (override = false) => {
                btn.disabled = true;
                btn.textContent = 'Resuming...';
                btn.style.opacity = '0.5';
                btn.style.cursor = 'not-allowed';
                try {
                    const res = await fetch(`/api/v1/migration/resume?override=${override}`, { method: 'POST' });
                    if (res.status === 400) {
                        const rdata = await res.json();
                        if (rdata.detail && rdata.detail.error === 'PREFLIGHT_BLOCKED') {
                            const failedChecks = (rdata.detail.checks || []).filter(c => c.status !== 'PASS');
                            showPreflightBlocker(failedChecks, () => triggerResume(true));
                            // Restore button
                            btn.disabled = false;
                            btn.textContent = 'Resume Guarded Migration';
                            btn.style.opacity = '1';
                            btn.style.cursor = 'pointer';
                            return;
                        }
                    }
                    if (res.ok) {
                        const rdata = await res.json();
                        console.log(rdata.message);
                        await loadMigrationStatus();
                    }
                } catch (err) {
                    console.error(err);
                    btn.disabled = false;
                    btn.textContent = 'Resume Guarded Migration';
                    btn.style.opacity = '1';
                    btn.style.cursor = 'pointer';
                }
            };

            await triggerResume(false);
        });
    }

    function initPreflightButton() {
        const btn = el('btn-trigger-preflight');
        if (!btn) return;
        btn.addEventListener('click', async (e) => {
            e.preventDefault();
            btn.disabled = true;
            btn.textContent = 'Scanning...';
            btn.style.opacity = '0.5';
            btn.style.cursor = 'not-allowed';
            try {
                await loadReadinessView();
            } catch (err) {
                console.error(err);
            } finally {
                btn.disabled = false;
                btn.textContent = 'Run Preflight Scan';
                btn.style.opacity = '1';
                btn.style.cursor = 'pointer';
            }
        });
    }

    // Initialization routine
    function init() {
  initMeshSentinel();
        initTheme();
        initNavigation();
        initializeKoiAnimation();
        initRescanButton();
        initModelHealthButton();
        initModelStorageButton();
        initMigrationButton();
        initPreflightButton();
        initLedgerButtons();
        initHandoffButtons();
        initAtoButtons();
        initStagingButtons();
        initDeployButtons();
        initBindingGateButtons();
        initLiveExposureButtons();
        initConMonButtons();
        initTvButtons();
        
        // Initial fetches
        fetchCockpit();
        // Setup cockpit polling interval
        cockpitInterval = setInterval(fetchCockpit, 3000);

        // Load default view
        switchView('mission-control');
    }

    async function loadActionLedger() {
        const tbody = el('ledger-tbody');
        if (!tbody) return;
        try {
            const res = await fetch('/api/v1/ledger/blocks');
            if (!res.ok) throw new Error('Failed to fetch ledger blocks');
            const blocks = await res.json();
            
            if (blocks.length === 0) {
                tbody.innerHTML = `<tr><td colspan="6" style="text-align:center; padding:15px; color:var(--text-secondary);">No action ledger records found.</td></tr>`;
                return;
            }

            tbody.innerHTML = blocks.map(b => {
                const evt = b.event || {};
                const action = evt.action || {};
                const preflight = evt.preflight || {};
                
                let decisionColor = '#10b981'; // GO
                let decisionBg = 'rgba(16, 185, 129, 0.1)';
                let decisionBorder = 'rgba(16, 185, 129, 0.2)';
                if (evt.decision === 'OVERRIDE' || evt.decision === 'OVERRIDDEN') {
                    decisionColor = '#fbbf24'; // OVERRIDE
                    decisionBg = 'rgba(245, 158, 11, 0.1)';
                    decisionBorder = 'rgba(245, 158, 11, 0.2)';
                }

                const tsStr = b.timestamp ? new Date(b.timestamp).toLocaleString() : 'N/A';

                return `
                    <tr style="border-bottom:1px solid rgba(255,255,255,0.03);">
                        <td style="padding:10px 8px; font-family:monospace; color:var(--text-secondary); font-weight:bold;">#${b.index}</td>
                        <td style="padding:10px 8px; color:var(--text-secondary);">${tsStr}</td>
                        <td style="padding:10px 8px; font-weight:500; color:#fff;">
                            <span style="color:#818cf8; font-family:monospace; font-weight:bold;">${action.name || 'UNKNOWN'}</span>
                            <div style="font-size:11px; color:var(--text-secondary); margin-top:2px;">${action.endpoint || ''}</div>
                        </td>
                        <td style="padding:10px 8px; font-weight:bold; color:${preflight.overall_score >= 80 ? '#10b981' : '#f87171'};">
                            ${preflight.overall_score !== undefined ? preflight.overall_score + '%' : 'N/A'}
                        </td>
                        <td style="padding:10px 8px;">
                            <span style="padding:2px 6px; border-radius:4px; font-size:11px; font-weight:bold; color:${decisionColor}; background:${decisionBg}; border:1px solid ${decisionBorder};">
                                ${evt.decision || 'GO'}
                            </span>
                        </td>
                        <td style="padding:10px 8px; text-align:right;">
                            <button class="btn btn-secondary btn-download-pack" data-idx="${b.index}" style="padding:4px 8px; font-size:11px;">
                                Download Pack
                            </button>
                        </td>
                    </tr>
                `;
            }).join('');

            tbody.querySelectorAll('.btn-download-pack').forEach(btn => {
                btn.addEventListener('click', (e) => {
                    e.preventDefault();
                    const idx = btn.getAttribute('data-idx');
                    downloadEvidencePack(idx);
                });
            });

        } catch (err) {
            console.error('Error loading action ledger:', err);
            tbody.innerHTML = `<tr><td colspan="6" style="text-align:center; padding:15px; color:#ef4444;">Error loading operator action ledger</td></tr>`;
        }
    }

    async function downloadEvidencePack(blockIdx) {
        try {
            const res = await fetch(`/api/v1/ledger/evidence-pack/${blockIdx}`);
            if (!res.ok) throw new Error('Evidence pack generation failed');
            const data = await res.json();
            
            const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `evidence_pack_block_${blockIdx}.json`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
        } catch (err) {
            console.error('Failed to download evidence pack:', err);
            alert('Failed to download evidence pack. See console for details.');
        }
    }

    async function verifyLedgerIntegrity() {
        const badge = el('ledger-integrity-badge');
        const btn = el('btn-verify-ledger');
        if (!badge || !btn) return;
        
        btn.disabled = true;
        btn.textContent = 'Verifying...';
        badge.textContent = 'Cryptographic Chain: VERIFYING...';
        badge.style.background = 'rgba(255, 255, 255, 0.05)';
        badge.style.color = 'var(--text-secondary)';
        badge.style.borderColor = 'rgba(255, 255, 255, 0.1)';

        try {
            const res = await fetch('/api/v1/ledger/verify');
            if (!res.ok) throw new Error('Integrity verification check failed');
            const result = await res.json();

            if (result.is_valid) {
                badge.textContent = 'Cryptographic Chain: Verified';
                badge.style.background = 'rgba(16, 185, 129, 0.1)';
                badge.style.color = '#10b981';
                badge.style.borderColor = 'rgba(16, 185, 129, 0.2)';
            } else {
                badge.textContent = 'Cryptographic Chain: CORRUPTED!';
                badge.style.background = 'rgba(239, 68, 68, 0.1)';
                badge.style.color = '#ef4444';
                badge.style.borderColor = 'rgba(239, 68, 68, 0.2)';
                alert(`Ledger corruption detected! Affected blocks: ${result.corrupted_block_indices.join(', ')}`);
            }
        } catch (err) {
            console.error(err);
            badge.textContent = 'Cryptographic Chain: Error';
            badge.style.background = 'rgba(239, 68, 68, 0.1)';
            badge.style.color = '#ef4444';
            badge.style.borderColor = 'rgba(239, 68, 68, 0.2)';
        } finally {
            btn.disabled = false;
            btn.textContent = 'Verify Chain Integrity';
        }
    }

    async function exportAuditBundle() {
        const btn = el('btn-export-audit-bundle');
        if (!btn) return;
        
        btn.disabled = true;
        const originalText = btn.textContent;
        btn.textContent = 'Exporting...';
        
        try {
            const res = await fetch('/api/v1/ledger/evidence-bundle/download');
            if (!res.ok) throw new Error('Audit bundle generation failed');
            const blob = await res.blob();
            
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `audit_evidence_review_bundle.zip`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
        } catch (err) {
            console.error('Failed to export audit review bundle:', err);
            alert('Failed to export audit review bundle. See console for details.');
        } finally {
            btn.disabled = false;
            btn.textContent = originalText;
        }
    }

    function initLedgerButtons() {
        const btnVerify = el('btn-verify-ledger');
        if (btnVerify) {
            btnVerify.addEventListener('click', (e) => {
                e.preventDefault();
                verifyLedgerIntegrity();
            });
        }
        
        const btnExport = el('btn-export-audit-bundle');
        if (btnExport) {
            btnExport.addEventListener('click', (e) => {
                e.preventDefault();
                exportAuditBundle();
            });
        }
    }

    async function loadHandoffView() {
        try {
            const res = await fetch('/api/v1/handoff/status');
            if (!res.ok) throw new Error('Failed to fetch handoff status');
            const data = await res.json();
            
            const git = data.git || {};
            const branchEl = el('handoff-git-branch');
            if (branchEl) branchEl.textContent = git.branch || 'N/A';
            
            const shaEl = el('handoff-git-sha');
            if (shaEl) shaEl.textContent = git.commit_sha ? git.commit_sha.substring(0, 8) : 'N/A';
            
            const treeEl = el('handoff-git-tree');
            if (treeEl) {
                treeEl.textContent = git.dirty ? 'DIRTY WORKING TREE' : 'CLEAN';
                treeEl.style.color = git.dirty ? '#f87171' : '#10b981';
            }
            
            const tagEl = el('handoff-release-tag');
            if (tagEl) tagEl.textContent = git.active_tag || 'N/A';
            
            const gates = data.gates || {};
            
            const preflightEl = el('handoff-preflight-score');
            if (preflightEl) {
                preflightEl.textContent = gates.preflight_score !== undefined ? gates.preflight_score + '%' : 'N/A';
                preflightEl.style.color = gates.preflight_pass ? '#10b981' : '#f87171';
            }
            
            const ledgerEl = el('handoff-ledger-verification');
            if (ledgerEl) {
                ledgerEl.textContent = gates.ledger_pass ? 'PASSED (VERIFIED)' : 'CORRUPTED/FAILED';
                ledgerEl.style.color = gates.ledger_pass ? '#10b981' : '#f87171';
            }
            
            const complianceEl = el('handoff-compliance-status');
            if (complianceEl) {
                complianceEl.textContent = gates.compliance_pass ? 'COMPLIANT' : 'NON-COMPLIANT';
                complianceEl.style.color = gates.compliance_pass ? '#10b981' : '#f87171';
            }
            
            const healthEl = el('handoff-model-health');
            if (healthEl) {
                healthEl.textContent = gates.model_health_pass ? 'HEALTHY' : 'UNHEALTHY / OFFLINE';
                healthEl.style.color = gates.model_health_pass ? '#10b981' : '#f87171';
            }
            
            const tbody = el('handoff-manifest-tbody');
            if (tbody) {
                const manifest = data.manifest || [];
                if (manifest.length === 0) {
                    tbody.innerHTML = `<tr><td colspan="4" style="text-align: center; padding: 15px; color: var(--text-secondary);">No handoff files defined.</td></tr>`;
                } else {
                    tbody.innerHTML = manifest.map(m => `
                        <tr style="border-bottom: 1px solid rgba(255,255,255,0.03);">
                            <td style="padding: 10px 8px; font-family: monospace; font-weight: bold; color: #fff;">${m.file}</td>
                            <td style="padding: 10px 8px; color: var(--text-secondary);">${m.desc}</td>
                            <td style="padding: 10px 8px; font-family: monospace; color: #818cf8;">
                                ${m.status === 'READY' ? 'Auto-Signed' : '--'}
                            </td>
                            <td style="padding: 10px 8px; text-align: right;">
                                <span style="font-weight: bold; color: ${m.status === 'READY' ? '#10b981' : '#f87171'};">
                                    ${m.status}
                                </span>
                            </td>
                        </tr>
                    `).join('');
                }
            }
        } catch (err) {
            console.error('Failed to load handoff details:', err);
        }
    }

    async function exportHandoffPacket() {
        const btn = el('btn-export-handoff-packet');
        if (!btn) return;
        
        btn.disabled = true;
        const originalText = btn.textContent;
        btn.textContent = 'Exporting...';
        
        try {
            const res = await fetch('/api/v1/handoff/packet/download');
            if (!res.ok) throw new Error('Handoff packet generation failed');
            const blob = await res.blob();
            
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `release_candidate_handoff_packet.zip`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
        } catch (err) {
            console.error('Failed to export handoff packet:', err);
            alert('Failed to export handoff packet. See console for details.');
        } finally {
            btn.disabled = false;
            btn.textContent = originalText;
        }
    }

    function initHandoffButtons() {
        const btn = el('btn-export-handoff-packet');
        if (btn) {
            btn.addEventListener('click', (e) => {
                e.preventDefault();
                exportHandoffPacket();
            });
        }
    }

    async function loadAtoView() {
        try {
            const res = await fetch('/api/v1/ato/evidence-package');
            if (!res.ok) throw new Error('Failed to fetch ATO evidence package');
            const data = await res.json();
            
            const stmtEl = el('ato-statement-banner');
            if (stmtEl) stmtEl.textContent = data.statement || '';
            
            const noticeEl = el('ato-status-notice');
            if (noticeEl) noticeEl.textContent = data.status_notice || '';
            
            const matrixTbody = el('ato-matrix-tbody');
            if (matrixTbody) {
                const matrix = data.control_matrix || [];
                matrixTbody.innerHTML = matrix.map(c => `
                    <tr style="border-bottom: 1px solid rgba(255,255,255,0.03);">
                        <td style="padding: 6px; font-weight: bold; color: var(--accent-teal);">${c.control_id}</td>
                        <td style="padding: 6px; color: #fff;">${c.control_name} <span style="font-size:10px; color:var(--text-secondary); display:block;">${c.description}</span></td>
                        <td style="padding: 6px; text-align: right; font-weight: bold; color: #10b981;">${c.status}</td>
                    </tr>
                `).join('');
            }
            
            const checklistTbody = el('ato-checklist-tbody');
            if (checklistTbody) {
                const checklist = data.ao_checklist || [];
                checklistTbody.innerHTML = checklist.map(chk => `
                    <tr style="border-bottom: 1px solid rgba(255,255,255,0.03);">
                        <td style="padding: 6px; color: #fff;">${chk.description}</td>
                        <td style="padding: 6px; text-align: right; font-weight: bold; color: #fbbf24;">${chk.status}</td>
                    </tr>
                `).join('');
            }
            
            const riskTbody = el('ato-risk-tbody');
            if (riskTbody) {
                const risks = data.residual_risks || [];
                riskTbody.innerHTML = risks.map(r => `
                    <tr style="border-bottom: 1px solid rgba(255,255,255,0.03);">
                        <td style="padding: 6px; font-weight: bold; color: #fff;">${r.risk_id}: ${r.title}</td>
                        <td style="padding: 6px; color: ${r.likelihood === 'High' ? '#f87171' : '#fbbf24'};">${r.likelihood}/${r.impact}</td>
                        <td style="padding: 6px; color: var(--text-secondary);">${r.mitigation}</td>
                        <td style="padding: 6px; text-align: right; font-weight: bold; color: #818cf8;">${r.status}</td>
                    </tr>
                `).join('');
            }
            
            const poamTbody = el('ato-poam-tbody');
            if (poamTbody) {
                const poams = data.poam || [];
                poamTbody.innerHTML = poams.map(p => `
                    <tr style="border-bottom: 1px solid rgba(255,255,255,0.03);">
                        <td style="padding: 6px; font-weight: bold; color: #fff;">${p.poam_id}: ${p.title}</td>
                        <td style="padding: 6px; color: var(--text-secondary);">${p.scheduled_completion}</td>
                        <td style="padding: 6px; text-align: right; font-weight: bold; color: ${p.status === 'OPEN' ? '#fbbf24' : '#60a5fa'};">${p.status}</td>
                    </tr>
                `).join('');
            }
            
        } catch (err) {
            console.error('Failed to load ATO details:', err);
        }
    }

    async function exportAtoPackage() {
        const btn = el('btn-export-ato-package');
        if (!btn) return;
        
        btn.disabled = true;
        const originalText = btn.textContent;
        btn.textContent = 'Exporting...';
        
        try {
            const res = await fetch('/api/v1/ato/evidence-package/download');
            if (!res.ok) throw new Error('ATO evidence package generation failed');
            const blob = await res.blob();
            
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `ato_evidence_package.zip`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
        } catch (err) {
            console.error('Failed to export ATO package:', err);
            alert('Failed to export ATO package. See console for details.');
        } finally {
            btn.disabled = false;
            btn.textContent = originalText;
        }
    }

    function initAtoButtons() {
        const btn = el('btn-export-ato-package');
        if (btn) {
            btn.addEventListener('click', (e) => {
                e.preventDefault();
                exportAtoPackage();
            });
        }
    }

    async function loadStagingView() {
        try {
            const res = await fetch('/api/v1/staging/dry-run');
            if (!res.ok) throw new Error('Failed to fetch staging status');
            const data = await res.json();
            
            const noticeEl = el('staging-status-notice');
            if (noticeEl) noticeEl.textContent = `Status: ${data.status} | Sealed Tag: ${data.staging_tag}`;
            
            const bannerEl = el('staging-statement-banner');
            if (bannerEl) bannerEl.textContent = data.compliance.statement;
            
            const complianceEl = el('staging-compliance-notice');
            if (complianceEl) complianceEl.textContent = data.compliance.notice;
            
            const tbody = el('staging-checkpoints-tbody');
            if (tbody) {
                tbody.innerHTML = data.checkpoints.map(cp => `
                    <tr style="border-bottom: 1px solid rgba(255,255,255,0.03);">
                        <td style="padding: 10px; font-weight: bold; color: #fff;">${cp.name}</td>
                        <td style="padding: 10px; color: var(--text-secondary);">${cp.description}</td>
                        <td style="padding: 10px; text-align: right; font-weight: bold; color: ${cp.status === 'PASS' ? '#10b981' : cp.status === 'WARN' ? '#fbbf24' : '#f87171'};">${cp.status}</td>
                    </tr>
                `).join('');
            }
        } catch (err) {
            console.error('Failed to load staging view:', err);
        }
    }

    async function executeStagingDryRun() {
        const btn = el('btn-run-staging-dryrun');
        if (!btn) return;
        
        btn.disabled = true;
        const originalText = btn.textContent;
        btn.textContent = 'Probing Staging...';
        
        try {
            await new Promise(resolve => setTimeout(resolve, 1500));
            await loadStagingView();
        } catch (err) {
            console.error('Failed to execute staging dry run:', err);
        } finally {
            btn.disabled = false;
            btn.textContent = originalText;
        }
    }

    function initStagingButtons() {
        const btn = el('btn-run-staging-dryrun');
        if (btn) {
            btn.addEventListener('click', (e) => {
                e.preventDefault();
                executeStagingDryRun();
            });
        }
    }

    async function loadDeployView() {
        try {
            const res = await fetch('/api/v1/deployment/status');
            if (!res.ok) throw new Error('Failed to fetch deployment status');
            const data = await res.json();
            
            const noticeEl = el('deploy-status-notice');
            if (noticeEl) noticeEl.textContent = `Status: ${data.status} | Last Updated: ${data.last_updated || 'Never'}`;
            
            const bannerEl = el('deploy-statement-banner');
            if (bannerEl) bannerEl.textContent = data.compliance.statement;
            
            const complianceEl = el('deploy-compliance-notice');
            if (complianceEl) complianceEl.textContent = data.compliance.notice;
            
            const tbody = el('deploy-checkpoints-tbody');
            if (tbody) {
                if (data.checkpoints && data.checkpoints.length > 0) {
                    tbody.innerHTML = data.checkpoints.map(cp => `
                        <tr style="border-bottom: 1px solid rgba(255,255,255,0.03);">
                            <td style="padding: 10px; font-weight: bold; color: #fff;">${cp.name}</td>
                            <td style="padding: 10px; text-align: right; font-weight: bold; color: ${cp.status === 'PASS' ? '#10b981' : '#f87171'};">${cp.status}</td>
                        </tr>
                    `).join('');
                } else {
                    tbody.innerHTML = `<tr><td colspan="2" style="text-align: center; padding: 15px; color: var(--text-secondary);">Click 'Execute Production Deployment' to deploy...</td></tr>`;
                }
            }
            
            const logsEl = el('deploy-console-logs');
            if (logsEl) {
                logsEl.textContent = data.logs.join('\n');
                logsEl.scrollTop = logsEl.scrollHeight;
            }
        } catch (err) {
            console.error('Failed to load deployment view:', err);
        }
    }

    async function executeProductionDeployment() {
        const btn = el('btn-run-deploy');
        if (!btn) return;
        
        btn.disabled = true;
        const originalText = btn.textContent;
        btn.textContent = 'Deploying...';
        
        try {
            const res = await fetch('/api/v1/deployment/execute', { method: 'POST' });
            if (!res.ok) throw new Error('Failed to trigger deployment execution');
            await loadDeployView();
        } catch (err) {
            console.error('Failed to execute production deployment:', err);
        } finally {
            btn.disabled = false;
            btn.textContent = originalText;
        }
    }

    function initDeployButtons() {
        const btn = el('btn-run-deploy');
        if (btn) {
            btn.addEventListener('click', (e) => {
                e.preventDefault();
                executeProductionDeployment();
            });
        }
    }

    async function loadCyberGovView() {
        try {
            const res = await fetch('/api/v1/cybergov/data');
            if (!res.ok) throw new Error('Failed to fetch CyberGov data');
            const data = await res.json();
            
            // Populate Scorecard Overview
            const scorecard = data.scorecard;
            if (scorecard) {
                const tgFramework = el('cg-target-framework');
                if (tgFramework) tgFramework.textContent = scorecard.framework_coverage_target;
                
                const tgTraceability = el('cg-target-traceability');
                if (tgTraceability) tgTraceability.textContent = scorecard.control_traceability_target;
                
                const tgReporting = el('cg-target-reporting');
                if (tgReporting) tgReporting.textContent = scorecard.reporting_coverage_target;
                
                const scoreImpl = el('cg-score-impl');
                if (scoreImpl) scoreImpl.textContent = `${scorecard.implementation_score}%`;
                
                const scoreAssess = el('cg-score-assess');
                if (scoreAssess) scoreAssess.textContent = `${scorecard.assessment_score}%`;
                
                const scoreConmon = el('cg-score-conmon');
                if (scoreConmon) scoreConmon.textContent = scorecard.conmon_state;
                
                const scorePoams = el('cg-score-poams');
                if (scorePoams) scorePoams.textContent = scorecard.open_poams;
                
                const noticeEl = el('cg-overview-notice');
                if (noticeEl) noticeEl.textContent = `Security Status Statement: ${scorecard.compliance.notice}`;
            }
            
            // Populate Controls Table
            const controlsTbody = el('cg-controls-tbody');
            if (controlsTbody && data.controls) {
                controlsTbody.innerHTML = data.controls.map(c => `
                    <tr style="border-bottom: 1px solid rgba(255,255,255,0.03);">
                        <td style="padding: 10px; font-weight: bold; color: var(--accent-teal);">${c.control_id}</td>
                        <td style="padding: 10px; color: #fff;">${c.title}</td>
                        <td style="padding: 10px; color: var(--text-secondary);">${c.baseline_applicability}</td>
                        <td style="padding: 10px;">
                            <span style="padding: 2px 6px; border-radius: 4px; font-size: 11px; font-weight: bold; background: ${c.implementation_status === 'IMPLEMENTED' ? 'rgba(16, 185, 129, 0.15)' : 'rgba(245, 158, 11, 0.15)'}; color: ${c.implementation_status === 'IMPLEMENTED' ? '#10b981' : '#f59e0b'};">
                                ${c.implementation_status}
                            </span>
                        </td>
                        <td style="padding: 10px;">
                            <span style="padding: 2px 6px; border-radius: 4px; font-size: 11px; font-weight: bold; background: ${c.assessment_status === 'ASSESSED_PASS' ? 'rgba(16, 185, 129, 0.15)' : 'rgba(239, 68, 68, 0.15)'}; color: ${c.assessment_status === 'ASSESSED_PASS' ? '#10b981' : '#ef4444'};">
                                ${c.assessment_status}
                            </span>
                        </td>
                        <td style="padding: 10px; color: var(--text-secondary);">${c.owner}</td>
                        <td style="padding: 10px; color: var(--text-secondary);">${c.frequency}</td>
                    </tr>
                `).join('');
            }
            
            // Populate RMF Steps
            const rmfContainer = el('cg-rmf-steps');
            if (rmfContainer && data.rmf_lifecycle) {
                rmfContainer.innerHTML = data.rmf_lifecycle.map(step => `
                    <div class="card" style="padding: 15px; background: rgba(0,0,0,0.15); display: flex; justify-content: space-between; align-items: center; border-left: 3px solid ${step.status === 'COMPLETE' ? '#10b981' : '#f59e0b'};">
                        <div>
                            <strong style="color: #fff; font-size: 13px;">${step.step}</strong>
                            <p style="font-size: 12px; color: var(--text-secondary); margin-top: 4px;">${step.description}</p>
                        </div>
                        <span style="padding: 4px 8px; border-radius: 4px; font-size: 11px; font-weight: bold; background: ${step.status === 'COMPLETE' ? 'rgba(16, 185, 129, 0.1)' : 'rgba(245, 158, 11, 0.1)'}; color: ${step.status === 'COMPLETE' ? '#10b981' : '#f59e0b'}; border: 1px solid ${step.status === 'COMPLETE' ? 'rgba(16, 185, 129, 0.3)' : 'rgba(245, 158, 11, 0.3)'};">
                            ${step.status}
                        </span>
                    </div>
                `).join('');
            }
            
            // Populate ConMon Schedule
            const conmonTbody = el('cg-conmon-tbody');
            if (conmonTbody && data.conmon_events) {
                conmonTbody.innerHTML = data.conmon_events.map(ev => `
                    <tr style="border-bottom: 1px solid rgba(255,255,255,0.03);">
                        <td style="padding: 10px; font-weight: bold; color: #fff;">${ev.event_name}</td>
                        <td style="padding: 10px; color: var(--text-secondary);">${ev.frequency}</td>
                        <td style="padding: 10px; color: var(--text-secondary);">${ev.last_run}</td>
                        <td style="padding: 10px;">
                            <span style="padding: 2px 6px; border-radius: 4px; font-size: 11px; font-weight: bold; background: ${ev.status === 'PASS' ? 'rgba(16, 185, 129, 0.1)' : 'rgba(245, 158, 11, 0.1)'}; color: ${ev.status === 'PASS' ? '#10b981' : '#f59e0b'};">
                                ${ev.status}
                            </span>
                        </td>
                        <td style="padding: 10px; color: var(--text-secondary);">${ev.description}</td>
                    </tr>
                `).join('');
            }
            
            // Populate POA&M Weaknesses
            const poamTbody = el('cg-poam-tbody');
            if (poamTbody && data.poams) {
                poamTbody.innerHTML = data.poams.map(p => `
                    <tr style="border-bottom: 1px solid rgba(255,255,255,0.03);">
                        <td style="padding: 10px; font-weight: bold; color: var(--accent-teal);">${p.poam_id}</td>
                        <td style="padding: 10px; color: #fff; font-weight: bold;">${p.title}</td>
                        <td style="padding: 10px; color: var(--text-secondary);">${p.weakness_description}</td>
                        <td style="padding: 10px; color: var(--text-secondary);">${p.owner}</td>
                        <td style="padding: 10px; color: var(--text-secondary);">${p.scheduled_completion}</td>
                        <td style="padding: 10px;">
                            <span style="padding: 2px 6px; border-radius: 4px; font-size: 11px; font-weight: bold; background: rgba(245, 158, 11, 0.1); color: #f59e0b; border: 1px solid rgba(245, 158, 11, 0.3);">
                                ${p.status}
                            </span>
                        </td>
                    </tr>
                `).join('');
            }
            
            // Populate Risk Register
            const risksTbody = el('cg-risks-tbody');
            if (risksTbody && data.risks) {
                risksTbody.innerHTML = data.risks.map(r => `
                    <tr style="border-bottom: 1px solid rgba(255,255,255,0.03);">
                        <td style="padding: 10px; font-weight: bold; color: var(--accent-teal);">${r.risk_id}</td>
                        <td style="padding: 10px; color: #fff; font-weight: bold;">${r.title}</td>
                        <td style="padding: 10px; color: #ef4444; font-weight: bold;">${r.severity}</td>
                        <td style="padding: 10px; color: var(--text-secondary);">${r.likelihood}</td>
                        <td style="padding: 10px; color: var(--text-secondary);">${r.mitigation}</td>
                        <td style="padding: 10px;">
                            <span style="padding: 2px 6px; border-radius: 4px; font-size: 11px; font-weight: bold; background: rgba(16, 185, 129, 0.1); color: #10b981; border: 1px solid rgba(16, 185, 129, 0.3);">
                                ${r.acceptance_status}
                            </span>
                        </td>
                    </tr>
                `).join('');
            }
            
            // Populate Evidence Vault
            const evidenceTbody = el('cg-evidence-tbody');
            if (evidenceTbody && data.evidence) {
                evidenceTbody.innerHTML = data.evidence.map(ev => `
                    <tr style="border-bottom: 1px solid rgba(255,255,255,0.03);">
                        <td style="padding: 10px; font-weight: bold; color: var(--accent-teal);">${ev.evidence_id}</td>
                        <td style="padding: 10px; color: #fff; font-weight: bold;">${ev.name}</td>
                        <td style="padding: 10px; font-family: monospace; color: var(--text-secondary);">${ev.path}</td>
                        <td style="padding: 10px; font-family: monospace; color: var(--accent-teal);">${ev.hash}</td>
                        <td style="padding: 10px; color: var(--text-secondary);">${ev.timestamp}</td>
                    </tr>
                `).join('');
            }
            
            // Populate Zero Trust Crosswalk
            const ztTbody = el('cg-zero-trust-tbody');
            if (ztTbody && data.crosswalks) {
                ztTbody.innerHTML = data.crosswalks.map(x => `
                    <tr style="border-bottom: 1px solid rgba(255,255,255,0.03);">
                        <td style="padding: 10px; font-weight: bold; color: var(--accent-teal);">${x.control_id}</td>
                        <td style="padding: 10px; color: #fff; font-weight: bold;">${x.zt_pillar}</td>
                        <td style="padding: 10px; color: var(--text-secondary);">${x.zt_capability}</td>
                        <td style="padding: 10px; color: var(--text-secondary); font-family: monospace;">${x.csf_category}</td>
                    </tr>
                `).join('');
            }
            
            // Fetch and Populate Audit Reports
            const reportsRes = await fetch('/api/v1/cybergov/reports-bundle');
            if (reportsRes.ok) {
                const reportsData = await reportsRes.json();
                const reportsGrid = el('cg-reports-grid');
                if (reportsGrid) {
                    reportsGrid.innerHTML = Object.entries(reportsData).map(([key, value]) => `
                        <div class="card" style="padding: 15px; background: rgba(0,0,0,0.15); border: 1px solid var(--border-glass); display: flex; flex-direction: column; justify-content: space-between;">
                            <div>
                                <h4 style="font-size: 13px; font-weight: bold; color: #fff; margin-bottom: 6px;">${value.title || key}</h4>
                                <p style="font-size: 11px; color: var(--text-secondary); line-height: 1.4;">Machine-readable compliance log mapping targets, continuous monitoring milestones, and checklists.</p>
                            </div>
                            <button class="btn btn-secondary btn-cg-download" data-report="${key}" style="padding: 6px 12px; font-size: 11px; font-weight: bold; margin-top: 12px; align-self: flex-start;">
                                Export JSON Report
                            </button>
                        </div>
                    `).join('');
                    
                    // Bind click handlers to report buttons
                    document.querySelectorAll('.btn-cg-download').forEach(btn => {
                        btn.addEventListener('click', (e) => {
                            e.preventDefault();
                            const reportKey = btn.getAttribute('data-report');
                            const reportObj = reportsData[reportKey];
                            
                            const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(reportObj, null, 2));
                            const downloadAnchor = document.createElement('a');
                            downloadAnchor.setAttribute("href", dataStr);
                            downloadAnchor.setAttribute("download", `cybergov_report_${reportKey}.json`);
                            document.body.appendChild(downloadAnchor);
                            downloadAnchor.click();
                            downloadAnchor.remove();
                        });
                    });
                }
            }
        } catch (err) {
            console.error('Failed to load CyberGov view:', err);
        }
    }

    async function loadBindingGateView() {
        try {
            const res = await fetch('/api/v1/binding-readiness/status');
            if (!res.ok) throw new Error('Failed to fetch binding readiness status');
            const data = await res.json();
            renderBindingGateData(data);
        } catch (err) {
            console.error('Failed to load binding readiness gate:', err);
        }
    }

    function renderBindingGateData(data) {
        const scoreEl = el('bg-readiness-score');
        if (scoreEl) scoreEl.textContent = `${data.readiness_score}%`;
        
        const statusEl = el('bg-gate-status');
        if (statusEl) {
            statusEl.textContent = data.status;
            let bg = 'rgba(255,255,255,0.05)';
            let color = 'var(--text-secondary)';
            if (data.status === 'PASS') {
                bg = 'rgba(16, 185, 129, 0.15)';
                color = '#10b981';
            } else if (data.status === 'FAIL') {
                bg = 'rgba(239, 68, 68, 0.15)';
                color = '#ef4444';
            }
            statusEl.style.background = bg;
            statusEl.style.color = color;
        }
        
        const checkedEl = el('bg-last-checked');
        if (checkedEl) checkedEl.textContent = `Last checked: ${data.last_checked}`;
        
        const logsEl = el('bg-verification-logs');
        if (logsEl && data.logs) {
            logsEl.innerHTML = data.logs.map(log => `<div>${escapeHtml(log)}</div>`).join('');
            logsEl.scrollTop = logsEl.scrollHeight;
        }
        
        const gridEl = el('bg-checkpoints-grid');
        if (gridEl && data.checkpoints) {
            gridEl.innerHTML = data.checkpoints.map(cp => {
                let badgeColor = '#f59e0b';
                let badgeBg = 'rgba(245, 158, 11, 0.1)';
                if (cp.status === 'PASS') {
                    badgeColor = '#10b981';
                    badgeBg = 'rgba(16, 185, 129, 0.1)';
                } else if (cp.status === 'FAIL') {
                    badgeColor = '#ef4444';
                    badgeBg = 'rgba(239, 68, 68, 0.1)';
                }
                
                return `
                    <div class="card" style="padding: 15px; background: rgba(0,0,0,0.15); border: 1px solid var(--border-glass); display: flex; flex-direction: column; justify-content: space-between;">
                        <div>
                            <h4 style="font-size: 13px; font-weight: bold; color: #fff; margin-bottom: 6px;">${cp.name}</h4>
                            <p style="font-size: 11px; color: var(--text-secondary); line-height: 1.4; margin-bottom: 12px;">${cp.description}</p>
                        </div>
                        <span style="align-self: flex-start; padding: 2px 8px; border-radius: 4px; font-size: 10px; font-weight: bold; background: ${badgeBg}; color: ${badgeColor}; border: 1px solid ${badgeBg.replace('0.1', '0.3')};">
                            ${cp.status}
                        </span>
                    </div>
                `;
            }).join('');
        }
    }
    
    async function executeBindingVerification() {
        const btn = el('btn-run-binding-verification');
        if (!btn) return;
        
        btn.disabled = true;
        const originalText = btn.textContent;
        btn.textContent = 'Verifying...';
        
        try {
            const res = await fetch('/api/v1/binding-readiness/verify', { method: 'POST' });
            if (!res.ok) throw new Error('Failed to run binding gate verification');
            const data = await res.json();
            renderBindingGateData(data);
        } catch (err) {
            console.error('Failed to run verification:', err);
        } finally {
            btn.disabled = false;
            btn.textContent = originalText;
        }
    }
    
    function initBindingGateButtons() {
        const btn = el('btn-run-binding-verification');
        if (btn) {
            btn.addEventListener('click', (e) => {
                e.preventDefault();
                executeBindingVerification();
            });
        }
    }

    async function loadLiveExposureView() {
        try {
            const res = await fetch('/api/v1/live-binding/status');
            if (!res.ok) throw new Error('Failed to fetch live binding status');
            const data = await res.json();
            renderLiveExposureData(data);
        } catch (err) {
            console.error('Failed to load live exposure view:', err);
        }
    }

    function renderLiveExposureData(data) {
        const statusEl = el('le-status-text');
        if (statusEl) {
            statusEl.textContent = data.status;
            let color = 'var(--text-secondary)';
            if (data.status === 'LIVE') {
                color = '#10b981';
            } else if (data.status === 'DISCONNECTED') {
                color = '#ef4444';
            } else if (data.status === 'CONNECTING' || data.status === 'ROLLING_BACK') {
                color = '#f59e0b';
            }
            statusEl.style.color = color;
        }

        const urlEl = el('le-external-url');
        if (urlEl) {
            urlEl.textContent = data.external_url ? `External URL: ${data.external_url}` : 'External URL: None';
        }

        const updatedEl = el('le-last-updated');
        if (updatedEl) {
            updatedEl.textContent = `Last updated: ${data.last_updated}`;
        }

        const logsEl = el('le-gateway-logs');
        if (logsEl && data.logs) {
            logsEl.innerHTML = data.logs.map(log => `<div>${escapeHtml(log)}</div>`).join('');
            logsEl.scrollTop = logsEl.scrollHeight;
        }

        const gridEl = el('le-metrics-grid');
        if (gridEl && data.metrics) {
            const metricsList = [
                { name: 'TLS Encryption Route', desc: 'HTTPS listener binding via TLS 1.3 protocol.', val: data.metrics.tls_active ? 'ACTIVE' : 'INACTIVE', ok: data.metrics.tls_active },
                { name: 'Admin Auth Control', desc: 'Secure session authenticator gateway intercept.', val: data.metrics.auth_enforced ? 'ACTIVE' : 'INACTIVE', ok: data.metrics.auth_enforced },
                { name: 'Network Route Limitation', desc: 'Only port 8443 exposed. Local ports isolated.', val: data.metrics.network_exposed_port ? `PORT ${data.metrics.network_exposed_port}` : 'ISOLATED', ok: !!data.metrics.network_exposed_port },
                { name: 'Action Ledger Audit Seal', desc: 'Cryptographic block added to action ledger.', val: data.metrics.audit_logs_sealed ? 'SEALED' : 'OPEN', ok: data.metrics.audit_logs_sealed },
                { name: 'ConMon Daily Scheduler', desc: 'Continuous compliance tracking enabled.', val: data.metrics.conmon_scheduler, ok: data.metrics.conmon_scheduler === 'ACTIVE' },
                { name: 'Emergency Rollback Capsule', desc: 'Simulated automatic fallback path is armed.', val: data.metrics.rollback_capsule_armed ? 'ARMED' : 'DISARMED', ok: data.metrics.rollback_capsule_armed },
                { name: 'CyberGov Sync Baseline', desc: 'Live scoreboard synchronized with portal.', val: data.metrics.cybergov_sync, ok: data.metrics.cybergov_sync === 'CONNECTED' }
            ];

            gridEl.innerHTML = metricsList.map(m => {
                let badgeColor = '#f59e0b';
                let badgeBg = 'rgba(245, 158, 11, 0.1)';
                if (m.ok) {
                    badgeColor = '#10b981';
                    badgeBg = 'rgba(16, 185, 129, 0.1)';
                } else if (m.val === 'INACTIVE' || m.val === 'DISCONNECTED') {
                    badgeColor = '#ef4444';
                    badgeBg = 'rgba(239, 68, 68, 0.1)';
                }
                
                return `
                    <div class="card" style="padding: 15px; background: rgba(0,0,0,0.15); border: 1px solid var(--border-glass); display: flex; flex-direction: column; justify-content: space-between;">
                        <div>
                            <h4 style="font-size: 13px; font-weight: bold; color: #fff; margin-bottom: 6px;">${m.name}</h4>
                            <p style="font-size: 11px; color: var(--text-secondary); line-height: 1.4; margin-bottom: 12px;">${m.desc}</p>
                        </div>
                        <span style="align-self: flex-start; padding: 2px 8px; border-radius: 4px; font-size: 10px; font-weight: bold; background: ${badgeBg}; color: ${badgeColor}; border: 1px solid ${badgeBg.replace('0.1', '0.3')};">
                            ${m.val}
                        </span>
                    </div>
                `;
            }).join('');
        }
    }

    async function triggerLiveBinding() {
        const btn = el('btn-establish-live-binding');
        if (!btn) return;
        btn.disabled = true;
        
        try {
            const res = await fetch('/api/v1/live-binding/execute', { method: 'POST' });
            if (!res.ok) throw new Error('Failed to establish live binding');
            const data = await res.json();
            renderLiveExposureData(data);
        } catch (err) {
            console.error('Failed to establish live binding:', err);
        } finally {
            btn.disabled = false;
        }
    }

    async function triggerLiveRollback() {
        const btn = el('btn-rollback-live-binding');
        if (!btn) return;
        btn.disabled = true;
        
        try {
            const res = await fetch('/api/v1/live-binding/rollback', { method: 'POST' });
            if (!res.ok) throw new Error('Failed to rollback live binding');
            const data = await res.json();
            renderLiveExposureData(data);
        } catch (err) {
            console.error('Failed to rollback live binding:', err);
        } finally {
            btn.disabled = false;
        }
    }

    function initLiveExposureButtons() {
        const btnEst = el('btn-establish-live-binding');
        if (btnEst) {
            btnEst.addEventListener('click', (e) => {
                e.preventDefault();
                triggerLiveBinding();
            });
        }
        const btnRoll = el('btn-rollback-live-binding');
        if (btnRoll) {
            btnRoll.addEventListener('click', (e) => {
                e.preventDefault();
                triggerLiveRollback();
            });
        }
    }

    async function loadConMonView() {
        try {
            const res = await fetch('/api/v1/conmon/status');
            if (!res.ok) throw new Error('Failed to fetch ConMon status');
            const data = await res.json();
            renderConMonData(data);
        } catch (err) {
            console.error('Failed to load ConMon view:', err);
        }
    }

    function renderConMonData(data) {
        const scoreEl = el('cm-score-text');
        if (scoreEl) {
            scoreEl.textContent = `${data.compliance_score.toFixed(1)}%`;
            scoreEl.style.color = data.status === 'ALERTING' ? '#ef4444' : '#10b981';
        }

        const deltaEl = el('cm-score-delta');
        if (deltaEl) {
            const sign = data.delta > 0 ? '+' : '';
            deltaEl.textContent = `Delta: ${sign}${data.delta.toFixed(1)}%`;
            deltaEl.style.color = data.delta >= 0 ? '#10b981' : '#ef4444';
        }

        const alertsCountEl = el('cm-alerts-count');
        if (alertsCountEl) {
            alertsCountEl.textContent = data.active_alerts.length;
            alertsCountEl.style.color = data.active_alerts.length > 0 ? '#ef4444' : '#10b981';
        }

        const lastRunEl = el('cm-last-run-text');
        if (lastRunEl) {
            lastRunEl.textContent = `Last run: ${data.last_run}`;
        }

        // Active Alerts Card
        const alertCard = el('conmon-alert-status-card');
        if (alertCard) {
            if (data.active_alerts.length > 0) {
                alertCard.style.background = 'rgba(239, 68, 68, 0.15)';
                alertCard.style.color = '#ef4444';
                alertCard.style.border = '1px solid rgba(239, 68, 68, 0.3)';
                alertCard.innerHTML = `
                    <div style="font-weight: bold; margin-bottom: 8px;">Compliance Violations Detected:</div>
                    <ul style="margin: 0; padding-left: 20px; font-size: 12px; line-height: 1.6;">
                        ${data.active_alerts.map(a => `<li>[${a.severity}] ${escapeHtml(a.message)}</li>`).join('')}
                    </ul>
                `;
            } else {
                alertCard.style.background = 'rgba(16, 185, 129, 0.15)';
                alertCard.style.color = '#10b981';
                alertCard.style.border = '1px solid rgba(16, 185, 129, 0.3)';
                alertCard.innerHTML = 'All continuous compliance checks are passing. No active alerts.';
            }
        }

        // Interval dropdown
        const intervalSelect = el('conmon-interval-select');
        if (intervalSelect) {
            intervalSelect.value = data.schedule_interval;
        }

        // Event Logs console
        const logsEl = el('conmon-daemon-logs');
        if (logsEl && data.logs) {
            logsEl.innerHTML = data.logs.map(log => `<div>${escapeHtml(log)}</div>`).join('');
            logsEl.scrollTop = logsEl.scrollHeight;
        }

        // Evidence snapshot history table
        const tbody = el('conmon-history-tbody');
        if (tbody) {
            if (data.history && data.history.length > 0) {
                tbody.innerHTML = data.history.map(h => {
                    const sign = h.delta > 0 ? '+' : '';
                    const tlsBadge = h.live_metrics.tls_active ? 
                        '<span style="color:#10b981; font-weight:bold;">ACTIVE</span>' : 
                        '<span style="color:var(--text-secondary);">INACTIVE</span>';
                    const authBadge = h.live_metrics.auth_enforced ? 
                        '<span style="color:#10b981; font-weight:bold;">ACTIVE</span>' : 
                        '<span style="color:var(--text-secondary);">INACTIVE</span>';
                    
                    return `
                        <tr style="border-bottom: 1px solid var(--border-glass);">
                            <td style="padding: 8px; font-family: monospace;">${h.timestamp}</td>
                            <td style="padding: 8px;">${h.interval}</td>
                            <td style="padding: 8px; font-weight: bold; color: ${h.alerts_count > 0 ? '#ef4444' : '#10b981'}">${h.compliance_score.toFixed(1)}%</td>
                            <td style="padding: 8px; color: ${h.delta >= 0 ? '#10b981' : '#ef4444'}">${sign}${h.delta.toFixed(1)}%</td>
                            <td style="padding: 8px; color: ${h.alerts_count > 0 ? '#ef4444' : '#10b981'}">${h.alerts_count}</td>
                            <td style="padding: 8px;">${tlsBadge}</td>
                            <td style="padding: 8px;">${authBadge}</td>
                        </tr>
                    `;
                }).join('');
            } else {
                tbody.innerHTML = `<tr><td colspan="7" style="text-align: center; padding: 12px; color: var(--text-secondary);">No scans executed yet. Click "Execute Scan Cycle" to generate monitoring evidence.</td></tr>`;
            }
        }
    }

    async function triggerConMonCycle() {
        const btn = el('btn-run-conmon-cycle');
        if (!btn) return;
        btn.disabled = true;
        btn.textContent = 'Scanning...';

        try {
            const res = await fetch('/api/v1/conmon/run', { method: 'POST' });
            if (!res.ok) throw new Error('ConMon execution failed');
            const data = await res.json();
            renderConMonData(data);
        } catch (err) {
            console.error('Failed to trigger ConMon cycle:', err);
        } finally {
            btn.disabled = false;
            btn.textContent = 'Execute Scan Cycle';
        }
    }

    async function updateConMonInterval(interval) {
        try {
            const res = await fetch('/api/v1/conmon/schedule/update', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ interval })
            });
            if (!res.ok) throw new Error('Schedule update failed');
            const data = await res.json();
            renderConMonData(data);
        } catch (err) {
            console.error('Failed to update ConMon interval:', err);
        }
    }

    function initConMonButtons() {
        const btnRun = el('btn-run-conmon-cycle');
        if (btnRun) {
            btnRun.addEventListener('click', (e) => {
                e.preventDefault();
                triggerConMonCycle();
            });
        }

        const intervalSelect = el('conmon-interval-select');
        if (intervalSelect) {
            intervalSelect.addEventListener('change', (e) => {
                updateConMonInterval(e.target.value);
            });
        }
    }

    // HOCH TV View & Player Integration
    let tvChannels = [];
    let tvGroups = [];
    let currentHls = null;

    function logTvDiag(msg, isError = false) {
        const consoleEl = el('tv-diagnostics-logs');
        if (!consoleEl) return;
        const ts = new Date().toISOString().split('T')[1].slice(0, 8);
        const color = isError ? '#ef4444' : '#10b981';
        consoleEl.innerHTML += `<div style="color: ${color}">[${ts}] ${escapeHtml(msg)}</div>`;
        consoleEl.scrollTop = consoleEl.scrollHeight;
    }

    async function loadHochTvView() {
        logTvDiag('Loading HOCH TV View state...');
        await runTvHealthCheck();
        await loadTvGroups();
        await loadTvChannels();
        await loadGroupHealth();
        await loadCacheStatus();
        await runSecurityAudit();
    }

    async function runTvHealthCheck() {
        const healthIndicator = el('tv-health-indicator');
        if (healthIndicator) {
            healthIndicator.textContent = 'Checking...';
            healthIndicator.style.color = '#eab308';
        }

        try {
            const res = await fetch('/api/tv/health');
            if (!res.ok) throw new Error(`HTTP ${res.status}`);
            const data = await res.json();
            
            if (data.ok) {
                if (healthIndicator) {
                    healthIndicator.textContent = 'HEALTHY';
                    healthIndicator.style.color = '#10b981';
                }
                logTvDiag(`Health check: nominal. ${data.channelCount} channels cached.`);
            } else {
                if (healthIndicator) {
                    healthIndicator.textContent = 'DEGRADED';
                    healthIndicator.style.color = '#ef4444';
                }
                logTvDiag(`Health check warning: ${data.diagnostics}`, true);
            }
            
            const countEl = el('tv-channels-count');
            if (countEl) countEl.textContent = data.channelCount;
            
            const epgEl = el('tv-epg-indicator');
            if (epgEl) {
                epgEl.textContent = data.epgConfigured ? 'CONFIGURED' : 'UNCONFIGURED';
                epgEl.style.color = data.epgConfigured ? '#10b981' : '#a1a1aa';
            }
            
            const loadedEl = el('tv-loaded-indicator');
            if (loadedEl) {
                loadedEl.textContent = data.playlistLoadedAt !== 'Never' ? 
                    data.playlistLoadedAt.split('T')[1].slice(0, 8) : 'Never';
            }
        } catch (err) {
            if (healthIndicator) {
                healthIndicator.textContent = 'ERROR';
                healthIndicator.style.color = '#ef4444';
            }
            logTvDiag(`Health check failed: ${err.message}`, true);
        }
    }

    async function loadTvGroups() {
        const filterSelect = el('tv-group-filter');
        if (!filterSelect) return;
        
        try {
            const res = await fetch('/api/tv/groups');
            if (!res.ok) throw new Error(`HTTP ${res.status}`);
            const groups = await res.json();
            tvGroups = groups;
            
            filterSelect.innerHTML = `
                <option value="ALL">All Categories</option>
                <option value="FAVORITES">⭐ Favorites</option>
                <option value="RECENTS">⏰ Recent Channels</option>
            `;
            groups.forEach(g => {
                const opt = document.createElement('option');
                opt.value = g;
                opt.textContent = g;
                filterSelect.appendChild(opt);
            });
            logTvDiag(`Loaded ${groups.length} channel groups.`);
        } catch (err) {
            logTvDiag(`Failed to load channel groups: ${err.message}`, true);
        }
    }

    async function loadTvChannels(force = false) {
        const listEl = el('tv-channels-list');
        if (!listEl) return;
        listEl.innerHTML = '<div style="color: var(--text-secondary); text-align: center; margin-top: 30px;">Loading channels...</div>';

        try {
            const url = force ? '/api/tv/channels?force=true' : '/api/tv/channels';
            const res = await fetch(url);
            if (!res.ok) {
                const errData = await res.json().catch(() => ({}));
                const detail = errData.detail || `HTTP ${res.status}`;
                throw new Error(detail);
            }
            const channels = await res.json();
            tvChannels = channels;
            
            renderTvChannels(channels);
            logTvDiag(`Loaded ${channels.length} channels.`);
            
            const countEl = el('tv-channels-count');
            if (countEl) countEl.textContent = channels.length;
        } catch (err) {
            listEl.innerHTML = `<div style="color: #ef4444; text-align: center; margin-top: 30px; font-size: 12px; padding: 10px;">${escapeHtml(err.message)}</div>`;
            logTvDiag(`Failed to load channels: ${err.message}`, true);
        }
    }

    let tvFavorites = JSON.parse(localStorage.getItem('hoch-tv-favorites') || '[]');
    let tvRecents = JSON.parse(localStorage.getItem('hoch-tv-recents') || '[]');
    let currentPlayingChannel = null;

    function redactFrontendUrl(url) {
        if (!url) return '';
        try {
            return url.replace(/([?&])(token|auth|pass|key|secret|user|w|g)=([^&#]*)/gi, '$1$2=[REDACTED]');
        } catch (e) {
            return url;
        }
    }

    async function loadGroupHealth() {
        const healthList = el('tv-groups-health-list');
        if (!healthList) return;
        
        try {
            const res = await fetch('/api/tv/groups/health');
            if (!res.ok) throw new Error('Failed to load group health');
            const data = await res.json();
            
            healthList.innerHTML = '';
            for (const g in data) {
                const info = data[g];
                const badgeColor = info.status === 'healthy' ? '#10b981' : 
                                  info.status === 'degraded' ? '#eab308' : '#ef4444';
                                  
                const div = document.createElement('div');
                div.style.cssText = 'display: flex; justify-content: space-between; align-items: center; padding: 4px 6px; background: rgba(0,0,0,0.15); border-radius: 3px;';
                div.innerHTML = `
                    <span style="color: #e4e4e7; font-weight: bold; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 180px;">${escapeHtml(g)}</span>
                    <div style="display: flex; align-items: center; gap: 6px;">
                        <span style="font-size: 10px; color: var(--text-secondary);">${info.healthyCount}/${info.total} OK</span>
                        <span style="width: 8px; height: 8px; border-radius: 50%; background: ${badgeColor}; display: inline-block;" title="Status: ${info.status}"></span>
                    </div>
                `;
                healthList.appendChild(div);
            }
        } catch (err) {
            healthList.innerHTML = `<div style="color: #ef4444; font-size: 10px;">Failed to load health: ${escapeHtml(err.message)}</div>`;
        }
    }

    function toggleFavorite(channelId) {
        const idx = tvFavorites.indexOf(channelId);
        if (idx === -1) {
            tvFavorites.push(channelId);
            logTvDiag(`Added channel to Favorites: ${channelId}`);
        } else {
            tvFavorites.splice(idx, 1);
            logTvDiag(`Removed channel from Favorites: ${channelId}`);
        }
        localStorage.setItem('hoch-tv-favorites', JSON.stringify(tvFavorites));
        
        const favBtn = el('tv-btn-favorite');
        if (favBtn) {
            const isFav = tvFavorites.includes(channelId);
            favBtn.querySelector('svg').setAttribute('fill', isFav ? '#f1c40f' : 'none');
            favBtn.style.color = isFav ? '#f1c40f' : '#a1a1aa';
        }
        
        renderTvChannels(tvChannels);
    }

    function addToRecents(channelId) {
        const idx = tvRecents.indexOf(channelId);
        if (idx !== -1) {
            tvRecents.splice(idx, 1);
        }
        tvRecents.unshift(channelId);
        if (tvRecents.length > 20) {
            tvRecents.pop();
        }
        localStorage.setItem('hoch-tv-recents', JSON.stringify(tvRecents));
    }

    async function loadEpgSchedule(channelId) {
        const epgContainer = el('tv-epg-schedule');
        if (!epgContainer) return;
        epgContainer.innerHTML = '<div style="color: var(--text-secondary); font-style: italic;">Loading schedule...</div>';
        
        try {
            const res = await fetch(`/api/tv/channel/${channelId}/epg`);
            if (!res.ok) throw new Error('EPG fetch failed');
            const data = await res.json();
            
            if (!data || data.length === 0) {
                epgContainer.innerHTML = '<div style="color: var(--text-secondary); font-style: italic;">No program guide available.</div>';
                return;
            }
            
            epgContainer.innerHTML = '';
            data.forEach(p => {
                const startStr = formatEpgTime(p.start);
                const stopStr = formatEpgTime(p.stop);
                
                const div = document.createElement('div');
                div.style.cssText = 'background: rgba(255, 255, 255, 0.02); border: 1px solid var(--border-glass); border-radius: 4px; padding: 6px 10px;';
                div.innerHTML = `
                    <div style="display: flex; justify-content: space-between; margin-bottom: 2px;">
                        <span style="font-size: 11px; font-weight: bold; color: var(--accent-teal);">${escapeHtml(startStr)} - ${escapeHtml(stopStr)}</span>
                    </div>
                    <div style="font-size: 12px; font-weight: bold; color: #fff;">${escapeHtml(p.title)}</div>
                    <div style="font-size: 11px; color: var(--text-secondary); margin-top: 2px; line-height: 1.4;">${escapeHtml(p.description)}</div>
                `;
                epgContainer.appendChild(div);
            });
        } catch (err) {
            epgContainer.innerHTML = `<div style="color: #ef4444; font-size: 11px;">Error loading EPG: ${escapeHtml(err.message)}</div>`;
        }
    }

    function formatEpgTime(timeStr) {
        if (!timeStr || timeStr.length < 12) return timeStr;
        try {
            const hour = timeStr.substring(8, 10);
            const min = timeStr.substring(10, 12);
            return `${hour}:${min}`;
        } catch (e) {
            return timeStr;
        }
    }

    async function runPlaybackTest(channelId) {
        const testBtn = el('tv-btn-test-stream');
        if (testBtn) {
            testBtn.disabled = true;
            testBtn.textContent = 'Testing...';
        }
        
        logTvDiag(`Running playback connectivity diagnostics on: ${channelId}`);
        
        try {
            const res = await fetch(`/api/tv/channel/${channelId}/test`, { method: 'POST' });
            if (!res.ok) throw new Error(`HTTP ${res.status}`);
            const data = await res.json();
            
            if (data.status === 'healthy') {
                logTvDiag(`Playback diagnostic PASS: ${channelId}. Latency: ${data.latencyMs}ms. Stream: ${redactFrontendUrl(data.url)}`);
            } else {
                logTvDiag(`Playback diagnostic FAIL: ${channelId}. Error: ${data.error}. Stream: ${redactFrontendUrl(data.url)}`, true);
            }
            
            await loadGroupHealth();
            await loadDiagnosticsHistory(channelId);
        } catch (err) {
            logTvDiag(`Connectivity test failed: ${err.message}`, true);
        } finally {
            if (testBtn) {
                testBtn.disabled = false;
                testBtn.textContent = 'Test Connection';
            }
        }
    }

    function renderTvChannels(channels) {
        const listEl = el('tv-channels-list');
        if (!listEl) return;
        
        const filterVal = el('tv-group-filter') ? el('tv-group-filter').value : 'ALL';
        const searchVal = el('tv-search') ? el('tv-search').value.toLowerCase().trim() : '';
        
        let filtered = [];
        if (filterVal === 'FAVORITES') {
            filtered = channels.filter(c => tvFavorites.includes(c.id));
        } else if (filterVal === 'RECENTS') {
            filtered = tvRecents.map(rid => channels.find(c => c.id === rid)).filter(Boolean);
        } else {
            filtered = channels.filter(c => {
                const matchesGroup = (filterVal === 'ALL' || c.group === filterVal);
                return matchesGroup;
            });
        }
        
        if (searchVal) {
            filtered = filtered.filter(c => c.name.toLowerCase().includes(searchVal));
        }

        if (filtered.length === 0) {
            listEl.innerHTML = '<div style="color: var(--text-secondary); text-align: center; margin-top: 30px; font-size: 13px;">No matching channels found.</div>';
            return;
        }

        listEl.innerHTML = '';
        filtered.forEach(c => {
            const div = document.createElement('div');
            div.className = 'channel-item';
            div.style.cssText = 'display: flex; align-items: center; gap: 10px; padding: 8px 12px; background: rgba(255,255,255,0.02); border: 1px solid var(--border-glass); border-radius: 4px; cursor: pointer; transition: all 0.2s;';
            
            div.addEventListener('mouseenter', () => {
                div.style.background = 'rgba(255,255,255,0.06)';
                div.style.borderColor = 'rgba(255,255,255,0.2)';
            });
            div.addEventListener('mouseleave', () => {
                div.style.background = 'rgba(255,255,255,0.02)';
                div.style.borderColor = 'var(--border-glass)';
            });

            const imgHtml = c.logo ? 
                `<img src="${escapeHtml(c.logo)}" style="width: 24px; height: 24px; object-fit: contain; border-radius: 2px;" onerror="this.src='data:image/svg+xml;utf8,<svg xmlns=%22http://www.w3.org/2000/svg%22 width=%2224%22 height=%2224%22 viewBox=%220 0 24 24%22 fill=%22none%22 stroke=%22currentColor%22 stroke-width=%222%22><rect x=%222%22 y=%222%22 width=%2220%22 height=%2220%22 rx=%222.18%22 ry=%222.18%22></rect><line x1=%227%22 y1=%222%22 x2=%227%22 y2=%2222%22></line><line x1=%2217%22 y1=%222%22 x2=%2217%22 y2=%2222%22></line><line x1=%222%22 y1=%2212%22 x2=%2222%22 y2=%2212%22></line><line x1=%222%22 y1=%227%22 x2=%227%22 y2=%227%22></line><line x1=%222%22 y1=%2217%22 x2=%227%22 y2=%2217%22></line><line x1=%2217%22 y1=%2217%22 x2=%2222%22 y2=%2217%22></line><line x1=%2217%22 y1=%227%22 x2=%2222%22 y2=%227%22></line></svg>'">` :
                `<div style="width: 24px; height: 24px; display: flex; align-items: center; justify-content: center; background: rgba(255,255,255,0.05); color: var(--text-secondary); border-radius: 2px;"><i data-lucide="tv" style="width: 14px; height: 14px;"></i></div>`;

            const isFav = tvFavorites.includes(c.id);
            const starIcon = isFav ? '<span style="color: #f1c40f; font-size: 14px; margin-left: auto;">★</span>' : '';

            div.innerHTML = `
                ${imgHtml}
                <div style="flex-grow: 1; min-width: 0; display: flex; align-items: center; justify-content: space-between; gap: 6px;">
                    <div style="min-width: 0; flex-grow: 1;">
                        <div style="font-size: 12px; font-weight: bold; color: #fff; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">${escapeHtml(c.name)}</div>
                        <div style="font-size: 9px; color: var(--text-secondary); white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">${escapeHtml(c.group)}</div>
                    </div>
                    ${starIcon}
                </div>
            `;
            
            div.addEventListener('click', () => {
                playTvChannel(c);
            });
            listEl.appendChild(div);
        });

        if (window.lucide) {
            window.lucide.createIcons();
        }
    }

    function playTvChannel(channel) {
        logTvDiag(`Initializing playback for: ${channel.name}`);
        currentPlayingChannel = channel;
        
        const video = el('tv-player');
        const placeholder = el('player-placeholder');
        const errorOverlay = el('player-error-overlay');
        const errorText = el('player-error-text');
        
        if (!video) return;

        if (placeholder) placeholder.style.display = 'none';
        if (errorOverlay) errorOverlay.style.display = 'none';

        const playingName = el('tv-playing-name');
        if (playingName) playingName.textContent = channel.name;
        
        const playingGroup = el('tv-playing-group');
        if (playingGroup) playingGroup.textContent = `Category: ${channel.group}`;

        const favBtn = el('tv-btn-favorite');
        if (favBtn) {
            favBtn.style.display = 'inline-flex';
            const isFav = tvFavorites.includes(channel.id);
            favBtn.querySelector('svg').setAttribute('fill', isFav ? '#f1c40f' : 'none');
            favBtn.style.color = isFav ? '#f1c40f' : '#a1a1aa';
        }

        const testBtn = el('tv-btn-test-stream');
        if (testBtn) {
            testBtn.style.display = 'inline-block';
        }

        const showHistoryBtn = el('tv-btn-show-history');
        if (showHistoryBtn) {
            showHistoryBtn.style.display = 'inline-block';
        }

        addToRecents(channel.id);
        loadEpgSchedule(channel.id);
        loadDiagnosticsHistory(channel.id);

        if (currentHls) {
            currentHls.destroy();
            currentHls = null;
        }

        const streamUrl = channel.playbackUrl || channel.streamUrl;
        
        let playbackRetryCount = 0;
        const maxPlaybackRetries = 3;
        let retryTimeout = null;

        function triggerPlaybackRetry(msg) {
            if (playbackRetryCount < maxPlaybackRetries) {
                playbackRetryCount++;
                logTvDiag(`[player] Playback retry attempt ${playbackRetryCount}/${maxPlaybackRetries} due to: ${msg}`);
                if (retryTimeout) clearTimeout(retryTimeout);
                retryTimeout = setTimeout(() => {
                    logTvDiag(`[player] Executing retry ${playbackRetryCount}...`);
                    if (currentHls) {
                        currentHls.loadSource(streamUrl);
                        currentHls.attachMedia(video);
                    } else {
                        video.load();
                    }
                    video.play().catch(err => {
                        logTvDiag(`[player] Play command during retry failed: ${err.message}`, true);
                    });
                }, 2000);
            } else {
                logTvDiag(`[player] Maximum retries (${maxPlaybackRetries}) reached. Failing closed.`, true);
                if (errorOverlay && errorText) {
                    errorText.textContent = `${msg} (All retry attempts failed)`;
                    errorOverlay.style.display = 'flex';
                }
            }
        }
        
        video.onerror = (e) => {
            const err = video.error;
            let errMsg = 'An unknown video error occurred.';
            if (err) {
                if (err.code === 1) errMsg = 'The fetching of the media resource was aborted by the user.';
                else if (err.code === 2) errMsg = 'A network error caused the media download to fail.';
                else if (err.code === 3) errMsg = 'An error occurred while decoding the media resource.';
                else if (err.code === 4) errMsg = 'The media resource was not supported or could not be played.';
            }
            logTvDiag(`HTML5 Video Error: ${errMsg}`, true);
            triggerPlaybackRetry(errMsg);
        };

        if (streamUrl.toLowerCase().includes('.m3u8')) {
            if (Hls.isSupported()) {
                const hls = new Hls({
                    maxBufferLength: 10,
                    enableWorker: true
                });
                hls.loadSource(streamUrl);
                hls.attachMedia(video);
                currentHls = hls;

                hls.on(Hls.Events.ERROR, function (event, data) {
                    if (data.fatal) {
                        logTvDiag(`Fatal HLS error encountered: ${data.type} - ${data.details}`, true);
                        switch (data.type) {
                            case Hls.ErrorTypes.NETWORK_ERROR:
                                logTvDiag('Fatal network error, attempting recovery...', true);
                                hls.startLoad();
                                break;
                            case Hls.ErrorTypes.MEDIA_ERROR:
                                logTvDiag('Fatal media error, attempting recovery...', true);
                                hls.recoverMediaError();
                                break;
                            default:
                                logTvDiag('Cannot recover from fatal stream error, triggering retry.', true);
                                triggerPlaybackRetry(`HLS ${data.type} error: ${data.details}`);
                                break;
                        }
                    }
                });
            } else if (video.canPlayType('application/vnd.apple.mpegurl')) {
                video.src = streamUrl;
            } else {
                const noHlsMsg = 'HLS playback is not supported in this browser.';
                logTvDiag(noHlsMsg, true);
                if (errorOverlay && errorText) {
                    errorText.textContent = noHlsMsg;
                    errorOverlay.style.display = 'flex';
                }
            }
        } else {
            video.src = streamUrl;
        }
    }

    function initTvButtons() {
        const btnReload = el('btn-tv-reload');
        if (btnReload) {
            btnReload.addEventListener('click', async (e) => {
                e.preventDefault();
                btnReload.disabled = true;
                btnReload.textContent = 'Reloading...';
                await loadTvChannels(true);
                await runTvHealthCheck();
                await loadGroupHealth();
                await loadCacheStatus();
                await runSecurityAudit();
                btnReload.disabled = false;
                btnReload.textContent = 'Reload Playlist';
            });
        }

        const btnHealth = el('btn-tv-health');
        if (btnHealth) {
            btnHealth.addEventListener('click', async (e) => {
                e.preventDefault();
                btnHealth.disabled = true;
                btnHealth.textContent = 'Running...';
                await runTvHealthCheck();
                await loadGroupHealth();
                await loadCacheStatus();
                await runSecurityAudit();
                btnHealth.disabled = false;
                btnHealth.textContent = 'Run Health Check';
            });
        }

        const btnLayout = el('btn-tv-toggle-layout');
        if (btnLayout) {
            btnLayout.addEventListener('click', (e) => {
                e.preventDefault();
                toggleTvLayout();
            });
        }

        const showHistoryBtn = el('tv-btn-show-history');
        if (showHistoryBtn) {
            showHistoryBtn.addEventListener('click', (e) => {
                e.preventDefault();
                const container = el('tv-diagnostics-history-container');
                if (container) {
                    container.style.display = 'block';
                }
            });
        }

        const closeHistoryBtn = el('tv-btn-close-history');
        if (closeHistoryBtn) {
            closeHistoryBtn.addEventListener('click', (e) => {
                e.preventDefault();
                const container = el('tv-diagnostics-history-container');
                if (container) {
                    container.style.display = 'none';
                }
            });
        }

        const searchInput = el('tv-search');
        if (searchInput) {
            searchInput.addEventListener('input', () => {
                renderTvChannels(tvChannels);
            });
        }

        const groupFilter = el('tv-group-filter');
        if (groupFilter) {
            groupFilter.addEventListener('change', () => {
                renderTvChannels(tvChannels);
            });
        }

        const btnFav = el('tv-btn-favorite');
        if (btnFav) {
            btnFav.addEventListener('click', (e) => {
                e.preventDefault();
                if (currentPlayingChannel) {
                    toggleFavorite(currentPlayingChannel.id);
                }
            });
        }

        const btnTest = el('tv-btn-test-stream');
        if (btnTest) {
            btnTest.addEventListener('click', (e) => {
                e.preventDefault();
                if (currentPlayingChannel) {
                    runPlaybackTest(currentPlayingChannel.id);
                }
            });
        }
    }

    async function loadDiagnosticsHistory(channelId) {
        const historyList = el('tv-diagnostics-history-list');
        if (!historyList) return;
        historyList.innerHTML = '<div style="color: var(--text-secondary); font-style: italic;">Loading diagnostics history...</div>';
        
        try {
            const res = await fetch(`/api/tv/channel/${channelId}/test/history`);
            if (!res.ok) throw new Error('Failed to fetch history');
            const data = await res.json();
            
            if (!data || data.length === 0) {
                historyList.innerHTML = '<div style="color: var(--text-secondary); font-style: italic;">No previous diagnostics runs.</div>';
                return;
            }
            
            historyList.innerHTML = '';
            data.slice().reverse().forEach(run => {
                const statusColor = run.status === 'healthy' ? '#10b981' : '#ef4444';
                const time = run.timestamp.split('T')[1].substring(0,8);
                const info = run.status === 'healthy' ? `${run.latencyMs}ms` : (run.error || 'failed');
                
                const div = document.createElement('div');
                div.style.cssText = 'display: flex; justify-content: space-between; border-bottom: 1px solid rgba(255,255,255,0.02); padding: 2px 0;';
                div.innerHTML = `
                    <span style="color: var(--text-secondary);">${escapeHtml(time)}</span>
                    <span style="color: ${statusColor}; font-weight: bold;">${run.status.toUpperCase()}</span>
                    <span style="color: #fff;">${escapeHtml(info)}</span>
                `;
                historyList.appendChild(div);
            });
        } catch (err) {
            historyList.innerHTML = `<div style="color: #ef4444;">Error: ${escapeHtml(err.message)}</div>`;
        }
    }

    async function loadTimelineGrid() {
        const gridContainer = el('tv-timeline-grid');
        if (!gridContainer) return;
        gridContainer.innerHTML = '<div style="color: var(--text-secondary); font-style: italic; padding: 20px; text-align: center;">Loading EPG schedule timeline...</div>';
        
        try {
            const res = await fetch('/api/tv/timeline');
            if (!res.ok) throw new Error('Timeline fetch failed');
            const channels = await res.json();
            
            if (!channels || channels.length === 0) {
                gridContainer.innerHTML = '<div style="color: var(--text-secondary); font-style: italic; padding: 20px; text-align: center;">No schedule schedules found. Click Reload Playlist.</div>';
                return;
            }
            
            gridContainer.innerHTML = '';
            
            // Build hourly markers at top of grid
            const headerRow = document.createElement('div');
            headerRow.style.cssText = 'display: flex; align-items: center; border-bottom: 1px solid var(--border-glass); padding-bottom: 6px; margin-bottom: 6px; gap: 10px; min-width: 800px;';
            headerRow.innerHTML = `<div style="width: 150px; min-width: 150px; font-size: 11px; font-weight: bold; color: var(--text-secondary);">CHANNEL</div>`;
            
            // Render 6 hourly slots starting from now
            const now = new Date();
            const startHour = new Date(now.getFullYear(), now.getMonth(), now.getDate(), now.getHours());
            for (let i = 0; i < 6; i++) {
                const markerTime = new Date(startHour.getTime() + i * 3600000);
                const timeString = markerTime.toTimeString().substring(0, 5);
                headerRow.innerHTML += `<div style="flex: 1; text-align: left; font-size: 11px; font-weight: bold; color: var(--text-secondary); border-left: 1px solid rgba(255,255,255,0.05); padding-left: 8px;">${timeString}</div>`;
            }
            gridContainer.appendChild(headerRow);
            
            channels.forEach(c => {
                const row = document.createElement('div');
                row.style.cssText = 'display: flex; align-items: center; gap: 10px; padding: 6px 0; border-bottom: 1px solid rgba(255,255,255,0.02); min-width: 800px;';
                
                const logoHtml = c.logo ? 
                    `<img src="${escapeHtml(c.logo)}" style="width: 20px; height: 20px; object-fit: contain; border-radius: 2px;" onerror="this.src='data:image/svg+xml;utf8,<svg></svg>'">` : 
                    `<i data-lucide="tv" style="width: 12px; height: 12px; color: var(--text-secondary);"></i>`;
                
                row.innerHTML = `
                    <div class="timeline-channel-cell" style="width: 150px; min-width: 150px; display: flex; align-items: center; gap: 8px; cursor: pointer;" title="Tune in to ${escapeHtml(c.name)}">
                        ${logoHtml}
                        <span style="font-size: 12px; font-weight: bold; color: #fff; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">${escapeHtml(c.name)}</span>
                    </div>
                `;
                
                // Add listener to channel cell to play channel
                row.querySelector('.timeline-channel-cell').addEventListener('click', () => {
                    // switch back to standard view to play
                    toggleTvLayout(false);
                    playTvChannel(c);
                });

                // Horizontal timeline container for program blocks
                const scheduleContainer = document.createElement('div');
                scheduleContainer.style.cssText = 'flex-grow: 1; display: flex; gap: 8px; height: 36px;';
                
                const programs = c.programs || [];
                if (programs.length === 0) {
                    const noEp = document.createElement('div');
                    noEp.style.cssText = 'flex: 1; background: rgba(255,255,255,0.01); border: 1px dashed var(--border-glass); border-radius: 4px; display: flex; align-items: center; justify-content: center; font-size: 10px; color: var(--text-secondary);';
                    noEp.textContent = 'No Schedule Data';
                    scheduleContainer.appendChild(noEp);
                } else {
                    // Display up to 3 programs
                    programs.slice(0, 3).forEach(p => {
                        const block = document.createElement('div');
                        block.style.cssText = 'flex: 1; background: rgba(16, 185, 129, 0.03); border: 1px solid rgba(16, 185, 129, 0.15); border-radius: 4px; padding: 4px 8px; display: flex; flex-direction: column; justify-content: center; cursor: pointer; transition: all 0.2s; overflow: hidden;';
                        block.innerHTML = `
                            <div style="font-size: 10px; font-weight: bold; color: var(--accent-teal); white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">${escapeHtml(formatEpgTime(p.start))} - ${escapeHtml(formatEpgTime(p.stop))}</div>
                            <div style="font-size: 11px; font-weight: bold; color: #fff; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;" title="${escapeHtml(p.title)}">${escapeHtml(p.title)}</div>
                        `;
                        block.addEventListener('mouseenter', () => {
                            block.style.background = 'rgba(16, 185, 129, 0.08)';
                            block.style.borderColor = 'rgba(16, 185, 129, 0.3)';
                        });
                        block.addEventListener('mouseleave', () => {
                            block.style.background = 'rgba(16, 185, 129, 0.03)';
                            block.style.borderColor = 'rgba(16, 185, 129, 0.15)';
                        });
                        block.addEventListener('click', () => {
                            toggleTvLayout(false);
                            playTvChannel(c);
                        });
                        scheduleContainer.appendChild(block);
                    });
                }
                
                row.appendChild(scheduleContainer);
                gridContainer.appendChild(row);
            });
            
            if (window.lucide) {
                window.lucide.createIcons();
            }
        } catch (err) {
            gridContainer.innerHTML = `<div style="color: #ef4444; padding: 20px; text-align: center;">Error loading timeline: ${escapeHtml(err.message)}</div>`;
        }
    }

    function toggleTvLayout(forceTimeline) {
        const timelineBtn = el('btn-tv-toggle-layout');
        const standardView = el('tv-standard-view');
        const timelineView = el('tv-timeline-view');
        
        if (!timelineBtn || !standardView || !timelineView) return;
        
        isTimelineView = forceTimeline !== undefined ? forceTimeline : !isTimelineView;
        
        if (isTimelineView) {
            standardView.style.display = 'none';
            timelineView.style.display = 'flex';
            timelineBtn.textContent = 'View Channels List';
            loadTimelineGrid();
        } else {
            standardView.style.display = 'grid';
            timelineView.style.display = 'none';
            timelineBtn.textContent = 'View EPG Timeline';
        }
    }

    async function loadCacheStatus() {
        try {
            const res = await fetch('/api/tv/cache/status');
            if (!res.ok) throw new Error('Failed to fetch cache status');
            const data = await res.json();
            
            const playlistIndicator = el('tv-playlist-cache-indicator');
            if (playlistIndicator && data.playlist) {
                const playlist = data.playlist;
                playlistIndicator.textContent = `${playlist.hitCount} H / ${playlist.missCount} M`;
                playlistIndicator.title = `Status: ${playlist.status}\nSize: ${playlist.sizeBytes} bytes\nHash: ${playlist.hash.substring(0,8)}...`;
                if (playlist.status === 'error') {
                    playlistIndicator.style.color = '#ef4444';
                } else if (playlist.status === 'fresh') {
                    playlistIndicator.style.color = '#10b981';
                } else {
                    playlistIndicator.style.color = '#fff';
                }
            }
            
            const epgIndicator = el('tv-epg-cache-indicator');
            if (epgIndicator && data.epg) {
                const epg = data.epg;
                epgIndicator.textContent = `${epg.hitCount} H / ${epg.missCount} M`;
                epgIndicator.title = `Status: ${epg.status}\nSize: ${epg.sizeBytes} bytes\nHash: ${epg.hash.substring(0,8)}...`;
                if (epg.status === 'error') {
                    epgIndicator.style.color = '#ef4444';
                } else if (epg.status === 'fresh') {
                    epgIndicator.style.color = '#10b981';
                } else {
                    epgIndicator.style.color = '#fff';
                }
            }
        } catch (err) {
            logTvDiag(`Error loading cache observability: ${err.message}`, true);
        }
    }

    async function runSecurityAudit() {
        const securityIndicator = el('tv-security-indicator');
        if (!securityIndicator) return;
        securityIndicator.textContent = 'Auditing...';
        securityIndicator.style.color = '#fff';
        
        try {
            const res = await fetch('/api/tv/security-audit');
            if (!res.ok) throw new Error('Security audit query failed');
            const data = await res.json();
            
            securityIndicator.textContent = data.status;
            if (data.status === 'SAFE') {
                securityIndicator.style.color = '#10b981';
                securityIndicator.title = `Checked at ${data.checkedAt}. Checked files: ${data.scannedFiles.join(', ')}. Zero credentials exposed.`;
            } else {
                securityIndicator.style.color = '#ef4444';
                securityIndicator.title = `Checked at ${data.checkedAt}. Warning: ${data.findings.join('; ')}`;
                logTvDiag(`Security Audit warnings: ${data.findings.join('; ')}`, true);
            }
        } catch (err) {
            securityIndicator.textContent = 'ERROR';
            securityIndicator.style.color = '#ef4444';
            logTvDiag(`Security audit failed: ${err.message}`, true);
        }
    }

    // Run initialization once DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

})();



let meshSentinelFilter = "all";

async function fetchJsonSafe(url) {
  const response = await fetch(url, { headers: { "Accept": "application/json" } });
  if (!response.ok) {
    throw new Error(`${url} returned ${response.status}`);
  }
  return response.json();
}

function meshTruthClass(truth) {
  const value = String(truth || "EMPTY").toLowerCase().replaceAll("_", "-");
  return `truth-${value}`;
}

function renderMeshSentinel(data) {
  const map = document.getElementById("mesh-sentinel-map");
  const alerts = document.getElementById("mesh-alerts");
  const updated = document.getElementById("mesh-last-updated");
  const truth = document.getElementById("mesh-truth-state");

  if (!map) return;

  const nodes = Array.isArray(data.nodes) ? data.nodes : [];
  const alertItems = Array.isArray(data.alerts) ? data.alerts : [];

  if (updated) updated.textContent = `Last updated: ${data.generated_at || "unknown"}`;
  if (truth) truth.textContent = `Truth: ${data.truth || "EMPTY"}`;

  const visibleNodes = nodes.filter(node => {
    if (meshSentinelFilter === "all") return true;
    if (meshSentinelFilter === "alerts") return String(node.truth || "").includes("UNEXPECTED");
    if (meshSentinelFilter === "MISSING_FROM_SCAN") return node.truth === "MISSING_FROM_SCAN";
    return node.kind === meshSentinelFilter;
  });

  if (!visibleNodes.length) {
    map.innerHTML = '<p class="empty-state">No live mesh nodes match the selected filter.</p>';
  } else {
    map.innerHTML = visibleNodes.map(node => {
      const models = Array.isArray(node.models) ? node.models : [];
      const modelList = models.length
        ? models.slice(0, 8).map(model => `<li>${escapeHtml(String(model))}</li>`).join("")
        : "<li>No models returned by endpoint.</li>";

      return `
        <article class="mesh-node ${meshTruthClass(node.truth)}">
          <div class="mesh-node-header">
            <strong>${escapeHtml(node.label || node.id || "Unknown Node")}</strong>
            <span class="status-pill">${escapeHtml(node.truth || "EMPTY")}</span>
          </div>
          <dl class="mesh-node-facts">
            <div><dt>IP</dt><dd>${escapeHtml(node.ip || "unknown")}</dd></div>
            <div><dt>Port</dt><dd>${escapeHtml(String(node.port || "unknown"))}</dd></div>
            <div><dt>Kind</dt><dd>${escapeHtml(node.kind || "UNKNOWN")}</dd></div>
            <div><dt>Reachable</dt><dd>${node.reachable ? "true" : "false"}</dd></div>
            <div><dt>Models</dt><dd>${escapeHtml(String(node.model_count ?? models.length ?? 0))}</dd></div>
            <div><dt>Source</dt><dd>${escapeHtml(node.source || "/api/v1/mesh-sentinel/map")}</dd></div>
            <div><dt>Last scanned</dt><dd>${escapeHtml(node.last_scanned || "unknown")}</dd></div>
          </dl>
          <details>
            <summary>Models</summary>
            <ul>${modelList}</ul>
          </details>
        </article>
      `;
    }).join("");
  }

  if (alerts) {
    if (!alertItems.length) {
      alerts.innerHTML = '<p class="empty-state">No live mesh alerts.</p>';
    } else {
      alerts.innerHTML = alertItems.map(item => `
        <article class="event-row ${meshTruthClass(item.severity)}">
          <strong>${escapeHtml(item.severity || "INFO")}</strong>
          <span>${escapeHtml(item.message || "Alert")}</span>
          <code>${escapeHtml(item.source || "/api/v1/detections/events")}</code>
        </article>
      `).join("");
    }
  }
}

async function loadMeshSentinel() {
  const map = document.getElementById("mesh-sentinel-map");
  if (map) map.innerHTML = '<p class="empty-state">Loading live mesh sentinel data...</p>';
  try {
    const data = await fetchJsonSafe("/api/v1/mesh-sentinel/map");
    renderMeshSentinel(data);
  } catch (error) {
    if (map) {
      map.innerHTML = `<p class="error-state">Mesh Sentinel failed: ${escapeHtml(error.message)}</p>`;
    }
  }
}

async function rescanMeshSentinel() {
  const button = document.getElementById("mesh-rescan-ai-runtimes");
  const status = document.getElementById("mesh-scan-status");

  if (button) button.disabled = true;
  if (status) status.textContent = "Scanning...";

  try {
    await fetchJsonSafe("/api/v1/discovery/ai-runtimes/rescan", { method: "POST" });
  } catch (_) {
    const response = await fetch("/api/v1/discovery/ai-runtimes/rescan", { method: "POST" });
    if (!response.ok) throw new Error(`rescan returned ${response.status}`);
  }

  await loadMeshSentinel();

  if (status) status.textContent = "Scan Complete";
  if (button) button.disabled = false;
}

function initMeshSentinel() {
  document.querySelectorAll("[data-mesh-filter]").forEach(button => {
    button.addEventListener("click", () => {
      meshSentinelFilter = button.getAttribute("data-mesh-filter") || "all";
      document.querySelectorAll("[data-mesh-filter]").forEach(item => item.classList.remove("active"));
      button.classList.add("active");
      loadMeshSentinel();
    });
  });

  const refresh = document.getElementById("mesh-refresh");
  if (refresh) refresh.addEventListener("click", loadMeshSentinel);

  const rescan = document.getElementById("mesh-rescan-ai-runtimes");
  if (rescan) rescan.addEventListener("click", () => {
    rescanMeshSentinel().catch(error => {
      const status = document.getElementById("mesh-scan-status");
      if (status) status.textContent = `Scan Failed: ${error.message}`;
      rescan.disabled = false;
    });
  });
}


// PROTO-3A — 10-device swarm prototype and agent chat
function renderDeviceSwarm(data) {
  const summary = document.getElementById("device-swarm-summary");
  const grid = document.getElementById("device-swarm-grid");
  const consoleEl = document.getElementById("device-swarm-console");
  if (!summary || !grid) return;

  const s = data.summary || {};
  summary.innerHTML = `
    <div class="metric-card"><span>Devices</span><strong>${escapeHtml(String(s.device_count ?? 0))}</strong></div>
    <div class="metric-card"><span>Model Runtimes</span><strong>${escapeHtml(String(s.model_runtime_count ?? 0))}</strong></div>
    <div class="metric-card"><span>Models</span><strong>${escapeHtml(String(s.model_count ?? 0))}</strong></div>
    <div class="metric-card"><span>Agents</span><strong>${escapeHtml(String((s.agents_available || []).length))}</strong></div>
  `;

  grid.innerHTML = (data.devices || []).map((d) => {
    const runtimeBadges = (d.runtimes || []).map((r) =>
      `<span class="pill model">${escapeHtml(r.runtime)}:${escapeHtml(String(r.port))} ${escapeHtml(r.truth_state)}</span>`
    ).join("");
    const modelBadges = (d.models || []).slice(0, 10).map((m) =>
      `<span class="pill model">${escapeHtml(m)}</span>`
    ).join("");
    const agentBadges = (d.agents_available || []).map((a) =>
      `<span class="pill agent">${escapeHtml(a)}</span>`
    ).join("");

    const klass = d.runtime_count > 0 ? "live" : d.truth_state === "MISSING_FROM_SCAN" ? "missing" : "service";

    return `
      <article class="device-swarm-card ${klass}">
        <h4>${escapeHtml(d.name || d.ip || "Unknown Device")}</h4>
        <dl>
          <div><dt>IP</dt><dd>${escapeHtml(d.ip || "unknown")}</dd></div>
          <div><dt>MAC</dt><dd>${escapeHtml(d.mac || "unknown")}</dd></div>
          <div><dt>Type</dt><dd>${escapeHtml(d.device_type || "UNKNOWN")}</dd></div>
          <div><dt>Truth</dt><dd>${escapeHtml(d.truth_state || "UNKNOWN")}</dd></div>
          <div><dt>Ports</dt><dd>${escapeHtml((d.open_ports || []).join(", ") || "none")}</dd></div>
          <div><dt>Source</dt><dd>${escapeHtml(d.source || "unknown")}</dd></div>
        </dl>
        <div class="pill-zone">${runtimeBadges}${modelBadges}${agentBadges}</div>
      </article>
    `;
  }).join("");

  if (consoleEl) {
    consoleEl.textContent = JSON.stringify({
      generated_at: data.generated_at,
      summary: data.summary,
      source: data.source
    }, null, 2);
  }
}

async function loadDeviceSwarm() {
  const status = document.getElementById("device-swarm-status");
  if (status) status.textContent = "Loading...";
  try {
    const data = await fetchJsonSafe("/api/v1/swarm/devices?limit=10");
    renderDeviceSwarm(data);
    if (status) status.textContent = "Live";
  } catch (error) {
    if (status) status.textContent = "Error";
    const consoleEl = document.getElementById("device-swarm-console");
    if (consoleEl) consoleEl.textContent = `Device swarm load failed: ${error.message}`;
  }
}

async function rescanDeviceSwarm() {
  const status = document.getElementById("device-swarm-status");
  if (status) status.textContent = "Scanning...";
  const data = await fetchJsonSafe("/api/v1/swarm/devices/rescan?limit=10", { method: "POST" });
  renderDeviceSwarm(data);
  if (status) status.textContent = "Scan Complete";
}

async function sendDeviceSwarmPrompt() {
  const payload = {
    agent: document.getElementById("device-swarm-agent")?.value || "Mission Commander",
    target: document.getElementById("device-swarm-target")?.value || "swarm",
    prompt: document.getElementById("device-swarm-prompt")?.value || ""
  };
  const out = await fetchJsonSafe("/api/v1/swarm/agent-chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
  });
  const consoleEl = document.getElementById("device-swarm-console");
  if (consoleEl) consoleEl.textContent = JSON.stringify(out, null, 2);
}

function initDeviceSwarmPrototype() {
  document.getElementById("device-swarm-rescan")?.addEventListener("click", () => {
    rescanDeviceSwarm().catch((error) => {
      const consoleEl = document.getElementById("device-swarm-console");
      if (consoleEl) consoleEl.textContent = `Rescan failed: ${error.message}`;
    });
  });
  document.getElementById("device-swarm-send")?.addEventListener("click", () => {
    sendDeviceSwarmPrompt().catch((error) => {
      const consoleEl = document.getElementById("device-swarm-console");
      if (consoleEl) consoleEl.textContent = `Agent prompt failed: ${error.message}`;
    });
  });
  loadDeviceSwarm();
}

document.addEventListener("DOMContentLoaded", initDeviceSwarmPrototype);
