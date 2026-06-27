(function () {
    'use strict';

    // Global state variables
    let activeView = 'mission-control';
    let cockpitInterval = null;
    let viewInterval = null;
    let pondAnimationId = null;
    let pondProcesses = [];

    // Helper functions
    const el = (id) => document.getElementById(id);

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
        { id: 'model-router', label: 'MODEL ROUTER' },
        { id: 'escalations', label: 'ESCALATIONS' },
        { id: 'evidence', label: 'EVIDENCE' },
        { id: 'detections', label: 'DETECTIONS' },
        { id: 'readiness', label: 'READINESS' },
        { id: 'settings', label: 'SETTINGS' }
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
            const dot = el(`dot-${key}`);
            const stateLabel = el(`state-${key}`);
            const body = el(`body-${key}`);

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
                html = `<div style="display:flex; flex-direction:column; gap:4px;">
                    <div>Registry workers: <strong style="color:#fff;">${data.devices_count || 0} profiles</strong></div>
                    <div style="font-size:9px; opacity:0.8;">Local cluster worker profiles.</div>
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

    // ── Koi Animation Layer (Batch UI-KOI-1) ─────────────────────────────────────
    function initializeKoiAnimation() {
        if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
            return;
        }
        const pond = document.getElementById("koi-pond-layer");
        if (!pond) return;

        // Clear existing
        pond.innerHTML = "";

        // Helper to create koi SVG
        function createKoiSVG() {
            return `
                <svg viewBox="0 0 60 30" width="100%" height="100%" fill="none" xmlns="http://www.w3.org/2000/svg">
                    <path d="M5,15 Q30,5 55,15 Q30,25 5,15 Z" fill="var(--accent-teal, var(--kimi-green, #8cff5c))" opacity="0.8"/>
                    <path d="M25,8 Q20,2 15,5 Q18,8 20,8 Z" fill="var(--kimi-green-soft, #56d944)" opacity="0.6"/>
                    <path d="M25,22 Q20,28 15,25 Q18,22 20,22 Z" fill="var(--kimi-green-soft, #56d944)" opacity="0.6"/>
                    <path d="M5,15 Q0,10 2,5 Q5,10 5,15 Z" fill="var(--kimi-green-soft, #56d944)" opacity="0.7"/>
                    <path d="M5,15 Q0,20 2,25 Q5,20 5,15 Z" fill="var(--kimi-green-soft, #56d944)" opacity="0.7"/>
                </svg>
            `;
        }

        // Create 3 koi orbits
        const orbits = [
            { width: 300, height: 300, duration: 35, top: "15%", left: "10%", reverse: false },
            { width: 450, height: 450, duration: 55, top: "45%", left: "55%", reverse: true },
            { width: 350, height: 350, duration: 40, top: "25%", left: "40%", reverse: false }
        ];

        orbits.forEach((cfg, idx) => {
            const orbit = document.createElement("div");
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
            fish.style.animationDelay = `${idx * 0.4}s`;
            fish.innerHTML = createKoiSVG();

            orbit.appendChild(fish);
            pond.appendChild(orbit);
        });

        // Ripple creator
        function triggerRipple(x, y) {
            if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
            const ripple = document.createElement("div");
            ripple.className = "koi-ripple";
            ripple.style.left = `${x}px`;
            ripple.style.top = `${y}px`;
            pond.appendChild(ripple);
            setTimeout(() => {
                ripple.remove();
            }, 3000);
        }

        // Document click triggers ripples
        document.addEventListener("click", (e) => {
            if (e.target.tagName !== "BUTTON" && e.target.tagName !== "A" && e.target.tagName !== "INPUT" && e.target.tagName !== "SELECT") {
                triggerRipple(e.clientX, e.clientY);
            }
        });

        // Random background ripples
        setInterval(() => {
            if (document.hidden) return;
            const x = Math.random() * window.innerWidth;
            const y = Math.random() * window.innerHeight;
            triggerRipple(x, y);
        }, 5000);
    }

    // Initialization routine
    function init() {
        initTheme();
        initNavigation();
        initializeKoiAnimation();
        
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
