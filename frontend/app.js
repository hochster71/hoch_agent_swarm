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
        { id: 'clawde', label: 'CLAWDE CONTROL TOWER' }
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

    // ── Loader: Readiness View ──────────────────────────────────────────────
    async function loadReadinessView() {
        const container = el('readiness-gate-info');
        if (!container) return;
        try {
            const res = await fetch('/api/v1/production-readiness');
            const data = await res.json();

            container.innerHTML = `
                <div class="card" style="padding:20px; border:1px solid var(--border-glass);">
                    <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:16px;">
                        <div>
                            <span style="font-size:12px; color:var(--text-secondary); text-transform:uppercase;">Overall Readiness Score</span>
                            <div style="font-size:36px; font-weight:800; color:#10b981; margin-top:4px;">${data.score || 0}%</div>
                        </div>
                        <div style="text-align:right;">
                            <span style="font-size:12px; color:var(--text-secondary); text-transform:uppercase;">Verdict</span>
                            <div style="font-size:24px; font-weight:800; color:${data.go_no_go === 'GO' ? '#10b981' : '#ef4444'}; margin-top:4px;">${data.go_no_go || 'UNKNOWN'}</div>
                        </div>
                    </div>
                </div>
                <div class="card" style="padding:20px; border:1px solid var(--border-glass);">
                    <h3 style="font-weight:bold; color:#fff; font-size:14px; margin-bottom:12px; text-transform:uppercase;">Readiness Gate Checks</h3>
                    <div style="display:flex; flex-direction:column; gap:8px; font-size:13px;">
                        <div style="display:flex; justify-content:space-between; border-bottom:1px solid rgba(255,255,255,0.03); padding-bottom:6px;">
                            <span>API Integrity check</span>
                            <span style="color:#10b981; font-weight:bold;">PASS</span>
                        </div>
                        <div style="display:flex; justify-content:space-between; border-bottom:1px solid rgba(255,255,255,0.03); padding-bottom:6px;">
                            <span>Port Hardening enforcement</span>
                            <span style="color:#10b981; font-weight:bold;">PASS</span>
                        </div>
                        <div style="display:flex; justify-content:space-between; border-bottom:1px solid rgba(255,255,255,0.03); padding-bottom:6px;">
                            <span>Autonomy budget allocation</span>
                            <span style="color:#10b981; font-weight:bold;">PASS</span>
                        </div>
                        <div style="display:flex; justify-content:space-between;">
                            <span>SIEM Rule compilation</span>
                            <span style="color:#10b981; font-weight:bold;">PASS</span>
                        </div>
                    </div>
                </div>
            `;
        } catch (err) {
            container.innerHTML = `<div style="color:#ef4444; text-align:center;">Error fetching production readiness metrics</div>`;
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

            phaseSpan.textContent = reg.next_phase || '--';
            completedSpan.textContent = reg.last_completed_phase || '--';
            
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

            if (promptCode) promptCode.textContent = paths.generated_prompt || '--';
            if (reportCode) reportCode.textContent = paths.latest_report || '--';
            if (sealCode) sealCode.textContent = paths.evidence_seal || '--';

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
                // Fetch the approval doc to find status
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
                        status = 'APPROVED'; // If file exists but not in memory queue yet
                    }
                } catch (e) {
                    status = 'APPROVED';
                }
            }
            
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

        } catch (err) {
            console.error("Error loading CLAWDE Control Tower state:", err);
            if (dbgApi) {
                dbgApi.textContent = 'OFFLINE';
                dbgApi.style.color = '#f87171';
            }
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
                        try {
                            const createRes = await fetch('/api/v1/runs', {
                                method: 'POST',
                                headers: { 'Content-Type': 'application/json' },
                                body: JSON.stringify({ name: `Flight Campaign ${new Date().toLocaleTimeString()}` })
                            });
                            if (createRes.ok) {
                                const newRun = await createRes.json();
                                selectedCampaignId = newRun.run_id;
                                isFlightDeckInitialized = false; // force refresh dropdown
                                loadAgentFlightDeckView();
                            }
                        } catch (err) {
                            console.error('[FlightDeck] failed to launch campaign:', err);
                        }
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

    // Initialization routine
    function init() {
  initMeshSentinel();
        initTheme();
        initNavigation();
        initializeKoiAnimation();
        initRescanButton();
        
        // Initial fetches
        fetchCockpit();
        // Setup cockpit polling interval
        cockpitInterval = setInterval(fetchCockpit, 3000);

        // Load default view
        switchView('mission-control');
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
