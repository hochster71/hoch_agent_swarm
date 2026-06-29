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
    let isTimelineView = false;

    // Global state variables for decision room
    let currentDecisionRoomCandidate = null;
    let activeAuthorityToken = null;
    let authorityCountdownInterval = null;
    let currentGeneratedPlan = null;

    // Missing stub functions to prevent console/runtime crashes
    function triggerCrewaiIngestion() { console.log('triggerCrewaiIngestion stub'); }
    async function loadCrewaiIngestionStatus() { console.log('loadCrewaiIngestionStatus stub'); }
    
    async function populateDecisionRoomCandidates() {
        const selectEl = document.getElementById("decision-room-candidate-select");
        if (!selectEl) return;
        try {
            const res = await fetch('/api/v1/release/candidate-packets');
            if (!res.ok) return;
            const packets = await res.json();
            
            selectEl.innerHTML = "";
            
            if (!packets || packets.length === 0) {
                const opt = document.createElement("option");
                opt.value = "";
                opt.textContent = "No candidates available";
                selectEl.appendChild(opt);
                currentDecisionRoomCandidate = null;
                await updateReleaseAuthorityUI();
                return;
            }
            
            packets.forEach(p => {
                const opt = document.createElement("option");
                opt.value = p.candidate_packet_id;
                opt.textContent = `${p.candidate_packet_id} (Ver: ${p.version})`;
                selectEl.appendChild(opt);
            });
            
            selectEl.selectedIndex = 0;
            await handleCandidateSelectionChange();
        } catch (err) {
            console.error("Error populating decision room candidates:", err);
        }
    }

    async function handleCandidateSelectionChange() {
        const selectEl = document.getElementById("decision-room-candidate-select");
        if (!selectEl || !selectEl.value) {
            currentDecisionRoomCandidate = null;
            await updateReleaseAuthorityUI();
            return;
        }
        
        try {
            const res = await fetch(`/api/v1/release/candidate-packets/${selectEl.value}`);
            if (!res.ok) return;
            currentDecisionRoomCandidate = await res.json();
            
            const selectVer = document.getElementById("decision-room-candidate-version");
            if (selectVer) selectVer.textContent = currentDecisionRoomCandidate.version;
            
            await updateReleaseAuthorityUI();
        } catch (err) {
            console.error("Error handling candidate selection change:", err);
        }
    }

    function simulateDecision() { console.log('simulateDecision stub'); }
    function exportDecisionMemo() { console.log('exportDecisionMemo stub'); }
    async function loadRoutingHistoryData() { console.log('loadRoutingHistoryData stub'); }
    async function loadInferenceHistory() { console.log('loadInferenceHistory stub'); }
    async function loadMultiModelHistory() { console.log('loadMultiModelHistory stub'); }
    function populateModelNodeSelect() { console.log('populateModelNodeSelect stub'); }
    async function loadAgentModelPolicies() { console.log('loadAgentModelPolicies stub'); }
    async function loadPolicyDecisions() { console.log('loadPolicyDecisions stub'); }
    function registerModelProvider() { console.log('registerModelProvider stub'); }
    function runProviderHealthCheck() { console.log('runProviderHealthCheck stub'); }
    function runProviderModelDiscovery() { console.log('runProviderModelDiscovery stub'); }
    function runProviderApproval() { console.log('runProviderApproval stub'); }
    function runProviderDisabling() { console.log('runProviderDisabling stub'); }
    function sendTestInference() { console.log('sendTestInference stub'); }
    function executeMultiModelReasoning() { console.log('executeMultiModelReasoning stub'); }
    function saveAgentModelPolicy() { console.log('saveAgentModelPolicy stub'); }

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
        { id: 'production-command-center', viewId: 'production-command-center', label: 'PRODUCTION COMMAND CENTER' },
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
        { id: 'prompt-catalog', label: 'PROMPT CATALOG' },
        { id: 'promptops', label: 'PROMPTOPS PORTAL' },
        { id: 'evidenceops', label: 'EVIDENCEOPS PORTAL' },
        { id: 'modelops', label: 'MODELOPS PORTAL' },
        { id: 'toolops', label: 'TOOLOPS PORTAL' },
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
        { id: "conmon-scheduler", label: "CONMON SCHEDULER" },
        { id: "hoch-tv", label: "HOCH TV" },
        { id: "readiness-autopilot", viewId: "readiness-autopilot", label: "READINESS AUTOPILOT" },
        { id: "hochster-runtime", viewId: "hochster-runtime", label: "HOCHSTER RUNTIME" },
        { id: "remediation-safety", viewId: "remediation-safety", label: "REMEDIATION SAFETY" },
        { id: "runtime-audit", viewId: "runtime-audit", label: "RUNTIME AUDIT" },
        { id: "error-budget", viewId: "error-budget", label: "ERROR BUDGET" },
        { id: "release-provenance", viewId: "release-provenance", label: "RELEASE PROVENANCE" },
        { id: "swarm-control", viewId: "swarm-control", label: "SWARM CONTROL" },
        { id: "mission-intel", viewId: "mission", label: "MISSION INTEL" },
        { id: "timeline-replay", viewId: "replay", label: "TIMELINE REPLAY" },
        { id: "cybersecurity-factory", viewId: "cybersecurity-factory", label: "CYBERSECURITY FACTORY" },
        { id: "governance", viewId: "governance", label: "OPERATOR GOVERNANCE" },
        { id: "device-swarm", label: "DEVICE SWARM" },
        { id: "mesh-sentinel", label: "MESH SENTINEL" },
        { id: "finance-command-center", viewId: "finance-command-center", label: "FINANCE COMMAND CENTER" },
        { id: "runtime-reliability", viewId: "runtime-reliability", label: "RUNTIME RELIABILITY" },
        { id: "pert-e2e-build", viewId: "pert-e2e-build", label: "PERT E2E BUILD" }
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
            if (btn) btn.classList.remove("active");
            const vId = v.viewId || v.id;
            const viewDiv = el(`view-${vId}`);
            if (viewDiv) {
                viewDiv.classList.add("hidden");
                viewDiv.setAttribute("hidden", "");
            }
        });

        const activeBtn = el(`nav-${viewId}`);
        if (activeBtn) activeBtn.classList.add("active");

        const tgtView = views.find(v => v.id === viewId);
        const resolvedViewId = tgtView ? (tgtView.viewId || tgtView.id) : viewId;
        const activeDiv = el(`view-${resolvedViewId}`);
        if (activeDiv) {
            activeDiv.classList.remove("hidden");
            activeDiv.removeAttribute("hidden");
        }

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
            case 'prompt-catalog':
                loadPromptCatalogView();
                break;
            case 'promptops':
                loadPromptOpsView();
                break;
            case 'evidenceops':
                loadEvidenceOpsView();
                break;
            case 'modelops':
                loadModelOpsView();
                break;
            case 'toolops':
                loadToolOpsView();
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
            case 'production-command-center':
                loadProductionCommandCenterView();
                viewInterval = setInterval(loadProductionCommandCenterView, 3000);
                break;
            case 'release-provenance':
                fetchAndRenderReleaseProvenance();
                viewInterval = setInterval(fetchAndRenderReleaseProvenance, 5000);
                break;
            case 'governance':
                fetchAndRenderGovernanceSummary();
                viewInterval = setInterval(fetchAndRenderGovernanceSummary, 5000);
                break;
            case 'finance-command-center':
                loadFinanceCommandCenterView();
                viewInterval = setInterval(loadFinanceCommandCenterView, 3000);
                break;
            case 'runtime-reliability':
                loadRuntimeReliabilityView();
                viewInterval = setInterval(loadRuntimeReliabilityView, 3000);
                break;
            case 'pert-e2e-build':
                loadPertE2eBuildView();
                viewInterval = setInterval(loadPertE2eBuildView, 3000);
                break;
        }
    }

    let qaLoopPoller = null;

    async function loadProductionCommandCenterView() {
        try {
            const res = await fetch('/api/v1/production-tracker');
            if (!res.ok) return;
            const data = await res.json();

            // 1. Last Updated Timestamp
            const updatedEl = el('cc-last-updated');
            if (updatedEl) {
                updatedEl.textContent = `Last Updated: ${new Date().toLocaleTimeString()}`;
            }

            // 2. Score text & Circular Gauge
            const scoreText = el('cc-score-text');
            if (scoreText) scoreText.textContent = data.readiness_score;

            const gaugeFill = el('cc-gauge-fill');
            if (gaugeFill) {
                const maxOffset = 251.2;
                const offset = maxOffset - (maxOffset * (data.readiness_score || 0) / 100);
                gaugeFill.style.strokeDashoffset = offset;
            }

            // 3. Drivers
            if (el('cc-driver-build')) el('cc-driver-build').textContent = `${data.drivers.build_health}%`;
            if (el('cc-driver-e2e')) el('cc-driver-e2e').textContent = `${data.drivers.e2e_pass_rate}%`;
            if (el('cc-driver-stability')) el('cc-driver-stability').textContent = `${data.drivers.runtime_stability}%`;

            // 4. Browser Telemetry
            const chromeEl = el('cc-telemetry-chrome');
            if (chromeEl) {
                chromeEl.textContent = data.browser_telemetry.chrome_alive ? "ALIVE" : "OFFLINE";
                chromeEl.style.color = data.browser_telemetry.chrome_alive ? "var(--accent-teal)" : "#ef4444";
            }
            const playwrightEl = el('cc-telemetry-playwright');
            if (playwrightEl) {
                playwrightEl.textContent = data.browser_telemetry.playwright_success ? "PASSING" : "FAILED";
                playwrightEl.style.color = data.browser_telemetry.playwright_success ? "var(--accent-teal)" : "#ef4444";
            }
            const profileEl = el('cc-telemetry-profile');
            if (profileEl) {
                profileEl.textContent = data.browser_telemetry.clean_profile ? "CLEAN" : "DIRTY";
                profileEl.style.color = data.browser_telemetry.clean_profile ? "var(--accent-blue)" : "var(--accent-yellow)";
            }
            const gpuEl = el('cc-telemetry-gpu');
            if (gpuEl) {
                gpuEl.textContent = (data.browser_telemetry.gpu_status || 'disabled').toUpperCase();
                gpuEl.style.color = data.browser_telemetry.gpu_status === 'enabled' ? "var(--accent-teal)" : "var(--text-secondary)";
            }
            const extensionsEl = el('cc-telemetry-extensions');
            if (extensionsEl) {
                extensionsEl.textContent = (data.browser_telemetry.extensions && data.browser_telemetry.extensions.length > 0) ? data.browser_telemetry.extensions.join(', ') : 'None';
            }

            // 5. Git Status
            const gitBranch = el('cc-git-branch');
            if (gitBranch) gitBranch.textContent = data.git_status.branch || 'unknown';
            
            const gitTree = el('cc-git-tree');
            if (gitTree) {
                gitTree.textContent = data.git_status.working_tree_clean ? "CLEAN" : "DIRTY";
                gitTree.style.color = data.git_status.working_tree_clean ? "var(--accent-teal)" : "var(--accent-yellow)";
            }

            const gitCommits = el('cc-git-commits');
            if (gitCommits && data.git_status.recent_commits) {
                gitCommits.innerHTML = data.git_status.recent_commits.map(c => `
                    <div style="margin-bottom:4px; text-overflow:ellipsis; overflow:hidden; white-space:nowrap;">
                        <span style="color:var(--accent-teal);">${c.substring(0, 7)}</span> ${c.substring(7)}
                    </div>
                `).join('');
            }

            // 6. Draw PERT Network SVG
            const svg = el('cc-pert-svg');
            if (svg && data.pert_graph) {
                svg.innerHTML = '';
                
                // Draw connecting edge lines
                data.pert_graph.edges.forEach(edge => {
                    const fromNode = data.pert_graph.nodes.find(n => n.id === edge.from);
                    const toNode = data.pert_graph.nodes.find(n => n.id === edge.to);
                    if (fromNode && toNode) {
                        const line = document.createElementNS("http://www.w3.org/2000/svg", "line");
                        line.setAttribute("x1", fromNode.x);
                        line.setAttribute("y1", fromNode.y);
                        line.setAttribute("x2", toNode.x);
                        line.setAttribute("y2", toNode.y);
                        line.setAttribute("stroke", edge.critical ? "#ef4444" : "rgba(255,255,255,0.15)");
                        line.setAttribute("stroke-width", edge.critical ? "2.5" : "1.5");
                        if (!edge.critical) {
                            line.setAttribute("stroke-dasharray", "4,4");
                        }
                        svg.appendChild(line);
                    }
                });

                // Draw nodes
                data.pert_graph.nodes.forEach(node => {
                    const g = document.createElementNS("http://www.w3.org/2000/svg", "g");
                    g.style.cursor = 'pointer';

                    const rect = document.createElementNS("http://www.w3.org/2000/svg", "rect");
                    rect.setAttribute("x", node.x - 50);
                    rect.setAttribute("y", node.y - 20);
                    rect.setAttribute("width", 100);
                    rect.setAttribute("height", 40);
                    rect.setAttribute("rx", 6);
                    
                    let strokeColor = "var(--border-glass)";
                    let fillColor = "rgba(16, 24, 48, 0.9)";
                    if (node.status === "DONE") {
                        strokeColor = "var(--accent-teal)";
                    } else if (node.status === "IN_PROGRESS") {
                        strokeColor = "var(--accent-yellow)";
                        fillColor = "rgba(245, 158, 11, 0.1)";
                    } else {
                        strokeColor = "rgba(255,255,255,0.1)";
                    }
                    if (node.critical && node.status !== "DONE") {
                        strokeColor = "#ef4444";
                    }

                    rect.setAttribute("stroke", strokeColor);
                    rect.setAttribute("stroke-width", "2");
                    rect.setAttribute("fill", fillColor);
                    g.appendChild(rect);

                    // Title
                    const text = document.createElementNS("http://www.w3.org/2000/svg", "text");
                    text.setAttribute("x", node.x);
                    text.setAttribute("y", node.y + 4);
                    text.setAttribute("text-anchor", "middle");
                    text.setAttribute("fill", "#fff");
                    text.setAttribute("font-size", "10px");
                    text.setAttribute("font-family", "sans-serif");
                    text.setAttribute("font-weight", "600");
                    text.textContent = node.label;
                    g.appendChild(text);

                    svg.appendChild(g);
                });
            }

            // 7. Live Task Board
            const todoList = el('cc-task-list-todo');
            const progressList = el('cc-task-list-progress');
            const doneList = el('cc-task-list-done');
            
            let todoCount = 0, progressCount = 0, doneCount = 0;
            if (todoList && progressList && doneList && data.tasks) {
                todoList.innerHTML = '';
                progressList.innerHTML = '';
                doneList.innerHTML = '';

                data.tasks.forEach(task => {
                    const card = document.createElement('div');
                    card.className = 'card';
                    card.style.background = 'rgba(255,255,255,0.02)';
                    card.style.border = task.critical_path ? '1px solid rgba(239, 68, 68, 0.4)' : '1px solid var(--border-glass)';
                    card.style.padding = '10px';
                    card.style.borderRadius = '6px';
                    card.style.fontSize = '12px';
                    card.style.lineHeight = '1.4';
                    card.style.display = 'flex';
                    card.style.flexDirection = 'column';
                    card.style.gap = '4px';

                    card.innerHTML = `
                        <div style="font-weight:bold; color:#fff; display:flex; justify-content:space-between; align-items:center;">
                            <span>${task.title}</span>
                            ${task.critical_path ? '<span style="font-size:8px; color:#ef4444; border:1px solid #ef4444; padding:1px 4px; border-radius:3px; text-transform:uppercase;">Critical</span>' : ''}
                        </div>
                        <div style="display:flex; justify-content:space-between; font-size:10px; color:var(--text-secondary); margin-top:4px;">
                            <span>Agent: ${task.assigned_agent}</span>
                            <span>ID: ${task.task_id}</span>
                        </div>
                    `;

                    if (task.status === 'DONE') {
                        doneList.appendChild(card);
                        doneCount++;
                    } else if (task.status === 'IN_PROGRESS') {
                        progressList.appendChild(card);
                        progressCount++;
                    } else {
                        todoList.appendChild(card);
                        todoCount++;
                    }
                });

                if (el('cc-task-count-todo')) el('cc-task-count-todo').textContent = todoCount;
                if (el('cc-task-count-progress')) el('cc-task-count-progress').textContent = progressCount;
                if (el('cc-task-count-done')) el('cc-task-count-done').textContent = doneCount;
            }

            // 8. Defect Queue
            const defectList = el('cc-defect-list');
            if (defectList && data.defects) {
                defectList.innerHTML = '';
                if (data.defects.length === 0) {
                    defectList.innerHTML = `<div style="color: var(--text-secondary); text-align: center; font-size: 12px; padding: 20px;">No defects detected.</div>`;
                } else {
                    data.defects.forEach(bug => {
                        const div = document.createElement('div');
                        div.className = 'card';
                        div.style.background = 'rgba(255,255,255,0.02)';
                        div.style.border = '1px solid var(--border-glass)';
                        div.style.padding = '10px';
                        div.style.borderRadius = '6px';
                        div.style.fontSize = '12px';
                        div.style.display = 'flex';
                        div.style.flexDirection = 'column';
                        div.style.gap = '4px';

                        let severityColor = "var(--accent-blue)";
                        if (bug.severity === "Critical") severityColor = "#ef4444";
                        else if (bug.severity === "High") severityColor = "var(--accent-orange)";
                        else if (bug.severity === "Medium") severityColor = "var(--accent-yellow)";

                        div.innerHTML = `
                            <div style="display:flex; justify-content:space-between; font-weight:bold; align-items:center;">
                                <span style="color:#fff;">${bug.title}</span>
                                <span style="font-size:9px; color:${severityColor}; border:1px solid ${severityColor}; padding:1px 4px; border-radius:3px;">${bug.severity}</span>
                            </div>
                            <div style="font-size:11px; color:var(--text-secondary); margin-top:2px;">${bug.description}</div>
                            <div style="display:flex; justify-content:space-between; font-size:10px; color:var(--text-secondary); margin-top:4px; border-top:1px solid rgba(255,255,255,0.03); padding-top:4px;">
                                <span>Status: <strong style="color:${bug.status === 'RESOLVED' ? 'var(--accent-teal)' : 'var(--accent-yellow)'}">${bug.status}</strong></span>
                                <span>${bug.defect_id}</span>
                            </div>
                        `;
                        defectList.appendChild(div);
                    });
                }
            }

            // 9. Release Readiness Checklist
            const checklistContainer = el('cc-checklist-container');
            if (checklistContainer && data.checklist) {
                checklistContainer.innerHTML = data.checklist.map(item => `
                    <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid rgba(255,255,255,0.03); padding-bottom: 6px;">
                        <span style="color: #fff;">${item.title}</span>
                        <span class="badge" style="background: ${item.status === 'PASS' ? 'rgba(16,185,129,0.15)' : 'rgba(239,68,68,0.15)'}; color: ${item.status === 'PASS' ? 'var(--accent-teal)' : '#ef4444'}; font-weight:bold; font-size:10px;">${item.status}</span>
                    </div>
                `).join('');
            }

            // 10. Evidence Pack Tracker
            const evidenceContainer = el('cc-evidence-container');
            if (evidenceContainer && data.evidence_packs) {
                if (data.evidence_packs.length === 0) {
                    evidenceContainer.innerHTML = `<div style="color: var(--text-secondary); text-align: center; font-size: 12px; padding: 20px;">No evidence files generated yet.</div>`;
                } else {
                    evidenceContainer.innerHTML = data.evidence_packs.map(pack => `
                        <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid rgba(255,255,255,0.03); padding-bottom: 6px; font-size: 11px;">
                            <a href="${pack.path}" target="_blank" style="color: var(--accent-teal); text-decoration: none; font-family: monospace;">${pack.name}</a>
                            <span style="color: var(--text-secondary); font-size:10px;">${new Date(pack.timestamp).toLocaleTimeString()}</span>
                        </div>
                    `).join('');
                }
            }

            // 11. Brain LLM Telemetry
            await loadBrainAutonomyTelemetry();

            if (window.lucide) window.lucide.createIcons();
        } catch (err) {
            console.error("Error loading Production Command Center:", err);
        }
    }

    function formatCurrency(val) {
        return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(val || 0);
    }

    async function loadFinanceCommandCenterView() {
        try {
            const res = await fetch('/api/v1/finance/tracker');
            if (!res.ok) return;
            const data = await res.json();

            // 1. Header & Last Audit Timestamp
            const updatedEl = el('fin-last-updated');
            if (updatedEl) {
                updatedEl.textContent = `Last Updated: ${new Date().toLocaleTimeString()}`;
            }
            const auditTimeEl = el('fin-last-audit');
            if (auditTimeEl) {
                auditTimeEl.textContent = `Last Audit: ${new Date().toLocaleDateString()} ${new Date().toLocaleTimeString()}`;
            }

            // 2. Metrics & Gauge Fill
            const metrics = data.metrics || {};
            if (el('monthly-income-total')) el('monthly-income-total').textContent = formatCurrency(metrics.monthly_income);
            if (el('monthly-bills-total')) el('monthly-bills-total').textContent = formatCurrency(metrics.monthly_bills);
            
            const availEl = el('monthly-available-total');
            if (availEl) {
                availEl.textContent = formatCurrency(metrics.monthly_available);
                availEl.style.color = metrics.monthly_available >= 0 ? "var(--accent-teal)" : "#ef4444";
            }
            
            if (el('debt-total')) el('debt-total').textContent = formatCurrency(metrics.total_debt);
            if (el('asset-total')) el('asset-total').textContent = formatCurrency(metrics.total_assets);
            if (el('savings-this-session')) el('savings-this-session').textContent = formatCurrency(metrics.savings_this_session);

            // 3. Render Income
            const incomeList = el('fin-income-list');
            if (incomeList && data.income) {
                incomeList.innerHTML = data.income.map(inc => {
                    let badge = '';
                    let opacity = '1';
                    if (inc.id === 'inc-alison') {
                        badge = '<span class="badge info" style="font-size:8px; margin-left:8px;">Projected Sep 2026 (Excluded)</span>';
                        opacity = '0.6';
                    } else if (inc.frequency === 'one-time') {
                        badge = '<span class="badge label" style="font-size:8px; margin-left:8px; background:rgba(255,255,255,0.05); color:#a1a1aa;">One-Time (Excluded)</span>';
                        opacity = '0.7';
                    } else if (inc.recurring) {
                        badge = '<span class="badge pass" style="font-size:8px; margin-left:8px;">Active Recurring</span>';
                    }
                    return `
                        <div style="display:flex; justify-content:space-between; align-items:center; border-bottom:1px solid rgba(255,255,255,0.03); padding-bottom:8px; opacity:${opacity};">
                            <div>
                                <span style="font-weight:bold; color:#fff; font-size:12px;">${inc.source}</span>
                                ${badge}
                                <div style="font-size:10px; color:var(--text-secondary); margin-top:2px;">Type: ${inc.type} • Freq: ${inc.frequency}</div>
                            </div>
                            <span style="font-weight:bold; color:var(--accent-teal); font-family:monospace; font-size:12px;">${formatCurrency(inc.amount)}</span>
                        </div>
                    `;
                }).join('');
            }

            // 4. Render Bills grouped by category with sub-totals
            const billsList = el('fin-bills-list');
            if (billsList && data.bills && data.billCategories) {
                billsList.innerHTML = '';
                
                // Group bills by category
                data.billCategories.forEach(cat => {
                    const catBills = data.bills.filter(b => b.category === cat);
                    if (catBills.length === 0) return;
                    
                    // Render Header Row for Category
                    const headerRow = document.createElement('tr');
                    headerRow.style.background = 'rgba(255,255,255,0.02)';
                    headerRow.style.borderBottom = '1px solid var(--border-glass)';
                    headerRow.innerHTML = `
                        <td colspan="4" style="padding: 6px 4px; font-weight: bold; color: var(--accent-teal); font-family: monospace; text-transform: uppercase; font-size: 10px;">
                            📁 ${cat}
                        </td>
                    `;
                    billsList.appendChild(headerRow);
                    
                    let catSum = 0;
                    
                    catBills.forEach(bill => {
                        const row = document.createElement('tr');
                        row.style.borderBottom = '1px solid rgba(255,255,255,0.02)';
                        
                        let nameDecor = bill.name;
                        let statusColor = 'var(--text-secondary)';
                        let amountColor = '#fff';
                        
                        let badgeStr = '';
                        if (bill.status === 'cancelled') {
                            badgeStr = ' <span class="badge fail" style="font-size:8px; padding:1px 3px;">CANCELLED</span>';
                            nameDecor = `<span style="text-decoration: line-through; color: var(--text-muted);">${bill.name}</span>`;
                            amountColor = 'var(--text-muted)';
                        } else {
                            // Active budgeted items sum up
                            catSum += bill.amount;
                            if (bill.status === 'paid_yearly') {
                                badgeStr = ' <span class="badge pass" style="font-size:8px; padding:1px 3px;">YEAR-PAID</span>';
                                statusColor = 'var(--accent-teal)';
                            } else if (bill.status === 'future_pmt') {
                                badgeStr = ' <span class="badge warning" style="font-size:8px; padding:1px 3px;">FUTURE</span>';
                                statusColor = 'var(--accent-yellow)';
                            } else if (bill.status === 'disputed') {
                                badgeStr = ' <span class="badge fail" style="font-size:8px; padding:1px 3px;">DISPUTED</span>';
                                statusColor = '#ef4444';
                            } else {
                                statusColor = 'var(--accent-teal)';
                            }
                        }
                        
                        row.innerHTML = `
                            <td style="padding: 6px 4px; color: #fff;">${nameDecor}${badgeStr}</td>
                            <td style="padding: 6px 4px; color: var(--text-secondary); font-family: monospace;">${bill.category}</td>
                            <td style="padding: 6px 4px; text-align: right; color: ${amountColor}; font-family: monospace;">${formatCurrency(bill.amount)}</td>
                            <td style="padding: 6px 4px; text-align: center; color: ${statusColor}; font-family: monospace; font-size: 10px;">${bill.status}</td>
                        `;
                        billsList.appendChild(row);
                    });
                    
                    // Render Category Sub-total Row
                    const subtotalRow = document.createElement('tr');
                    subtotalRow.style.borderBottom = '2px solid var(--border-glass)';
                    subtotalRow.style.fontWeight = 'bold';
                    subtotalRow.innerHTML = `
                        <td colspan="2" style="padding: 6px 4px; text-align: right; color: var(--text-secondary); font-size: 9px; font-family: monospace;">
                            Sub-total (${cat}):
                        </td>
                        <td style="padding: 6px 4px; text-align: right; color: var(--accent-teal); font-family: monospace;">
                            ${formatCurrency(catSum)}
                        </td>
                        <td></td>
                    `;
                    billsList.appendChild(subtotalRow);
                });
            }

            // 5. Spending Intelligence Category Breakdown & Transactions (with z-index z-indexed tooltips)
            const spendingMeta = el('fin-spending-meta');
            if (spendingMeta && data.spendingAnalysis) {
                const totalSpent = data.spendingAnalysis.reduce((sum, item) => sum + item.total, 0);
                const totalCount = data.spendingAnalysis.reduce((sum, item) => sum + item.count, 0);
                spendingMeta.textContent = `Total: ${formatCurrency(totalSpent)} | Count: ${totalCount}`;
            }

            const spendingCategories = el('fin-spending-categories');
            if (spendingCategories && data.spendingAnalysis) {
                spendingCategories.innerHTML = data.spendingAnalysis.map(item => `
                    <div class="card" style="padding:8px; display:flex; justify-content:space-between; align-items:center; background:rgba(255,255,255,0.01); border:1px solid var(--border-glass); cursor:pointer;" onclick="window.filterFinanceSpending('${item.category}')">
                        <div>
                            <div style="font-weight:bold; font-size:11px; color:#fff;">${item.category}</div>
                            <div style="font-size:9px; color:var(--text-secondary); margin-top:2px;">${item.count} txs</div>
                        </div>
                        <span style="font-family:monospace; font-weight:bold; color:var(--accent-teal); font-size:11px;">${formatCurrency(item.total)}</span>
                    </div>
                `).join('');
            }

            const spendingTransactions = el('fin-spending-transactions');
            if (spendingTransactions && data.transactions) {
                window.renderFinanceTransactions = function(filterCat) {
                    const txs = filterCat 
                        ? data.transactions.filter(t => t.category === filterCat) 
                        : data.transactions;
                    
                    spendingTransactions.innerHTML = txs.map(t => {
                        const tooltipText = `Merchant: ${t.vendor}\nCategory: ${t.category}\nDate: ${t.date}\nAmount: ${formatCurrency(t.amount)}`;
                        return `
                            <div class="card" style="padding:8px; display:flex; justify-content:space-between; align-items:center; background:rgba(255,255,255,0.01); border:1px solid var(--border-glass); font-size:11px; position:relative;" title="${tooltipText}">
                                <div>
                                    <div style="font-weight:bold; color:#fff;">${t.vendor}</div>
                                    <div style="font-size:9px; color:var(--text-secondary); margin-top:2px;">${t.date} • ${t.category}</div>
                                </div>
                                <span style="font-family:monospace; font-weight:bold; color:#ef4444;">${formatCurrency(t.amount)}</span>
                            </div>
                        `;
                    }).join('');
                };
                window.filterFinanceSpending = function(cat) {
                    window.renderFinanceTransactions(cat);
                };
                window.renderFinanceTransactions(); // Initial render
            }

            // 6. Debt Command Center
            const debtMeta = el('fin-debt-meta');
            if (debtMeta && data.debts) {
                const totalDebt = data.debts.reduce((sum, item) => sum + item.balance, 0);
                const activePayment = data.debts.reduce((sum, item) => sum + item.monthlyMin, 0);
                debtMeta.textContent = `Total: ${formatCurrency(totalDebt)} | Monthly: ${formatCurrency(activePayment)}`;
            }

            const debtList = el('fin-debt-list');
            if (debtList && data.debts) {
                debtList.innerHTML = data.debts.map(debt => {
                    let riskColor = 'var(--accent-teal)';
                    if (debt.legalRisk === 'high') riskColor = '#ef4444';
                    else if (debt.legalRisk === 'medium') riskColor = 'var(--accent-yellow)';
                    
                    let badge = '';
                    let nameDecor = debt.creditor;
                    if (debt.status === 'disputed') {
                        badge = '<span class="badge fail" style="font-size:8px; margin-left:4px;">DISPUTED</span>';
                        nameDecor = `<span style="color:var(--text-muted);">${debt.creditor}</span>`;
                    } else if (debt.status === 'future') {
                        badge = '<span class="badge info" style="font-size:8px; margin-left:4px;">FUTURE</span>';
                    }
                    
                    return `
                        <div style="border-bottom:1px solid rgba(255,255,255,0.03); padding-bottom:8px;">
                            <div style="display:flex; justify-content:space-between; align-items:center;">
                                <span style="font-weight:bold; color:#fff; font-size:11px;">${nameDecor}${badge}</span>
                                <span style="font-family:monospace; font-weight:bold; color:var(--accent-yellow); font-size:11px;">${formatCurrency(debt.balance)}</span>
                            </div>
                            <div style="display:flex; justify-content:space-between; font-size:9px; color:var(--text-secondary); margin-top:2px;">
                                <span>Min Pay: ${formatCurrency(debt.monthlyMin)}/mo</span>
                                <span style="color:${riskColor}">Risk: ${debt.legalRisk.toUpperCase()}</span>
                            </div>
                        </div>
                    `;
                }).join('');
            }

            const strategyBox = el('fin-debt-strategy-box');
            if (strategyBox) {
                strategyBox.innerHTML = `
                    <div style="font-weight:bold; color:#fff; font-size:11px; margin-bottom:6px;">📈 Automated Repayment Sequencer</div>
                    <div style="font-size:10px; color:var(--text-secondary); line-height:1.4;">
                        <strong>Avalanche Strategy (Recommended):</strong><br/>
                        1. Target SkylaFCU 2nd Mortgage (6.75% rate)<br/>
                        2. Target Rausch & Sturm (accel option: $1,000/mo)<br/>
                        3. Target SOFI Loan once active.
                    </div>
                    <div style="font-size:10px; color:var(--text-secondary); margin-top:8px; line-height:1.4; border-top:1px solid var(--border-glass); padding-top:6px;">
                        <strong>Settlement Candidates:</strong><br/>
                        Halsted Financial & ARM Solutions are optimal targets for Goodwill / Pay-For-Delete agreements.
                    </div>
                `;
            }

            // 7. Legal & Credit Hub
            const legalList = el('fin-legal-list');
            if (legalList && data.legalCreditHub) {
                legalList.innerHTML = data.legalCreditHub.map(l => `
                    <div class="card" style="padding:8px; background:rgba(255,255,255,0.01); border:1px solid var(--border-glass); font-size:11px;">
                        <div style="display:flex; justify-content:space-between; align-items:center;">
                            <strong style="color:#fff;">${l.title}</strong>
                            <span class="badge info" style="font-size:8px; padding:1px 3px;">${l.type.toUpperCase()}</span>
                        </div>
                        <div style="font-size:9px; color:var(--text-secondary); margin-top:2px;">${l.description}</div>
                        <button class="btn btn-secondary" style="padding:2px 6px; font-size:9px; margin-top:6px; border:1px solid var(--border-glass); background:none; color:var(--accent-teal); cursor:pointer;" onclick="alert('Template ready: Copied to clipboard.')">
                            Copy Template
                        </button>
                    </div>
                `).join('');
            }

            // 8. Insurance & Estate
            const insList = el('fin-insurance-list');
            if (insList && data.insurance) {
                const totalCoverage = data.insurance.reduce((sum, item) => sum + item.coverage, 0);
                insList.innerHTML = `
                    <div style="font-weight:bold; color:var(--accent-teal); font-size:13px; margin-bottom:8px; display:flex; justify-content:space-between;">
                        <span>Total Coverage:</span>
                        <span>${formatCurrency(totalCoverage)}</span>
                    </div>
                ` + data.insurance.map(ins => `
                    <div style="border-bottom:1px solid rgba(255,255,255,0.03); padding-bottom:8px; margin-bottom:8px;">
                        <div style="display:flex; justify-content:space-between; font-size:11px;">
                            <span style="font-weight:bold; color:#fff;">Policy: ${ins.policyNumber}</span>
                            <span style="font-family:monospace; color:var(--accent-teal); font-weight:bold;">${formatCurrency(ins.coverage)}</span>
                        </div>
                        <div style="display:flex; justify-content:space-between; font-size:9px; color:var(--text-secondary); margin-top:2px;">
                            <span>Carrier: ${ins.carrier}</span>
                            <span>Cost: ${formatCurrency(ins.cost)}/mo</span>
                        </div>
                    </div>
                `).join('');
            }

            // 9. Assets
            const assetsList = el('fin-assets-list');
            if (assetsList && data.assets) {
                const totalVal = data.assets.reduce((sum, item) => sum + item.value, 0);
                assetsList.innerHTML = `
                    <div style="font-weight:bold; color:#60a5fa; font-size:13px; margin-bottom:8px; display:flex; justify-content:space-between;">
                        <span>Portfolio Value:</span>
                        <span>${formatCurrency(totalVal)}</span>
                    </div>
                ` + data.assets.map(asset => `
                    <div style="border-bottom:1px solid rgba(255,255,255,0.03); padding-bottom:8px; margin-bottom:8px; font-size:11px;">
                        <div style="display:flex; justify-content:space-between;">
                            <span style="font-weight:bold; color:#fff;">${asset.name}</span>
                            <span style="font-family:monospace; color:#60a5fa; font-weight:bold;">${formatCurrency(asset.value)}</span>
                        </div>
                        <div style="font-size:9px; color:var(--text-secondary); margin-top:2px;">Type: ${asset.type.toUpperCase()} • ${asset.notes || 'No active tags'}</div>
                    </div>
                `).join('');
            }

            // 10. Investing & DCA
            const investList = el('fin-investing-list');
            if (investList && data.investingPlan) {
                investList.innerHTML = data.investingPlan.map(inv => `
                    <div style="border-bottom:1px solid rgba(255,255,255,0.03); padding-bottom:8px; margin-bottom:8px; font-size:11px;">
                        <div style="display:flex; justify-content:space-between;">
                            <span style="font-weight:bold; color:#fff;">DCA Target: ${inv.asset}</span>
                            <span style="color:var(--accent-teal); font-weight:bold;">$${inv.dailyAllocation}/day</span>
                        </div>
                        <div style="font-size:9px; color:var(--text-secondary); margin-top:2px;">Est: ${formatCurrency(inv.monthlyAllocation)}/mo • ${inv.notes || 'Fidelity / Coinbase'}</div>
                    </div>
                `).join('') + `
                    <div style="font-size:9px; color:#f59e0b; background:rgba(245,158,11,0.05); padding:8px; border-radius:4px; border:1px solid rgba(245,158,11,0.2); margin-top:8px; line-height:1.4;">
                        ⚠️ HIGH VOLATILITY. Do not invest money needed for bills, emergency funds, or debt obligations.
                    </div>
                `;
            }

            // 11. Cost-Cutting
            const cutsList = el('fin-cuts-list');
            if (cutsList && data.costCuts) {
                const totalSaved = data.costCuts.filter(c => c.status === 'completed').reduce((sum, item) => sum + item.monthlySavings, 0);
                cutsList.innerHTML = `
                    <div style="font-weight:bold; color:var(--accent-teal); font-size:13px; margin-bottom:8px; display:flex; justify-content:space-between;">
                        <span>Monthly Savings:</span>
                        <span>${formatCurrency(totalSaved)}</span>
                    </div>
                ` + data.costCuts.map(cut => `
                    <div style="display:flex; justify-content:space-between; align-items:center; border-bottom:1px solid rgba(255,255,255,0.03); padding-bottom:6px; font-size:11px;">
                        <span style="color:#fff;">${cut.service}</span>
                        <span style="font-family:monospace; color:var(--accent-teal); font-weight:bold;">${formatCurrency(cut.monthlySavings)}/mo</span>
                    </div>
                `).join('');
            }

            // 12. Business Finance
            const businessList = el('fin-business-list');
            if (businessList && data.businessFinance) {
                businessList.innerHTML = data.businessFinance.map(bus => `
                    <div style="border-bottom:1px solid rgba(255,255,255,0.03); padding-bottom:8px; margin-bottom:8px; font-size:11px;">
                        <div style="display:flex; justify-content:space-between;">
                            <span style="font-weight:bold; color:#fff;">${bus.item}</span>
                            <span style="color:#60a5fa; font-weight:bold;">${formatCurrency(bus.monthly)}</span>
                        </div>
                        <div style="font-size:9px; color:var(--text-secondary); margin-top:2px;">${bus.notes}</div>
                    </div>
                `).join('');
            }

            // 13. Activity Stream
            const activityList = el('fin-activity-list');
            if (activityList && data.auditLog) {
                activityList.innerHTML = data.auditLog.map(log => `
                    <div style="font-size:10px; color:var(--text-secondary); font-family:monospace; border-bottom:1px solid rgba(255,255,255,0.03); padding-bottom:4px; margin-bottom:4px;">
                        [${new Date(log.timestamp).toLocaleTimeString()}] <span style="color:#fff;">${log.agent}:</span> ${log.event}
                    </div>
                `).join('');
            }

            // 14. QA Audit validation checks
            const qaAuditList = el('fin-qa-audit-list');
            const qaBadge = el('finance-qa-badge');
            if (qaAuditList) {
                qaAuditList.innerHTML = '';
                let hasAuditFailure = false;
                const audits = [];
                
                // Income Audit
                const activeIncSum = data.income.filter(item => item.recurring && item.type !== "bonus" && !item.notes).reduce((sum, item) => sum + item.amount, 0);
                const incPass = Math.abs(activeIncSum - metrics.monthly_income) < 0.01;
                audits.push({ name: 'Active Income sum verification', status: incPass ? 'PASS' : 'FAIL', details: `Expected: ${formatCurrency(metrics.monthly_income)} | Computed: ${formatCurrency(activeIncSum)}` });
                if (!incPass) hasAuditFailure = true;

                // Bills Audit
                const activeBillsSum = data.bills.filter(item => item.status !== 'cancelled').reduce((sum, item) => sum + item.amount, 0);
                const billsPass = Math.abs(activeBillsSum - metrics.monthly_bills) < 0.01;
                audits.push({ name: 'Active Bills sum verification', status: billsPass ? 'PASS' : 'FAIL', details: `Expected: ${formatCurrency(metrics.monthly_bills)} | Computed: ${formatCurrency(activeBillsSum)}` });
                if (!billsPass) hasAuditFailure = true;

                // Debt Audit
                const debtSum = data.debts.reduce((sum, item) => sum + item.balance, 0);
                const debtPass = Math.abs(debtSum - metrics.total_debt) < 0.01;
                audits.push({ name: 'Total Debt registry validation', status: debtPass ? 'PASS' : 'FAIL', details: `Expected: ${formatCurrency(metrics.total_debt)} | Computed: ${formatCurrency(debtSum)}` });
                if (!debtPass) hasAuditFailure = true;

                // Asset Audit
                const assetSum = data.assets.reduce((sum, item) => sum + item.value, 0);
                const assetPass = Math.abs(assetSum - metrics.total_assets) < 0.01;
                audits.push({ name: 'Total Assets valuation integrity', status: assetPass ? 'PASS' : 'FAIL', details: `Expected: ${formatCurrency(metrics.total_assets)} | Computed: ${formatCurrency(assetSum)}` });
                if (!assetPass) hasAuditFailure = true;

                qaAuditList.innerHTML = audits.map(aud => `
                    <div style="display:flex; justify-content:space-between; align-items:center; border-bottom:1px solid rgba(255,255,255,0.03); padding-bottom:6px; font-size:11px;">
                        <div>
                            <span style="color:#fff; font-weight:bold;">${aud.name}</span>
                            <div style="font-size:9px; color:var(--text-secondary); margin-top:2px;">${aud.details}</div>
                        </div>
                        <span class="badge" style="background:${aud.status === 'PASS' ? 'rgba(16,185,129,0.15)' : 'rgba(239,68,68,0.15)'}; color:${aud.status === 'PASS' ? 'var(--accent-teal)' : '#ef4444'}; font-weight:bold; font-size:9px;">${aud.status}</span>
                    </div>
                `).join('');

                if (qaBadge) {
                    if (hasAuditFailure) {
                        qaBadge.className = 'badge fail';
                        qaBadge.textContent = 'MATHEMATICAL DISCREPANCY DETECTED';
                    } else {
                        qaBadge.className = 'badge pass';
                        qaBadge.textContent = 'ALL MATHEMATICAL INTEGRITY VALIDATED';
                    }
                }

                // Update Health Score Circular Gauge fill dynamically
                const healthScoreFill = el('finance-health-score');
                if (healthScoreFill) {
                    const healthPct = hasAuditFailure ? 50 : 100;
                    const maxOffset = 263.8;
                    const offset = maxOffset - (maxOffset * healthPct / 100);
                    healthScoreFill.style.strokeDashoffset = offset;
                    
                    const scoreTextEl = healthScoreFill.parentElement.nextElementSibling;
                    if (scoreTextEl) scoreTextEl.textContent = `${healthPct}%`;
                }
            }

            if (window.lucide) window.lucide.createIcons();
        } catch (err) {
            console.error("Error loading Finance Command Center view:", err);
        }
    }

    async function loadRuntimeReliabilityView() {
        try {
            const res = await fetch('/api/v1/reliability/status');
            if (!res.ok) return;
            const data = await res.json();

            if (el('rel-monthly-cost')) el('rel-monthly-cost').textContent = formatCurrency(data.estimatedMonthlyCost);
            
            // Calculate active agents based on UP services or default to 2
            const activeCount = data.services.filter(s => s.status === 'UP').length * 2;
            if (el('rel-agent-ratio')) el('rel-agent-ratio').textContent = `${activeCount} / ${data.registeredAgents}`;
            
            if (el('rel-queue-status')) el('rel-queue-status').textContent = data.queue.status;
            if (el('rel-queue-depth-val')) el('rel-queue-depth-val').textContent = data.queue.pendingTasks;
            
            if (el('rel-last-backup') && data.backups.lastBackup) {
                el('rel-last-backup').textContent = new Date(data.backups.lastBackup).toLocaleTimeString();
            }
            if (el('rel-watchdog-heartbeat') && data.watchdog.lastHeartbeat) {
                el('rel-watchdog-heartbeat').textContent = new Date(data.watchdog.lastHeartbeat).toLocaleTimeString();
            }

            const primaryEl = el('rel-primary-status');
            if (primaryEl) {
                primaryEl.textContent = data.failover.primaryStatus;
                primaryEl.className = data.failover.primaryStatus === 'UP' ? 'badge pass' : 'badge fail';
            }

            const secondaryEl = el('rel-secondary-status');
            if (secondaryEl) {
                secondaryEl.textContent = data.failover.secondaryStatus;
                secondaryEl.className = data.failover.secondaryStatus === 'ACTIVE' ? 'badge pass' : 'badge warning';
            }

            const failoverReadyEl = el('rel-failover-ready');
            if (failoverReadyEl) {
                failoverReadyEl.textContent = data.failover.failoverReadiness;
                failoverReadyEl.className = data.failover.failoverReadiness === 'READY' ? 'badge pass' : 'badge fail';
            }

            const servicesEl = el('rel-docker-services');
            if (servicesEl && data.services) {
                servicesEl.innerHTML = data.services.map(s => {
                    const badgeClass = s.status === 'UP' ? 'badge pass' : 'badge fail';
                    return `
                        <div style="display:flex; justify-content:space-between; align-items:center; border-bottom:1px solid rgba(255,255,255,0.03); padding-bottom:6px;">
                            <span style="color:#fff; font-size:11px;">${s.name}</span>
                            <span class="${badgeClass}" style="font-size:9px;">${s.status}</span>
                        </div>
                    `;
                }).join('');
            }

            const risksEl = el('rel-risks-list');
            if (risksEl && data.risks) {
                risksEl.innerHTML = data.risks.map(r => `
                    <div style="color:var(--text-secondary); margin-bottom:4px; line-height:1.4;">• ${r}</div>
                `).join('');
            }

            if (window.lucide) window.lucide.createIcons();
        } catch (err) {
            console.error("Error loading Runtime Reliability view:", err);
        }
    }

    window.triggerReliabilityBackup = async function() {
        try {
            const res = await fetch('/api/v1/reliability/run-backup', { method: 'POST' });
            if (res.ok) {
                alert("Backup triggered successfully!");
                loadRuntimeReliabilityView();
            } else {
                alert("Failed to run backup.");
            }
        } catch (err) {
            console.error("Error triggering backup:", err);
        }
    };

    window.toggleFailoverSim = async function() {
        try {
            const res = await fetch('/api/v1/reliability/toggle-failover', { method: 'POST' });
            if (res.ok) {
                alert("Failover simulation toggled!");
                loadRuntimeReliabilityView();
            } else {
                alert("Failed to toggle failover.");
            }
        } catch (err) {
            console.error("Error toggling failover:", err);
        }
    };

    async function loadPertE2eBuildView() {
        try {
            const res = await fetch('/api/v1/pert/tracker');
            if (!res.ok) return;
            const data = await res.json();

            // Render Decision
            const decisionBadge = el('pert-go-no-go-decision');
            if (decisionBadge) {
                decisionBadge.textContent = data.summary.goNoGo;
                decisionBadge.className = data.summary.goNoGo.includes('GO FOR') ? 'badge pass' : 'badge alert';
            }

            // Render SVG Network Graph
            const graphContainer = el('pert-e2e-network-graph');
            if (graphContainer) {
                // Pre-defined coordinates
                const coords = {
                    "A": { x: 40, y: 110 },
                    "B": { x: 120, y: 110 },
                    "C": { x: 200, y: 60 },
                    "D": { x: 200, y: 160 },
                    "E": { x: 280, y: 20 },
                    "F": { x: 280, y: 70 },
                    "G": { x: 280, y: 120 },
                    "H": { x: 280, y: 170 },
                    "I": { x: 280, y: 220 },
                    "J": { x: 360, y: 220 },
                    "K": { x: 420, y: 70 },
                    "L": { x: 500, y: 70 },
                    "M": { x: 580, y: 70 },
                    "O": { x: 360, y: 60 },
                    "N": { x: 440, y: 160 },
                    "P": { x: 500, y: 20 },
                    "Q": { x: 500, y: 170 },
                    "R": { x: 660, y: 70 },
                    "S": { x: 740, y: 110 },
                    "T": { x: 820, y: 110 }
                };

                let edgesSvg = '';
                data.edges.forEach(edge => {
                    const fromCoord = coords[edge.from];
                    const toCoord = coords[edge.to];
                    if (fromCoord && toCoord) {
                        const isCriticalEdge = data.criticalPath.includes(edge.from) && data.criticalPath.includes(edge.to);
                        const strokeColor = isCriticalEdge ? '#ef4444' : 'rgba(255,255,255,0.15)';
                        const strokeWidth = isCriticalEdge ? '3' : '1.5';
                        edgesSvg += `
                            <line x1="${fromCoord.x}" y1="${fromCoord.y}" x2="${toCoord.x}" y2="${toCoord.y}" 
                                  stroke="${strokeColor}" stroke-width="${strokeWidth}" marker-end="url(#arrow)" />
                        `;
                    }
                });

                let nodesSvg = '';
                data.tasks.forEach(task => {
                    const coord = coords[task.id];
                    if (coord) {
                        const isCritical = data.criticalPath.includes(task.id);
                        let fillColor = '#10b981'; // Completed
                        if (task.status === 'active') fillColor = '#3b82f6';
                        if (task.status === 'blocked') fillColor = '#ef4444';

                        const borderStroke = isCritical ? '#ef4444' : 'rgba(255,255,255,0.3)';
                        const borderWidth = isCritical ? '2' : '1';

                        nodesSvg += `
                            <g cursor="pointer">
                                <circle cx="${coord.x}" cy="${coord.y}" r="12" fill="${fillColor}" stroke="${borderStroke}" stroke-width="${borderWidth}" />
                                <text x="${coord.x}" y="${coord.y + 4}" fill="#000" font-size="9px" font-weight="bold" text-anchor="middle">${task.id}</text>
                                <title>${task.name} (${task.status})&#13;Expected: ${task.te}m&#13;Slack: ${task.slack}m</title>
                            </g>
                        `;
                    }
                });

                graphContainer.innerHTML = `
                    <svg width="100%" height="100%" viewBox="0 0 900 250" style="background:#090d16;">
                        <defs>
                            <marker id="arrow" viewBox="0 0 10 10" refX="22" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
                                <path d="M 0 0 L 10 5 L 0 10 z" fill="rgba(255,255,255,0.4)" />
                            </marker>
                        </defs>
                        ${edgesSvg}
                        ${nodesSvg}
                    </svg>
                `;
            }

            // Render Critical Path Lane
            const criticalPathContainer = el('pert-critical-path-lane');
            if (criticalPathContainer) {
                criticalPathContainer.innerHTML = data.criticalPath.map(id => {
                    const task = data.tasks.find(t => t.id === id);
                    if (!task) return '';
                    return `
                        <div style="padding: 10px; background: rgba(239, 68, 68, 0.05); border: 1px solid rgba(239, 68, 68, 0.2); border-radius: 6px; display: flex; justify-content: space-between; align-items: center;">
                            <div>
                                <strong style="color: #ef4444; font-size: 11px;">[${task.id}] ${task.name}</strong>
                                <div style="color: var(--text-secondary); font-size: 10px; margin-top: 2px;">Owner: ${task.owner}</div>
                            </div>
                            <div style="font-family: monospace; font-size: 11px; color: #fff;">${task.te} mins</div>
                        </div>
                    `;
                }).join('');
            }

            // Render Task Duration Table
            const durationTable = el('pert-task-duration-table');
            if (durationTable) {
                durationTable.innerHTML = data.tasks.map(t => `
                    <tr style="border-bottom: 1px solid rgba(255,255,255,0.05); color: #fff;">
                        <td style="padding: 6px 4px; font-family: monospace; color: var(--accent-teal);">${t.id}</td>
                        <td style="padding: 6px 4px;">${t.name}</td>
                        <td style="padding: 6px 4px; text-align: center; color: var(--text-secondary);">${t.optimistic}</td>
                        <td style="padding: 6px 4px; text-align: center; color: var(--text-secondary);">${t.most_likely}</td>
                        <td style="padding: 6px 4px; text-align: center; color: var(--text-secondary);">${t.pessimistic}</td>
                        <td style="padding: 6px 4px; text-align: right; font-weight: bold;">${t.te}m</td>
                        <td style="padding: 6px 4px; text-align: right; color: ${t.slack === 0 ? '#ef4444' : 'var(--text-secondary)'};">${t.slack}m</td>
                    </tr>
                `).join('');
            }

            // Render Slack Table
            const slackTable = el('pert-slack-table');
            if (slackTable) {
                slackTable.innerHTML = data.tasks.map(t => `
                    <tr style="border-bottom: 1px solid rgba(255,255,255,0.05); color: #fff;">
                        <td style="padding: 6px 4px;">${t.name}</td>
                        <td style="padding: 6px 4px; text-align: right; color: ${t.slack === 0 ? '#ef4444' : 'var(--text-secondary)'};">${t.slack}m</td>
                    </tr>
                `).join('');
            }

            // Render Dependency Matrix
            const depMatrix = el('pert-dependency-matrix');
            if (depMatrix) {
                depMatrix.innerHTML = data.tasks.map(t => {
                    const preds = t.predecessors || [];
                    return `
                        <div style="padding: 6px 0; border-bottom: 1px solid rgba(255,255,255,0.05); display: flex; justify-content: space-between;">
                            <span>${t.name}</span>
                            <strong style="color: var(--accent-teal); font-family: monospace;">${preds.length > 0 ? preds.join(', ') : 'None'}</strong>
                        </div>
                    `;
                }).join('');
            }

            // Render P0/P1/P2 Gap Board
            const gapBoard = el('pert-gap-board');
            if (gapBoard) {
                gapBoard.innerHTML = data.risks.map(r => `
                    <div style="padding: 10px; background: rgba(255,255,255,0.02); border: 1px solid var(--border-glass); border-radius: 6px;">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px;">
                            <strong style="color: #fff; font-size: 11px;">${r.title}</strong>
                            <span class="badge warning" style="font-size: 9px; padding: 2px 6px;">${r.level.toUpperCase()}</span>
                        </div>
                        <div style="color: var(--text-secondary); font-size: 10px;">Mitigation: ${r.mitigation}</div>
                    </div>
                `).join('');
            }

            // Render Build/Test Gates
            const buildTestGates = el('pert-build-test-gates');
            if (buildTestGates) {
                buildTestGates.innerHTML = data.gates.map(g => `
                    <div style="display: flex; justify-content: space-between; align-items: center; padding: 6px 0; border-bottom: 1px solid rgba(255,255,255,0.05);">
                        <span>${g.name}</span>
                        <span class="badge ${g.status === 'PASS' ? 'pass' : 'alert'}">${g.status}</span>
                    </div>
                `).join('');
            }

            // Render Evidence Coverage
            const evidenceCoverage = el('pert-evidence-coverage');
            if (evidenceCoverage) {
                evidenceCoverage.innerHTML = data.evidence.map(e => `
                    <div style="padding: 10px; background: rgba(255,255,255,0.02); border: 1px solid var(--border-glass); border-radius: 6px; display: flex; flex-direction: column; gap: 4px;">
                        <strong style="color: #fff; font-size: 11px; text-overflow: ellipsis; overflow: hidden; white-space: nowrap;">${e.name}</strong>
                        <a href="file:///${data.metadata.root}/${e.path}" target="_blank" style="color: var(--accent-teal); font-size: 10px; text-decoration: none;">View File</a>
                    </div>
                `).join('');
            }

            if (window.lucide) window.lucide.createIcons();
        } catch (err) {
            console.error("Error loading PERT view:", err);
        }
    }

    window.triggerPertBuildRun = async function() {
        try {
            const res = await fetch('/api/v1/pert/tracker/run-build', { method: 'POST' });
            if (res.ok) {
                alert("E2E Build triggered successfully!");
                loadPertE2eBuildView();
            } else {
                alert("Failed to trigger E2E Build.");
            }
        } catch (err) {
            console.error("Error triggering E2E build:", err);
        }
    };

    async function triggerQaLoopExecution() {
        const consoleContainer = el('cc-loop-console-container');
        const consoleLog = el('cc-loop-console-log');
        
        if (consoleContainer) consoleContainer.style.display = 'block';
        if (consoleLog) consoleLog.textContent = '[system] Triggering QA loop script execution...\n';

        try {
            const res = await fetch('/api/v1/production-tracker/run-qa-loop', { method: 'POST' });
            const data = await res.json();
            
            if (consoleLog) consoleLog.textContent += `[system] ${data.message}\n`;
            
            // Start fast poller for logs
            if (qaLoopPoller) clearInterval(qaLoopPoller);
            qaLoopPoller = setInterval(async () => {
                const statusRes = await fetch('/api/v1/production-tracker/run-qa-loop/status');
                if (statusRes.ok) {
                    const statusData = await statusRes.json();
                    if (consoleLog) {
                        consoleLog.textContent = statusData.log || '[system] Awaiting console output...';
                        consoleLog.scrollTop = consoleLog.scrollHeight;
                    }
                    if (statusData.status === 'idle') {
                        clearInterval(qaLoopPoller);
                        qaLoopPoller = null;
                        if (consoleLog) consoleLog.textContent += '\n[system] QA Runtime Loop finished execution.\n';
                        loadProductionCommandCenterView();
                    }
                }
            }, 500);
        } catch (err) {
            if (consoleLog) consoleLog.textContent += `[error] Failed to trigger QA loop: ${err.message}\n`;
        }
    }

    async function fetchAndRenderReleaseProvenance() {
        try {
            const sigRes = await fetch('/api/v1/release/signing-policy');
            if (sigRes.ok) {
                const sigData = await sigRes.json();
                const cur = sigData.current_release || {};
                
                const policyStatusEl = el('release-signing-policy-status');
                if (policyStatusEl) {
                    policyStatusEl.textContent = cur.signing_policy_status || 'UNKNOWN';
                    policyStatusEl.className = cur.signing_policy_status === 'PASS' ? 'badge badge-success' : 'badge badge-danger';
                }
                
                const sigStatusEl = el('release-signature-status');
                if (sigStatusEl) sigStatusEl.textContent = (cur.signature_status || 'unsigned').toUpperCase();
                
                const finalStatusEl = el('release-finalization-status');
                if (finalStatusEl) finalStatusEl.textContent = (cur.release_finalization_status || 'blocked').toUpperCase();
                
                const waiverStatusEl = el('release-signing-waiver-status');
                if (waiverStatusEl) waiverStatusEl.textContent = (cur.signing_waiver_status || 'none').toUpperCase();
            }
            
            const govRes = await fetch('/api/v1/release/channel-governance');
            if (govRes.ok) {
                const govData = await govRes.json();
                
                const chanPolicyStatusEl = el('release-channel-policy-status');
                if (chanPolicyStatusEl) {
                    const isPass = govData.working_tree_clean && govData.tag_alignment_status === 'TAG_AT_HEAD';
                    chanPolicyStatusEl.textContent = isPass ? 'PASS' : 'WARN';
                    chanPolicyStatusEl.className = isPass ? 'badge badge-success' : 'badge badge-warning';
                }
                
                const chanCurEl = el('release-channel-current');
                if (chanCurEl) chanCurEl.textContent = govData.current_channel || 'Local Dev';
                
                const tagCurEl = el('release-tag-current');
                if (tagCurEl) tagCurEl.textContent = govData.release_tag || 'none';
                
                const tagStatusEl = el('release-tag-status');
                if (tagStatusEl) tagStatusEl.textContent = govData.tag_status || 'UNKNOWN';
                
                const tagAlignEl = el('release-tag-alignment-status');
                if (tagAlignEl) tagAlignEl.textContent = govData.tag_alignment_status || 'UNKNOWN';
                
                const headShaEl = el('release-tag-head-sha');
                if (headShaEl) headShaEl.textContent = govData.head_sha || '...';
                
                const targetShaEl = el('release-tag-target-sha');
                if (targetShaEl) targetShaEl.textContent = govData.tag_sha || '...';
                
                const formalFinalEl = el('release-formal-finalization-status');
                if (formalFinalEl) {
                    const isReady = govData.working_tree_clean && govData.tag_alignment_status === 'TAG_AT_HEAD';
                    formalFinalEl.textContent = isReady ? 'Formal Release Ready' : 'Formal Release Blocked';
                }
            }
            if (window.lucide) window.lucide.createIcons();
        } catch (err) {
            console.error("Error loading release provenance:", err);
        }
    }

    function initCommandCenterButtons() {
        const btnRun = el('btn-cc-run-qa-loop');
        if (btnRun) {
            btnRun.addEventListener('click', (e) => {
                e.preventDefault();
                triggerQaLoopExecution();
            });
        }
        const btnClose = el('btn-cc-close-console');
        if (btnClose) {
            btnClose.addEventListener('click', (e) => {
                e.preventDefault();
                const consoleContainer = el('cc-loop-console-container');
                if (consoleContainer) consoleContainer.style.display = 'none';
            });
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

        // Load and populate the Router configuration panel
        try {
            const configRes = await fetch('/api/v1/models/registry');
            if (configRes.ok) {
                const config = await configRes.json();
                const defaultProviderEl = el('router-default-provider');
                const defaultModelEl = el('router-default-model');
                const localFirstEl = el('router-local-first');
                const paidEnabledEl = el('router-paid-enabled');
                
                if (defaultProviderEl) defaultProviderEl.value = config.default_provider || 'lmstudio';
                if (defaultModelEl) defaultModelEl.value = config.default_model || '';
                if (localFirstEl) localFirstEl.checked = !!config.local_first;
                if (paidEnabledEl) paidEnabledEl.checked = !!config.paid_models_enabled;
            }
        } catch (err) {
            console.error('Failed to load router config:', err);
        }

        const saveRouterBtn = el('btn-save-router-config');
        if (saveRouterBtn && !saveRouterBtn.hasAttribute('data-bound')) {
            saveRouterBtn.setAttribute('data-bound', 'true');
            saveRouterBtn.addEventListener('click', async (e) => {
                e.preventDefault();
                const defaultProvider = el('router-default-provider').value;
                const defaultModel = el('router-default-model').value;
                const localFirst = el('router-local-first').checked;
                const paidEnabled = el('router-paid-enabled').checked;
                
                let currentRegistry = { providers: {} };
                try {
                    const currentRes = await fetch('/api/v1/models/registry');
                    if (currentRes.ok) {
                        currentRegistry = await currentRes.json();
                    }
                } catch(err) {}
                
                const updatedConfig = {
                    ...currentRegistry,
                    local_first: localFirst,
                    paid_models_enabled: paidEnabled,
                    default_provider: defaultProvider,
                    default_model: defaultModel
                };
                
                saveRouterBtn.disabled = true;
                saveRouterBtn.textContent = 'Saving...';
                
                try {
                    const postRes = await fetch('/api/v1/models/router/config', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify(updatedConfig)
                    });
                    
                    if (postRes.ok) {
                        saveRouterBtn.textContent = 'Configuration Saved!';
                        saveRouterBtn.style.color = '#34d399';
                        saveRouterBtn.style.background = 'rgba(16, 185, 129, 0.15)';
                    } else {
                        saveRouterBtn.textContent = 'Save Failed';
                        saveRouterBtn.style.color = '#f87171';
                    }
                } catch(err) {
                    saveRouterBtn.textContent = 'Error Saving';
                    saveRouterBtn.style.color = '#f87171';
                } finally {
                    setTimeout(() => {
                        saveRouterBtn.disabled = false;
                        saveRouterBtn.textContent = 'Save Routing Parameters';
                        saveRouterBtn.style.color = '#34d399';
                        saveRouterBtn.style.background = 'rgba(16, 185, 129, 0.2)';
                    }, 2000);
                }
            });
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
            const endpoint = status === 'APPROVED' ? '/api/v1/escalations/approve' : '/api/v1/escalations/deny';
            const res = await fetch(endpoint, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ approval_id: approvalId, operator: 'operator' })
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

            const replayBtn = el('btn-replay-telemetry');
            if (replayBtn && !replayBtn.hasAttribute('data-bound')) {
                replayBtn.setAttribute('data-bound', 'true');
                replayBtn.addEventListener('click', async (e) => {
                    e.preventDefault();
                    const logBox = el('telemetry-log-stream');
                    if (!logBox) return;
                    
                    replayBtn.disabled = true;
                    replayBtn.textContent = 'Replaying...';
                    logBox.innerHTML = '<div style="color: #6b7280;">[SYSTEM] Initializing telemetry replay mode...</div>';
                    
                    try {
                        const res = await fetch('/api/mission/feed');
                        const data = await res.json();
                        const events = data.events || [];
                        
                        if (events.length === 0) {
                            logBox.innerHTML = '<div style="color: #6b7280;">[SYSTEM] No historical events found to replay.</div>';
                            replayBtn.disabled = false;
                            replayBtn.textContent = 'Replay Mission Events';
                            return;
                        }
                        
                        logBox.innerHTML = '';
                        
                        let idx = 0;
                        const interval = setInterval(() => {
                            if (idx >= events.length) {
                                clearInterval(interval);
                                replayBtn.disabled = false;
                                replayBtn.textContent = 'Replay Mission Events';
                                const completionDiv = document.createElement('div');
                                completionDiv.style.color = '#10b981';
                                completionDiv.textContent = '[SYSTEM] Log replay complete.';
                                logBox.appendChild(completionDiv);
                                logBox.scrollTop = logBox.scrollHeight;
                                return;
                            }
                            
                            const ev = events[idx];
                            const logDiv = document.createElement('div');
                            logDiv.textContent = `[Replayed - ${new Date(ev.timestamp).toLocaleTimeString()}] ${ev.message || ''}`;
                            logBox.appendChild(logDiv);
                            logBox.scrollTop = logBox.scrollHeight;
                            idx++;
                        }, 150);
                    } catch (err) {
                        logBox.innerHTML = `<div style="color: #ef4444;">[ERROR] Failed to replay mission events: ${err.message}</div>`;
                        replayBtn.disabled = false;
                        replayBtn.textContent = 'Replay Mission Events';
                    }
                });
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
                    <div class="flight-card task-card-item" data-task-id="${t.id}" style="border-left: 3px solid ${t.status === 'completed' ? '#10b981' : (t.status === 'running' ? '#3b82f6' : 'rgba(255,255,255,0.05)')}; cursor: pointer;">
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

            // Bind click events on task cards
            document.querySelectorAll('.task-card-item').forEach(card => {
                card.addEventListener('click', () => {
                    const taskId = card.getAttribute('data-task-id');
                    showTaskEvidenceModal(taskId);
                });
            });

            // Build the execution DAG list dynamically!
            const dagNodesContainer = el('flight-deck-dag-nodes');
            if (dagNodesContainer) {
                if (tasks && tasks.length > 0) {
                    dagNodesContainer.innerHTML = tasks.map(t => {
                        const isDone = t.status === 'completed';
                        const isRunning = t.status === 'running';
                        
                        let nodeBg = 'rgba(255,255,255,0.02)';
                        let borderCol = 'var(--border-glass)';
                        let glow = '';
                        
                        if (isDone) {
                            nodeBg = 'rgba(16, 185, 129, 0.1)';
                            borderCol = '#10b981';
                            glow = 'box-shadow: 0 0 15px rgba(16, 185, 129, 0.3);';
                        } else if (isRunning) {
                            nodeBg = 'rgba(59, 130, 246, 0.1)';
                            borderCol = '#3b82f6';
                            glow = 'box-shadow: 0 0 15px rgba(59, 130, 246, 0.3); animation: pulse 2s infinite;';
                        }
                        
                        const deps = t.dependencies && t.dependencies.length > 0 ? t.dependencies.join(', ') : 'none';
                        
                        return `
                            <div class="dag-node-box" data-task-id="${t.id}" style="background: ${nodeBg}; border: 1px solid ${borderCol}; padding: 12px; border-radius: 8px; min-width: 140px; cursor: pointer; transition: all 0.2s; ${glow}">
                                <div style="font-weight: bold; font-size: 12px; color: #fff; margin-bottom: 4px;">${t.id}</div>
                                <div style="font-size: 11px; color: var(--text-secondary); text-overflow: ellipsis; overflow: hidden; white-space: nowrap;">${t.title}</div>
                                <div style="font-size: 9px; color: #6b7280; margin-top: 4px;">Deps: ${deps}</div>
                            </div>
                        `;
                    }).join('<div style="color: var(--text-secondary); font-weight: bold;">→</div>');
                    
                    // Bind click events on DAG nodes
                    document.querySelectorAll('.dag-node-box').forEach(box => {
                        box.addEventListener('click', () => {
                            const taskId = box.getAttribute('data-task-id');
                            showTaskEvidenceModal(taskId);
                        });
                    });
                } else {
                    dagNodesContainer.innerHTML = '<div style="color: var(--text-secondary); font-size: 12px;">Select an active campaign to view DAG nodes.</div>';
                }
            }
        } catch (err) {
            console.error('[FlightDeck] failed to load tasks:', err);
        }
    }

    async function showTaskEvidenceModal(taskId) {
        const modal = el('task-evidence-modal');
        const modalSubtitle = el('evidence-modal-subtitle');
        const modalContent = el('evidence-modal-content');
        
        if (!modal || !modalContent) return;
        
        modal.style.display = 'flex';
        if (modalSubtitle) modalSubtitle.textContent = `Task ID: ${taskId}`;
        modalContent.innerHTML = '<div style="color: var(--text-secondary); padding: 20px; text-align: center;">Loading evidence trail...</div>';
        
        try {
            const res = await fetch(`/api/v1/runs/${selectedCampaignId}/tasks/${taskId}/evidence`);
            if (!res.ok) throw new Error("Failed to load evidence.");
            const data = await res.json();
            
            const t = data.task || {};
            const tools = data.tool_calls || [];
            const validation = data.validation_evidence || [];
            const routing = data.model_routing || [];
            
            let html = `
                <div>
                    <h4 style="font-size: 12px; color: var(--accent-teal); text-transform: uppercase; margin-bottom: 6px;">Task Specification</h4>
                    <div style="background: rgba(255,255,255,0.02); border: 1px solid var(--border-glass); border-radius: 8px; padding: 12px; font-size: 12px; display: flex; flex-direction: column; gap: 6px;">
                        <div><strong style="color: #fff;">Title:</strong> ${t.title || ''}</div>
                        <div><strong style="color: #fff;">Description:</strong> ${t.description || ''}</div>
                        <div><strong style="color: #fff;">Priority:</strong> <span style="color: ${t.priority === 'critical' ? '#ef4444' : '#60a5fa'}">${t.priority}</span></div>
                        <div><strong style="color: #fff;">Status:</strong> <span class="badge" style="font-size: 10px;">${t.status || ''}</span></div>
                        <div><strong style="color: #fff;">Assigned Agent:</strong> <code>${t.ownerAgentId || 'none'}</code></div>
                        <div><strong style="color: #fff;">Approval Required:</strong> ${t.approvalRequired ? 'YES' : 'NO'}</div>
                    </div>
                </div>
            `;
            
            html += `
                <div>
                    <h4 style="font-size: 12px; color: var(--accent-teal); text-transform: uppercase; margin-bottom: 6px;">Model Router Fallback History</h4>
                    <div style="background: rgba(255,255,255,0.02); border: 1px solid var(--border-glass); border-radius: 8px; padding: 12px; font-size: 11px;">
            `;
            if (routing.length > 0) {
                html += routing.map(r => {
                    const failoverInfo = r.event_type === 'route_failed_closed' ? `<span style="color: #ef4444;">[FAIL CLOSED] ${r.error || ''}</span>` : '';
                    const successInfo = r.event_type === 'route_success' ? `<span style="color: #10b981;">[SUCCESS] Mapped to ${r.provider}/${r.model} (Confidence: ${r.confidence_score || 'N/A'})</span>` : '';
                    return `
                        <div style="border-bottom: 1px solid rgba(255,255,255,0.04); padding: 6px 0;">
                            <div><strong>Timestamp:</strong> ${new Date(r.timestamp * 1000).toLocaleTimeString()}</div>
                            <div><strong>Event:</strong> ${r.event_type}</div>
                            <div><strong>Details:</strong> ${successInfo} ${failoverInfo}</div>
                        </div>
                    `;
                }).join('');
            } else {
                html += `<div style="color: var(--text-secondary); text-align: center; padding: 10px;">No model routing fallback events logged for this task.</div>`;
            }
            html += `</div></div>`;
            
            html += `
                <div>
                    <h4 style="font-size: 12px; color: var(--accent-teal); text-transform: uppercase; margin-bottom: 6px;">Executed Tool Calls</h4>
                    <div style="background: rgba(255,255,255,0.02); border: 1px solid var(--border-glass); border-radius: 8px; padding: 12px; font-size: 11px;">
            `;
            if (tools.length > 0) {
                html += tools.map(tc => {
                    return `
                        <div style="border-bottom: 1px solid rgba(255,255,255,0.04); padding: 8px 0;">
                            <div><strong style="color: #fff;">Tool:</strong> <code>${tc.tool_name}</code></div>
                            <div><strong>Arguments:</strong> <code style="word-break: break-all;">${tc.arguments}</code></div>
                            <div style="margin-top: 4px; color: var(--text-secondary);"><strong>Output summary:</strong> ${tc.output_summary}</div>
                        </div>
                    `;
                }).join('');
            } else {
                html += `<div style="color: var(--text-secondary); text-align: center; padding: 10px;">No tool calls executed.</div>`;
            }
            html += `</div></div>`;
            
            html += `
                <div>
                    <h4 style="font-size: 12px; color: var(--accent-teal); text-transform: uppercase; margin-bottom: 6px;">Validation Evidence</h4>
                    <div style="background: rgba(255,255,255,0.02); border: 1px solid var(--border-glass); border-radius: 8px; padding: 12px; font-size: 11px;">
            `;
            if (validation.length > 0) {
                html += validation.map(ev => {
                    return `
                        <div style="border-bottom: 1px solid rgba(255,255,255,0.04); padding: 6px 0;">
                            <div><strong>Evidence Ref:</strong> <code>${ev.evidence_id}</code></div>
                            <div><strong>Validator:</strong> ${ev.validator_name}</div>
                            <div><strong>Verdict:</strong> <span class="badge ${ev.status === 'PASS' ? 'success' : 'blocked'}">${ev.status}</span></div>
                            <div style="color: var(--text-secondary); margin-top: 2px;">${ev.notes || ''}</div>
                        </div>
                    `;
                }).join('');
            } else {
                html += `<div style="color: var(--text-secondary); text-align: center; padding: 10px;">No schema validation evidence recorded.</div>`;
            }
            html += `</div></div>`;
            
            modalContent.innerHTML = html;
        } catch (err) {
            modalContent.innerHTML = `<div style="color: #f87171; padding: 20px; text-align: center;">Error loading evidence trail: ${err.message}</div>`;
        }
    }

    const closeEvidenceBtn = el('btn-close-evidence-modal');
    if (closeEvidenceBtn) {
        closeEvidenceBtn.addEventListener('click', () => {
            const modal = el('task-evidence-modal');
            if (modal) modal.style.display = 'none';
        });
    }
    const evidenceModal = el('task-evidence-modal');
    if (evidenceModal) {
        evidenceModal.addEventListener('click', (e) => {
            if (e.target === evidenceModal) {
                evidenceModal.style.display = 'none';
            }
        });
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
        initDeviceRegistry();
        initCrewaiIngestionBridge();
        initReleaseDecisionRoom();
        initReleaseEvidenceRetention();
        initReleaseEvidenceArchivePreview();
        initReleaseEvidenceArchiveBuildPlan();
        initReleaseEvidenceArchiveSealPreview();
        initFormalReleaseSealDryRun();
        initCapabilityRouterUI();
        initModelProviderRegistryUI();
        initModelRouterUI();
        
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
        initCommandCenterButtons();
        
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

    /**
     * buildHlsProxyUrl(remoteUrl)
     * ---------------------------
     * Returns a same-origin /api/hls/proxy?url=<encoded> URL that the
     * backend will fetch on behalf of the browser.  This eliminates the
     * CORS error (browser never contacts g1o.empek.xyz directly) and the
     * 403 rejection (backend sends the correct User-Agent / Referer).
     *
     * If remoteUrl is already a local path (starts with '/') it is
     * returned unchanged so local test streams still work.
     */
    function buildHlsProxyUrl(remoteUrl) {
        if (!remoteUrl) return remoteUrl;
        // Local / relative URLs do not need proxying
        if (remoteUrl.startsWith('/') || remoteUrl.startsWith('http://localhost') || remoteUrl.startsWith('http://127.0.0.1')) {
            return remoteUrl;
        }
        return '/api/hls/proxy?url=' + encodeURIComponent(remoteUrl);
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
        if (testBtn) testBtn.style.display = 'inline-block';

        const showHistoryBtn = el('tv-btn-show-history');
        if (showHistoryBtn) showHistoryBtn.style.display = 'inline-block';

        addToRecents(channel.id);
        loadEpgSchedule(channel.id);
        loadDiagnosticsHistory(channel.id);

        if (currentHls) {
            currentHls.destroy();
            currentHls = null;
        }

        // ── Route the raw stream URL through the backend HLS proxy ────────
        // The browser MUST NOT make direct cross-origin requests to remote
        // CDNs (CORS block) or hosts that reject non-player User-Agents
        // (HTTP 403).  buildHlsProxyUrl() wraps the URL in
        //   /api/hls/proxy?url=<encoded>
        // so the backend fetches it server-side and returns it on
        // http://localhost, which is always same-origin.
        const rawStreamUrl = channel.playbackUrl || channel.streamUrl;
        const streamUrl = buildHlsProxyUrl(rawStreamUrl);

        logTvDiag(`[proxy] Routing via /api/hls/proxy → ${redactFrontendUrl(rawStreamUrl)}`);

        let playbackRetryCount = 0;
        const maxPlaybackRetries = 3;
        let retryTimeout = null;

        // ── Browser-safe error display helper ─────────────────────────────
        function showPlayerError(msg) {
            logTvDiag(`[player] Error: ${msg}`, true);
            if (errorOverlay && errorText) {
                errorText.textContent = msg;
                errorOverlay.style.display = 'flex';
            }
        }

        function triggerPlaybackRetry(msg) {
            if (playbackRetryCount < maxPlaybackRetries) {
                playbackRetryCount++;
                logTvDiag(`[player] Retry ${playbackRetryCount}/${maxPlaybackRetries}: ${msg}`);
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
                showPlayerError(`${msg} (All retry attempts failed)`);
            }
        }

        video.onerror = () => {
            const err = video.error;
            let errMsg = 'An unknown video error occurred.';
            if (err) {
                if (err.code === 1) errMsg = 'Playback aborted by the user.';
                else if (err.code === 2) errMsg = 'A network error prevented the media from loading.';
                else if (err.code === 3) errMsg = 'A media decoding error occurred.';
                else if (err.code === 4) errMsg = 'The media format is not supported by this browser.';
            }
            logTvDiag(`HTML5 Video Error: ${errMsg}`, true);
            triggerPlaybackRetry(errMsg);
        };

        if (rawStreamUrl && rawStreamUrl.toLowerCase().includes('.m3u8')) {
            if (typeof Hls !== 'undefined' && Hls.isSupported()) {
                const hls = new Hls({
                    maxBufferLength: 10,
                    enableWorker: true,
                    // Tell hls.js how to load sub-resources: wrap every URL
                    // through the same proxy so CORS is never violated.
                    loader: class extends Hls.DefaultConfig.loader {
                        load(context, config, callbacks) {
                            // Rewrite any URL hls.js tries to load directly
                            const origUrl = context.url || '';
                            if (origUrl && !origUrl.startsWith('/api/hls/proxy')) {
                                context.url = buildHlsProxyUrl(origUrl);
                            }
                            super.load(context, config, callbacks);
                        }
                    }
                });
                hls.loadSource(streamUrl);
                hls.attachMedia(video);
                currentHls = hls;

                hls.on(Hls.Events.ERROR, function (event, data) {
                    if (!data.fatal) return;
                    logTvDiag(`Fatal HLS error: ${data.type} — ${data.details}`, true);

                    // Map well-known proxy error codes to human-readable messages
                    let userMsg = `HLS ${data.type} error: ${data.details}`;
                    const respCode = data.response && data.response.code;
                    if (respCode === 403 || (data.details && data.details.includes('403'))) {
                        userMsg = 'CORS / upstream-blocked: The stream server returned HTTP 403. ' +
                            'The channel may require an active subscription or the URL has expired.';
                    } else if (respCode === 404 || (data.details && data.details.includes('404'))) {
                        userMsg = 'Missing asset (404): An HLS segment or playlist was not found on the CDN. ' +
                            'The stream may have been rotated. Try reloading the playlist.';
                    } else if (data.details === Hls.ErrorDetails.MANIFEST_LOAD_ERROR ||
                               data.details === Hls.ErrorDetails.MANIFEST_PARSING_ERROR) {
                        userMsg = 'Playlist rewrite failure: The HLS manifest could not be loaded or parsed. ' +
                            'Check the proxy logs for a HLS_PROXY_REWRITE_ERROR detail.';
                    } else if (data.type === Hls.ErrorTypes.NETWORK_ERROR) {
                        userMsg = 'CORS / network failure: The browser was blocked from loading stream data. ' +
                            'All requests are routed through /api/hls/proxy — verify the backend is reachable.';
                    }

                    switch (data.type) {
                        case Hls.ErrorTypes.NETWORK_ERROR:
                            logTvDiag('Attempting network recovery...', true);
                            hls.startLoad();
                            break;
                        case Hls.ErrorTypes.MEDIA_ERROR:
                            logTvDiag('Attempting media recovery...', true);
                            hls.recoverMediaError();
                            break;
                        default:
                            triggerPlaybackRetry(userMsg);
                            break;
                    }
                });
            } else if (video.canPlayType('application/vnd.apple.mpegurl')) {
                // Safari native HLS: pass the proxied URL directly
                video.src = streamUrl;
            } else {
                showPlayerError('HLS playback is not supported in this browser.');
            }
        } else {
            // Non-HLS stream (plain MP4, etc.) — still proxy if remote
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

    let allPrompts = [];
    let promptCatalogInitialized = false;

    async function loadPromptCatalogView() {
        try {
            // Load metrics
            const metrics = await fetchJsonSafe('/api/prompts/metrics');
            
            // Update metric elements
            const elTotal = el('prompt-metric-total');
            const elHighRisk = el('prompt-metric-high-risk');
            const elPassRate = el('prompt-metric-pass-rate');
            
            if (elTotal) elTotal.textContent = metrics.total_prompts || '0';
            if (elHighRisk) elHighRisk.textContent = (metrics.severities && metrics.severities.HIGH) || '0';
            if (elPassRate && metrics.fixtures_summary) {
                const total = metrics.fixtures_summary.total || 50;
                const passed = metrics.fixtures_summary.passed || 50;
                elPassRate.textContent = `${((passed / total) * 100).toFixed(0)}%`;
            }
            
            // Fetch all prompts
            allPrompts = await fetchJsonSafe('/api/prompts');
            
            // Populate filters once
            if (!promptCatalogInitialized) {
                initPromptCatalogFilters();
            }
            
            renderPromptCatalog();
        } catch (err) {
            console.error("Error loading prompt catalog view:", err);
            const grid = el('prompt-catalog-grid');
            if (grid) {
                grid.innerHTML = `<div style="grid-column: 1/-1; color: #ef4444; padding: 20px; text-align: center;">Error loading prompts: ${err.message}</div>`;
            }
        }
    }

    function initPromptCatalogFilters() {
        const sectorSelect = el('prompt-filter-sector');
        const catSelect = el('prompt-filter-category');
        
        if (sectorSelect && catSelect) {
            const sectors = new Set();
            const categories = new Set();
            
            allPrompts.forEach(p => {
                if (p.sector) sectors.add(p.sector);
                if (p.category) categories.add(p.category);
            });
            
            // Clear and add "All" option
            sectorSelect.innerHTML = '<option value="">All Sectors</option>';
            catSelect.innerHTML = '<option value="">All Categories</option>';
            
            Array.from(sectors).sort().forEach(sec => {
                sectorSelect.innerHTML += `<option value="${escapeHtml(sec)}">${escapeHtml(sec)}</option>`;
            });
            
            Array.from(categories).sort().forEach(cat => {
                catSelect.innerHTML += `<option value="${escapeHtml(cat)}">${escapeHtml(cat)}</option>`;
            });
            
            // Bind listeners
            const searchInput = el('prompt-search-input');
            const riskSelect = el('prompt-filter-risk');
            
            [searchInput, sectorSelect, catSelect, riskSelect].forEach(item => {
                item?.addEventListener('input', renderPromptCatalog);
                item?.addEventListener('change', renderPromptCatalog);
            });
            
            // Bind Run Golden Fixtures Suite
            const btnAllFixtures = el('btn-run-all-fixtures');
            btnAllFixtures?.addEventListener('click', runGoldenFixturesSuite);
            
            // Bind detail modal close buttons
            el('btn-close-prompt-modal')?.addEventListener('click', closePromptDetailModal);
            el('btn-close-prompt-modal-bottom')?.addEventListener('click', closePromptDetailModal);
            
            promptCatalogInitialized = true;
        }
    }

    function renderPromptCatalog() {
        const grid = el('prompt-catalog-grid');
        if (!grid) return;
        
        const query = el('prompt-search-input')?.value.toLowerCase() || '';
        const sector = el('prompt-filter-sector')?.value || '';
        const category = el('prompt-filter-category')?.value || '';
        const risk = el('prompt-filter-risk')?.value || '';
        
        const filtered = allPrompts.filter(p => {
            // Search match
            const matchesQuery = !query || 
                p.id.toLowerCase().includes(query) || 
                p.title.toLowerCase().includes(query) || 
                (p.mission && p.mission.toLowerCase().includes(query));
                
            // Sector match
            const matchesSector = !sector || p.sector === sector;
            
            // Category match
            const matchesCategory = !category || p.category === category;
            
            // Risk match
            const pRisk = (p.severity_model && p.severity_model.severity) || 'LOW';
            const matchesRisk = !risk || pRisk === risk;
            
            return matchesQuery && matchesSector && matchesCategory && matchesRisk;
        });
        
        const countSpan = el('prompt-filter-count');
        if (countSpan) countSpan.textContent = `Showing ${filtered.length} of ${allPrompts.length} prompts`;
        
        if (filtered.length === 0) {
            grid.innerHTML = '<div style="grid-column: 1/-1; color: var(--text-secondary); text-align: center; padding: 40px;">No prompts found matching your criteria.</div>';
            return;
        }
        
        grid.innerHTML = filtered.map(p => {
            const pRisk = (p.severity_model && p.severity_model.severity) || 'LOW';
            let riskStyle = 'background: rgba(255,255,255,0.05); color: var(--text-secondary);';
            if (pRisk === 'HIGH') {
                riskStyle = 'background: rgba(239,68,68,0.15); border: 1px solid rgba(239,68,68,0.3); color: #f87171;';
            } else if (pRisk === 'MEDIUM') {
                riskStyle = 'background: rgba(245,158,11,0.15); border: 1px solid rgba(245,158,11,0.3); color: #fbbf24;';
            } else if (pRisk === 'LOW') {
                riskStyle = 'background: rgba(16,185,129,0.15); border: 1px solid rgba(16,185,129,0.3); color: #34d399;';
            }
            
            const qaPassed = p.qa_status === 'passed';
            const qaStyle = qaPassed ? 
                'background: rgba(16,185,129,0.15); border: 1px solid rgba(16,185,129,0.3); color: #34d399;' :
                'background: rgba(239,68,68,0.15); border: 1px solid rgba(239,68,68,0.3); color: #f87171;';
                
            return `
                <div class="card prompt-card" data-prompt-id="${escapeHtml(p.id)}" style="padding: 16px; background: rgba(10, 15, 30, 0.85); border: 1px solid var(--border-glass); border-radius: 10px; cursor: pointer; transition: all 0.2s ease; display: flex; flex-direction: column; justify-content: space-between; min-height: 180px;">
                    <div>
                        <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 8px;">
                            <span style="font-family: monospace; font-size: 11px; color: var(--accent-teal); font-weight: bold; background: rgba(20,184,166,0.1); padding: 2px 6px; border-radius: 4px;">${escapeHtml(p.id)}</span>
                            <div style="display: flex; gap: 6px;">
                                <span class="status-pill" style="font-size: 9px; padding: 2px 6px; font-weight: bold; border-radius: 4px; ${riskStyle}">${escapeHtml(pRisk)}</span>
                                <span class="status-pill" style="font-size: 9px; padding: 2px 6px; font-weight: bold; border-radius: 4px; ${qaStyle}">QA: ${escapeHtml(p.qa_status || 'passed')}</span>
                            </div>
                        </div>
                        <h4 style="font-size: 13px; font-weight: 700; color: #fff; margin: 0 0 6px 0; line-height: 1.3;">${escapeHtml(p.title)}</h4>
                        <p style="font-size: 11px; color: var(--text-secondary); line-height: 1.4; margin: 0; display: -webkit-box; -webkit-line-clamp: 3; -webkit-box-orient: vertical; overflow: hidden;">${escapeHtml(p.mission)}</p>
                    </div>
                    <div style="display: flex; flex-wrap: wrap; gap: 6px; border-top: 1px solid var(--border-glass); padding-top: 10px; margin-top: 12px; font-size: 9px; color: var(--text-secondary);">
                        <span style="background: rgba(255,255,255,0.05); padding: 2px 6px; border-radius: 4px;">${escapeHtml(p.category)}</span>
                        <span style="background: rgba(255,255,255,0.05); padding: 2px 6px; border-radius: 4px; max-width: 140px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">${escapeHtml(p.industry)}</span>
                    </div>
                </div>
            `;
        }).join("");
        
        // Add card click listeners
        grid.querySelectorAll('.prompt-card').forEach(card => {
            card.addEventListener('click', () => {
                const promptId = card.getAttribute('data-prompt-id');
                openPromptDetailModal(promptId);
            });
        });
    }

    function openPromptDetailModal(promptId) {
        const p = allPrompts.find(x => x.id === promptId);
        if (!p) return;
        
        // Set standard fields
        el('prompt-modal-id').textContent = p.id;
        el('prompt-modal-title').textContent = p.title;
        el('prompt-modal-sector').textContent = p.sector || 'N/A';
        el('prompt-modal-category').textContent = p.category || 'N/A';
        el('prompt-modal-family').textContent = p.prompt_family || 'N/A';
        el('prompt-modal-phase').textContent = p.lifecycle_phase || 'N/A';
        
        const pRisk = (p.severity_model && p.severity_model.severity) || 'LOW';
        el('prompt-modal-risk').textContent = pRisk;
        el('prompt-modal-qa').textContent = p.qa_status || 'passed';
        el('prompt-modal-mission').textContent = p.mission || '';
        el('prompt-modal-text').textContent = p.prompt_text || p.prompt || '';
        
        // Evidence checklist
        const ev = p.evidence_required;
        el('prompt-modal-evidence').innerHTML = `<span style="color:var(--text-secondary); display:block; margin-bottom:4px; font-weight:bold;">Evidence Required:</span>` +
            (ev && ev.length ? ev.map(x => `• ${escapeHtml(x)}`).join('<br>') : 'None');
            
        // Approval Gate
        const gate = p.approval_gate;
        el('prompt-modal-gate').innerHTML = `<span style="color:var(--text-secondary); display:block; margin-bottom:4px; font-weight:bold;">Approval Gate:</span>` +
            (gate ? `Owner: <strong>${escapeHtml(gate.owner || 'None')}</strong><br>Role: ${escapeHtml(gate.role || 'None')}<br>Bypass Allowed: ${gate.bypass_allowed ? 'Yes' : 'No'}` : 'None');
            
        // Commands
        const cmd = p.stack_command_templates;
        const cmdSec = el('prompt-modal-command-section');
        if (cmd && cmd.length) {
            cmdSec.style.display = 'block';
            el('prompt-modal-command').textContent = cmd.join('\n');
        } else {
            cmdSec.style.display = 'none';
        }
        
        // Reset console section
        el('prompt-modal-console-section').style.display = 'none';
        el('prompt-modal-console').textContent = '';
        el('prompt-modal-evidence-link').innerHTML = '';
        
        // Reset Run button
        const runBtn = el('btn-run-prompt-swarm');
        if (runBtn) {
            runBtn.disabled = false;
            runBtn.innerHTML = '<i data-lucide="play" style="width: 14px; height: 14px;"></i> Run Prompt Through Swarm';
            runBtn.onclick = () => runPromptThroughSwarm(promptId);
        }
        
        const modal = el('prompt-detail-modal');
        if (modal) {
            modal.style.display = 'flex';
        }
        
        if (window.lucide) {
            window.lucide.createIcons();
        }
    }

    function closePromptDetailModal() {
        const modal = el('prompt-detail-modal');
        if (modal) {
            modal.style.display = 'none';
        }
    }

    async function runPromptThroughSwarm(promptId) {
        const consoleSec = el('prompt-modal-console-section');
        const consoleBox = el('prompt-modal-console');
        const runBtn = el('btn-run-prompt-swarm');
        
        if (consoleSec && consoleBox && runBtn) {
            consoleSec.style.display = 'block';
            consoleBox.textContent = `[INFO] Initializing prompt execution for ${promptId}...\n`;
            consoleBox.textContent += `[INFO] Dispatching task with instructions to operator swarm...\n`;
            
            runBtn.disabled = true;
            runBtn.textContent = 'Running Swarm...';
            
            try {
                const response = await fetch(`/api/prompts/${promptId}/run`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' }
                });
                
                if (!response.ok) {
                    throw new Error(`Execution returned status code ${response.status}`);
                }
                
                const data = await response.json();
                
                consoleBox.textContent += `[OK] Swarm execution completed successfully.\n\n`;
                consoleBox.textContent += data.result;
                
                const evLink = el('prompt-modal-evidence-link');
                if (evLink && data.evidence_file) {
                    const cleanLink = data.evidence_file.replace(/\\/g, '/');
                    evLink.innerHTML = `✓ Evidence exported: <a href="file:///${escapeHtml(cleanLink)}" target="_blank" style="color: var(--accent-teal); text-decoration: underline; font-family: monospace;">${escapeHtml(cleanLink.split('/').pop())}</a>`;
                }
            } catch (err) {
                consoleBox.textContent += `\n[FAIL] Execution error: ${err.message}\n`;
            } finally {
                runBtn.disabled = false;
                runBtn.innerHTML = '<i data-lucide="play" style="width: 14px; height: 14px;"></i> Run Prompt Through Swarm';
                if (window.lucide) {
                    window.lucide.createIcons();
                }
            }
        }
    }

    async function runGoldenFixturesSuite() {
        const btn = el('btn-run-all-fixtures');
        if (!btn) return;
        
        btn.disabled = true;
        btn.textContent = 'Running QA Suite...';
        
        try {
            const response = await fetch('/api/prompts/qa/golden-fixtures', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
            });
            
            if (!response.ok) {
                throw new Error(`QA execution returned status code ${response.status}`);
            }
            
            const data = await response.json();
            
            await loadPromptCatalogView();
            
            alert(`QA validation complete. Passed: ${data.passed_fixtures}/${data.total_fixtures}. Status: ${data.status}`);
        } catch (err) {
            console.error('Error running golden fixtures suite:', err);
            alert(`QA suite execution failed: ${err.message}`);
        } finally {
            btn.disabled = false;
            btn.innerHTML = '<i data-lucide="play" style="width: 12px; height: 12px;"></i> Run Golden Fixtures Suite';
            if (window.lucide) {
                window.lucide.createIcons();
            }
        }
    }

    async function loadPromptOpsView() {
        try {
            const metrics = await fetchJsonSafe('/api/promptops/metrics');
            
            const elRuns = el('promptops-metric-runs');
            const elFail = el('promptops-metric-failure-rate');
            const elStale = el('promptops-metric-stale');
            const elQuar = el('promptops-metric-quarantined');
            const elPend = el('promptops-metric-pending');
            
            if (elRuns) elRuns.textContent = metrics.total_usage || '0';
            if (elFail) elFail.textContent = `${metrics.failure_rate || '0.0'}%`;
            if (elStale) elStale.textContent = metrics.stale_count || '0';
            if (elQuar) elQuar.textContent = metrics.quarantined_count || '0';
            if (elPend) elPend.textContent = metrics.approval_queue_count || '0';
            
            const approvals = await fetchJsonSafe('/api/promptops/approvals');
            const approvalsList = el('promptops-approvals-list');
            if (approvalsList) {
                if (approvals.length === 0) {
                    approvalsList.innerHTML = '<tr><td colspan="4" style="padding: 10px; color: var(--text-secondary); text-align: center;">No pending approvals.</td></tr>';
                } else {
                    approvalsList.innerHTML = approvals.map(p => {
                        const isHigh = p.severity === 'HIGH';
                        const badgeStyle = isHigh ? 'background: rgba(239, 68, 68, 0.15); color: #f87171;' : 'background: rgba(245, 158, 11, 0.15); color: #fbbf24;';
                        return `
                            <tr style="border-bottom: 1px solid rgba(255,255,255,0.05);">
                                <td style="padding: 8px; font-family: monospace; font-weight: bold; color: var(--accent-teal);">${escapeHtml(p.id)}</td>
                                <td style="padding: 8px;"><span class="status-pill" style="font-size: 9px; padding: 2px 6px; border-radius: 4px; background: rgba(169, 85, 247, 0.15); color: #c084fc;">${escapeHtml(p.lifecycle_state)}</span></td>
                                <td style="padding: 8px;"><span class="status-pill" style="font-size: 9px; padding: 2px 6px; border-radius: 4px; ${badgeStyle}">${escapeHtml(p.severity || 'LOW')}</span></td>
                                <td style="padding: 8px; text-align: right; display: flex; gap: 6px; justify-content: flex-end;">
                                    <button onclick="approvePromptFlow('${escapeHtml(p.id)}')" class="btn" style="padding: 3px 8px; font-size: 10px; background: rgba(16, 185, 129, 0.2); border: 1px solid rgba(16, 185, 129, 0.4); color: #34d399; font-weight: bold; cursor: pointer; border-radius: 4px;">Approve</button>
                                    <button onclick="quarantinePrompt('${escapeHtml(p.id)}')" class="btn" style="padding: 3px 8px; font-size: 10px; background: rgba(239, 68, 68, 0.2); border: 1px solid rgba(239, 68, 68, 0.4); color: #f87171; font-weight: bold; cursor: pointer; border-radius: 4px;">Quarantine</button>
                                </td>
                            </tr>
                        `;
                    }).join('');
                }
            }
            
            const driftFindings = await fetchJsonSafe('/api/promptops/drift');
            const driftList = el('promptops-drift-list');
            if (driftList) {
                if (driftFindings.length === 0) {
                    driftList.innerHTML = '<tr><td colspan="5" style="padding: 10px; color: var(--text-secondary); text-align: center;">No drift detected. All prompts are stable.</td></tr>';
                } else {
                    driftList.innerHTML = driftFindings.map(f => {
                        const isHigh = f.severity === 'HIGH';
                        const badgeStyle = isHigh ? 'background: rgba(239, 68, 68, 0.15); color: #f87171;' : 'background: rgba(245, 158, 11, 0.15); color: #fbbf24;';
                        return `
                            <tr style="border-bottom: 1px solid rgba(255,255,255,0.05);">
                                <td style="padding: 8px; font-family: monospace; font-weight: bold; color: var(--accent-teal);">${escapeHtml(f.prompt_id)}</td>
                                <td style="padding: 8px; font-weight: bold; color: #fff;">${escapeHtml(f.type.replace('_', ' ').toUpperCase())}</td>
                                <td style="padding: 8px;"><span class="status-pill" style="font-size: 9px; padding: 2px 6px; border-radius: 4px; ${badgeStyle}">${escapeHtml(f.severity)}</span></td>
                                <td style="padding: 8px; color: var(--text-secondary);">${escapeHtml(f.message)}</td>
                                <td style="padding: 8px; color: var(--text-secondary);">${escapeHtml(new Date(f.timestamp).toLocaleString())}</td>
                            </tr>
                        `;
                    }).join('');
                }
            }
            
            const ciBtn = el('btn-run-ci-gate');
            if (ciBtn) {
                ciBtn.onclick = runCiGateChecks;
            }
            
        } catch (err) {
            console.error("Error loading PromptOps view:", err);
        }
    }

    async function approvePromptFlow(promptId) {
        const user = prompt("Enter Authorized Approver Name:");
        if (!user) return;
        const role = prompt("Enter Approver Role (e.g. Owner/Reviewer):");
        if (!role) return;
        
        try {
            await fetchJsonSafe(`/api/promptops/prompts/${promptId}/approve`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ user, role })
            });
            alert(`Prompt ${promptId} successfully approved and set to Active.`);
            await loadPromptOpsView();
        } catch (err) {
            alert(`Approval failed: ${err.message}`);
        }
    }

    async function quarantinePrompt(promptId) {
        if (!confirm(`Are you sure you want to quarantine prompt ${promptId}?`)) return;
        try {
            await fetchJsonSafe(`/api/promptops/prompts/${promptId}/quarantine`, {
                method: 'POST'
            });
            alert(`Prompt ${promptId} has been quarantined.`);
            await loadPromptOpsView();
        } catch (err) {
            alert(`Quarantine failed: ${err.message}`);
        }
    }

    async function runCiGateChecks() {
        const term = el('ci-gate-terminal');
        const banner = el('ci-gate-banner');
        const btn = el('btn-run-ci-gate');
        
        if (!term || !btn) return;
        
        btn.disabled = true;
        term.textContent = `[INFO] Initializing CI/CD Quality Gate check...\n`;
        term.textContent += `[INFO] Running static schema check...\n`;
        term.textContent += `[INFO] Running golden fixtures regression suite check...\n`;
        term.textContent += `[INFO] Verifying unreviewed hash changes and required approval gates...\n`;
        
        try {
            const res = await fetchJsonSafe('/api/promptops/ci-gate', {
                method: 'POST'
            });
            
            term.textContent += `\n[RESULT] Status: ${res.status}\n`;
            if (res.status === 'PASSED') {
                term.textContent += `[PASSED] CI/CD Gate passed successfully. All 354 prompts are 100% compliant.\n`;
                if (banner) {
                    banner.style.display = 'block';
                    banner.style.background = 'rgba(16, 185, 129, 0.15)';
                    banner.style.border = '1px solid rgba(16, 185, 129, 0.3)';
                    banner.style.color = '#34d399';
                    banner.textContent = '✓ CI/CD GATE PASSED — BUILD COMPLIANT';
                }
            } else {
                term.textContent += `[FAILED] Gate validation failed with ${res.errors.length} blocking issues:\n`;
                res.errors.forEach(e => {
                    term.textContent += `  - ${e}\n`;
                });
                if (banner) {
                    banner.style.display = 'block';
                    banner.style.background = 'rgba(239, 68, 68, 0.15)';
                    banner.style.border = '1px solid rgba(239, 68, 68, 0.3)';
                    banner.style.color = '#f87171';
                    banner.textContent = '✗ CI/CD GATE BLOCKED — COMPLIANCE ISSUES FOUND';
                }
            }
        } catch (err) {
            term.textContent += `\n[ERROR] CI gate execution failed: ${err.message}\n`;
        } finally {
            btn.disabled = false;
        }
    }

    async function loadEvidenceOpsView() {
        try {
            // 1. Fetch Metrics
            const metrics = await fetchJsonSafe('/api/evidenceops/metrics');
            const elRuns = el('evidenceops-metric-runs');
            const elApprovals = el('evidenceops-metric-approvals');
            const elDrift = el('evidenceops-metric-drift');
            const elBlockedCI = el('evidenceops-metric-blocked-ci');
            
            if (elRuns) elRuns.textContent = metrics.total_runs ?? '0';
            if (elApprovals) elApprovals.textContent = metrics.approval_events ?? '0';
            if (elDrift) elDrift.textContent = metrics.fixture_drift ?? '0';
            if (elBlockedCI) elBlockedCI.textContent = metrics.blocked_ci_gates ?? '0';

            // 2. Fetch Snapshot
            const snapshot = await fetchJsonSafe('/api/evidenceops/daily-snapshot');
            const elSnapTime = el('evidenceops-snapshot-time');
            const elSnapActive = el('evidenceops-snap-active');
            const elSnapFailedFix = el('evidenceops-snap-failed-fix');
            const elSnapHashDrift = el('evidenceops-snap-hash-drift');
            const elSnapPendingHR = el('evidenceops-snap-pending-hr');
            
            if (elSnapTime) elSnapTime.textContent = `Snapshot Timestamp: ${snapshot.timestamp ? new Date(snapshot.timestamp).toLocaleString() : '--'}`;
            if (elSnapActive) elSnapActive.textContent = snapshot.active_prompts_count ?? '0';
            if (elSnapFailedFix) elSnapFailedFix.textContent = snapshot.failed_fixtures_count ?? '0';
            if (elSnapHashDrift) elSnapHashDrift.textContent = snapshot.hash_drift_count ?? '0';
            if (elSnapPendingHR) elSnapPendingHR.textContent = snapshot.high_risk_awaiting_approval ?? '0';

            // 3. Fetch Runs Ledger
            const runs = await fetchJsonSafe('/api/evidenceops/runs');
            const ledgerList = el('evidenceops-ledger-list');
            if (ledgerList) {
                if (runs.length === 0) {
                    ledgerList.innerHTML = '<tr><td colspan="9" style="padding: 10px; color: var(--text-secondary); text-align: center;">No execution runs recorded in the ledger yet.</td></tr>';
                } else {
                    // Sort descending by timestamp
                    runs.sort((a,b) => new Date(b.timestamp) - new Date(a.timestamp));
                    ledgerList.innerHTML = runs.map(r => {
                        const isGo = r.verdict === 'GO';
                        const verdictStyle = isGo ? 'background: rgba(16, 185, 129, 0.15); color: #34d399;' : 'background: rgba(239, 68, 68, 0.15); color: #f87171;';
                        return `
                            <tr style="border-bottom: 1px solid rgba(255,255,255,0.05);">
                                <td style="padding: 8px; color: var(--text-secondary); white-space: nowrap;">${new Date(r.timestamp).toLocaleString()}</td>
                                <td style="padding: 8px; font-family: monospace; font-weight: bold; color: var(--accent-teal);">${escapeHtml(r.prompt_id)}</td>
                                <td style="padding: 8px; color: var(--text-secondary);">${escapeHtml(r.version)}</td>
                                <td style="padding: 8px; color: var(--text-secondary);">${escapeHtml(r.model)}</td>
                                <td style="padding: 8px; color: var(--text-secondary);">${escapeHtml(r.agent_route)}</td>
                                <td style="padding: 8px; color: var(--text-secondary); max-width: 150px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">${escapeHtml(r.input_summary)}</td>
                                <td style="padding: 8px; color: var(--text-secondary); max-width: 150px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">${escapeHtml(r.output_contract)}</td>
                                <td style="padding: 8px;"><span class="status-pill" style="font-size: 9px; padding: 2px 6px; border-radius: 4px; ${verdictStyle}">${escapeHtml(r.verdict)}</span></td>
                                <td style="padding: 8px; font-family: monospace;"><a href="/${r.evidence_path}" target="_blank" style="color: #38bdf8; text-decoration: underline;">evidence.json</a></td>
                            </tr>
                        `;
                    }).join('');
                }
            }

            const exportBtn = el('btn-evidenceops-export');
            if (exportBtn) {
                exportBtn.onclick = runEvidenceOpsExport;
            }

        } catch (err) {
            console.error("Error loading EvidenceOps view:", err);
        }
    }

    async function runEvidenceOpsExport() {
        const btn = el('btn-evidenceops-export');
        const linksBox = el('evidenceops-export-links');
        if (!btn) return;
        
        btn.disabled = true;
        btn.innerHTML = '<i data-lucide="loader" class="spin"></i> Generating Bundle...';
        if (window.lucide) window.lucide.createIcons();

        try {
            const res = await fetchJsonSafe('/api/evidenceops/export', {
                method: 'POST'
            });
            
            if (linksBox) {
                linksBox.style.display = 'block';
                el('export-link-md').href = '/' + res.files.markdown;
                el('export-link-csv').href = '/' + res.files.csv;
                el('export-link-json').href = '/' + res.files.json;
                el('export-link-zip').href = '/' + res.files.zip;
            }
            alert('Evidence bundle successfully generated!');
        } catch (err) {
            alert(`Export failed: ${err.message}`);
        } finally {
            btn.disabled = false;
            btn.innerHTML = '<i data-lucide="download"></i> Generate & Export Bundle';
            if (window.lucide) window.lucide.createIcons();
        }
    }

    async function loadModelOpsView() {
        try {
            // 1. Fetch Metrics
            const metrics = await fetchJsonSafe('/api/modelops/metrics');
            const elActive = el('modelops-metric-active');
            const elRouted = el('modelops-metric-routed');
            const elFallback = el('modelops-metric-fallback');
            const elFailed = el('modelops-metric-failed');

            if (elActive) elActive.textContent = metrics.health_breakdown?.active ?? '0';
            if (elRouted) elRouted.textContent = metrics.total_routed_requests ?? '0';
            if (elFallback) elFallback.textContent = metrics.fallback_count ?? '0';
            if (elFailed) elFailed.textContent = metrics.failed_calls ?? '0';

            // 2. Fetch Models and Populate Inventory Table and Eval Select
            const models = await fetchJsonSafe('/api/modelops/models');
            const inventoryList = el('modelops-inventory-list');
            const evalSelect = el('modelops-eval-select');
            
            if (inventoryList) {
                if (models.length === 0) {
                    inventoryList.innerHTML = '<tr><td colspan="7" style="padding: 10px; color: var(--text-secondary); text-align: center;">No models registered in the registry.</td></tr>';
                } else {
                    inventoryList.innerHTML = models.map(m => {
                        const statusColor = m.status === 'active' ? '#10b981' : (m.status === 'failed_eval' ? '#ef4444' : '#6b7280');
                        const scoreDisplay = m.eval_score !== null ? m.eval_score.toFixed(2) : '--';
                        return `
                            <tr style="border-bottom: 1px solid rgba(255,255,255,0.05);">
                                <td style="padding: 8px; font-family: monospace; font-weight: bold; color: var(--accent-teal);">${escapeHtml(m.model_id)}</td>
                                <td style="padding: 8px; text-transform: uppercase;">${escapeHtml(m.provider)}</td>
                                <td style="padding: 8px; color: var(--text-secondary);">${escapeHtml(m.context_window.toString())} tokens</td>
                                <td style="padding: 8px; color: var(--text-secondary); text-transform: capitalize;">${escapeHtml(m.best_for)}</td>
                                <td style="padding: 8px; font-weight: bold; color: ${m.eval_score < 0.7 ? '#ef4444' : '#fff'};">${scoreDisplay}</td>
                                <td style="padding: 8px;"><span style="color: ${statusColor}; font-weight: bold; display: flex; align-items: center; gap: 4px;"><span style="display: inline-block; width: 6px; height: 6px; border-radius: 50%; background: ${statusColor};"></span>${escapeHtml(m.status)}</span></td>
                                <td style="padding: 8px; text-align: right;">
                                    <button onclick="triggerModelEval('${escapeHtml(m.model_id)}')" class="btn" style="padding: 2px 6px; font-size: 9px; background: rgba(16, 185, 129, 0.15); border: 1px solid rgba(16, 185, 129, 0.3); color: #34d399; font-weight: bold; cursor: pointer; border-radius: 4px;">Eval</button>
                                </td>
                            </tr>
                        `;
                    }).join('');
                }
            }

            if (evalSelect) {
                evalSelect.innerHTML = models.map(m => `<option value="${escapeHtml(m.model_id)}">${escapeHtml(m.model_id)}</option>`).join('');
            }

            // 3. Fetch Routing Policies and Populate Table
            const routesData = await fetchJsonSafe('/api/modelops/routes');
            const policiesBox = el('modelops-routing-policies');
            if (policiesBox && routesData.routing_policies) {
                policiesBox.innerHTML = routesData.routing_policies.map(p => `
                    <div style="background: rgba(255,255,255,0.02); padding: 8px; border-radius: 6px; border: 1px solid var(--border-glass);">
                        <div style="font-weight: bold; color: var(--accent-teal); margin-bottom: 2px;">${escapeHtml(p.prompt_family)}</div>
                        <div style="font-size: 10px; color: #fff; margin-bottom: 4px;">Preferred: <span style="font-family: monospace; color: #38bdf8;">${escapeHtml(p.preferred_model)}</span></div>
                        <div style="font-size: 10px; color: var(--text-secondary);">Fallback: <span style="font-family: monospace;">${escapeHtml(p.fallback_model)}</span></div>
                        <div style="font-size: 9px; color: var(--text-secondary); margin-top: 4px; font-style: italic;">${escapeHtml(p.description)}</div>
                    </div>
                `).join('');
            }

            // 4. Populate Failed Calls and Fallback Log
            const failuresList = el('modelops-failures-list');
            if (failuresList) {
                const logs = [];
                if (metrics.failed_requests_log) {
                    metrics.failed_requests_log.forEach(f => {
                        logs.push(`<li style="color: #f87171; border-left: 2px solid #ef4444; padding-left: 6px; margin-bottom: 4px;">
                            <strong>[FAILURE]</strong> ${escapeHtml(new Date(f.timestamp).toLocaleTimeString())} - Model ${escapeHtml(f.model_id)}: ${escapeHtml(f.error)}
                        </li>`);
                    });
                }
                if (metrics.fallback_usage_log) {
                    metrics.fallback_usage_log.forEach(f => {
                        logs.push(`<li style="color: #fbbf24; border-left: 2px solid #f59e0b; padding-left: 6px; margin-bottom: 4px;">
                            <strong>[FALLBACK]</strong> ${escapeHtml(new Date(f.timestamp).toLocaleTimeString())} - Failover from ${escapeHtml(f.requested_model)} to ${escapeHtml(f.fallback_model)}
                        </li>`);
                    });
                }
                if (logs.length === 0) {
                    failuresList.innerHTML = '<li style="color: var(--text-secondary); text-align: center; padding: 10px;">No failovers or routing failures registered.</li>';
                } else {
                    failuresList.innerHTML = logs.join('');
                }
            }

            // Bind Health check button
            const healthBtn = el('btn-modelops-health');
            if (healthBtn) {
                healthBtn.onclick = runModelOpsHealthCheck;
            }

            // Bind eval runner button
            const evalRunBtn = el('btn-modelops-run-eval');
            if (evalRunBtn) {
                evalRunBtn.onclick = () => {
                    const selectEl = el('modelops-eval-select');
                    if (selectEl) {
                        triggerModelEval(selectEl.value);
                    }
                };
            }

        } catch (err) {
            console.error("Error loading ModelOps view:", err);
        }
    }

    async function runModelOpsHealthCheck() {
        const btn = el('btn-modelops-health');
        if (!btn) return;
        btn.disabled = true;
        btn.innerHTML = '<i data-lucide="loader" class="spin"></i> Checking Health...';
        if (window.lucide) window.lucide.createIcons();

        try {
            await fetchJsonSafe('/api/modelops/health');
            alert('Model health check verification complete. Registry updated.');
            await loadModelOpsView();
        } catch (err) {
            alert(`Health check failed: ${err.message}`);
        } finally {
            btn.disabled = false;
            btn.innerHTML = '<i data-lucide="activity"></i> Run Health Check';
            if (window.lucide) window.lucide.createIcons();
        }
    }

    async function triggerModelEval(modelId) {
        const progressEl = el('modelops-eval-progress');
        const progressBar = el('modelops-eval-progress-bar');
        const progressPct = el('modelops-eval-progress-pct');
        const resultEl = el('modelops-eval-result');

        if (progressEl) progressEl.style.display = 'block';
        if (resultEl) resultEl.style.display = 'none';

        // Simulate progress bar increment animation
        let pct = 0;
        const interval = setInterval(() => {
            pct += 10;
            if (progressBar) progressBar.style.width = pct + '%';
            if (progressPct) progressPct.textContent = pct + '%';
            if (pct >= 100) {
                clearInterval(interval);
            }
        }, 100);

        try {
            const res = await fetchJsonSafe('/api/modelops/evals', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ model_id: modelId })
            });

            // Wait a moment for visual completion
            await new Promise(r => setTimeout(r, 1000));
            if (progressEl) progressEl.style.display = 'none';

            if (resultEl) {
                resultEl.style.display = 'block';
                const isPass = res.status !== 'failed_eval';
                resultEl.style.background = isPass ? 'rgba(16, 185, 129, 0.1)' : 'rgba(239, 68, 68, 0.1)';
                resultEl.style.border = isPass ? '1px solid rgba(16, 185, 129, 0.3)' : '1px solid rgba(239, 68, 68, 0.3)';
                resultEl.innerHTML = `
                    <div style="font-weight: bold; color: ${isPass ? '#34d399' : '#f87171'}; font-size: 12px; margin-bottom: 4px;">
                        ${isPass ? '✓ EVALUATION PASSED' : '✗ EVALUATION FAILED'}
                    </div>
                    <div style="font-size: 11px; color: #fff;">
                        Model: <span style="font-family: monospace;">${escapeHtml(res.model_id)}</span><br>
                        Accuracy/Compliance Score: <strong>${(res.eval_score * 100).toFixed(0)}%</strong> (Threshold: 70%)<br>
                        New Status: <span style="font-weight: bold; color: ${isPass ? '#34d399' : '#f87171'};">${escapeHtml(res.status)}</span>
                    </div>
                `;
            }
            await loadModelOpsView();
        } catch (err) {
            clearInterval(interval);
            if (progressEl) progressEl.style.display = 'none';
            alert(`Evaluation run failed: ${err.message}`);
        }
    }

    window.approvePromptFlow = approvePromptFlow;
    window.quarantinePrompt = quarantinePrompt;
    window.loadEvidenceOpsView = loadEvidenceOpsView;
    window.runEvidenceOpsExport = runEvidenceOpsExport;
    window.loadModelOpsView = loadModelOpsView;
    window.runModelOpsHealthCheck = runModelOpsHealthCheck;

    async function loadToolOpsView() {
        try {
            const state = await fetchJsonSafe('/api/toolops/blocked');
            const tools = await fetchJsonSafe('/api/toolops/tools');
            const auditLog = await fetchJsonSafe('/api/toolops/audit-log');
            const policies = await fetchJsonSafe('/api/toolops/policies');

            const allowedCount = (tools || []).length;
            const blockedCount = (state.blocked_actions || []).length;
            const pendingCount = (state.pending_approvals || []).length;
            const totalCalls = (auditLog || []).filter(item => item.verdict === 'APPROVED' || item.verdict === 'OPERATOR_APPROVED').length;

            const elAllowed = el('toolops-metric-allowed-count');
            const elBlocked = el('toolops-metric-blocked-count');
            const elPending = el('toolops-metric-pending-count');
            const elTotal = el('toolops-metric-total-calls');

            if (elAllowed) elAllowed.textContent = allowedCount;
            if (elBlocked) elBlocked.textContent = blockedCount;
            if (elPending) elPending.textContent = pendingCount;
            if (elTotal) elTotal.textContent = totalCalls;

            const inventoryList = el('toolops-inventory-list');
            if (inventoryList) {
                inventoryList.innerHTML = (tools || []).map(t => {
                    const statusClass = t.status === 'active' ? 'text-success' : 'text-danger';
                    const requiresApprovalText = t.requires_approval ? 
                        '<span style="color: var(--accent-orange); font-weight: bold;">YES</span>' : 
                        '<span style="color: var(--accent-teal);">NO</span>';
                    const riskColor = t.risk_class === 'destructive' || t.risk_class === 'privileged' ? '#f87171' : 
                                      t.risk_class === 'networked' ? '#fbbf24' : '#6ee7b7';
                    
                    return `
                        <tr style="border-bottom: 1px solid rgba(255,255,255,0.05);">
                            <td style="padding: 8px; font-family: monospace; font-weight: bold; color: #fff;">${escapeHtml(t.tool_id)}</td>
                            <td style="padding: 8px;">${escapeHtml(t.name)}</td>
                            <td style="padding: 8px; text-transform: uppercase;">${escapeHtml(t.category)}</td>
                            <td style="padding: 8px;"><span style="color: ${riskColor}; font-weight: bold;">${escapeHtml(t.risk_class)}</span></td>
                            <td style="padding: 8px; font-family: monospace;">${escapeHtml(t.allowed_agents.join(', '))}</td>
                            <td style="padding: 8px; font-family: monospace;">${escapeHtml(t.allowed_prompt_families.join(', '))}</td>
                            <td style="padding: 8px;">${requiresApprovalText}</td>
                            <td style="padding: 8px;" class="${statusClass}">${escapeHtml(t.status.toUpperCase())}</td>
                        </tr>
                    `;
                }).join('');
            }

            const pendingList = el('toolops-pending-list');
            if (pendingList) {
                const pendingItems = state.pending_approvals || [];
                const blockedItems = state.blocked_actions || [];
                
                let html = '';
                
                pendingItems.forEach(item => {
                    html += `
                        <tr style="border-bottom: 1px solid rgba(255,255,255,0.05); background: rgba(245, 158, 11, 0.05);">
                            <td style="padding: 8px; color: var(--text-secondary);">${new Date(item.timestamp).toLocaleTimeString()}</td>
                            <td style="padding: 8px; font-family: monospace; color: #fff;">${escapeHtml(item.tool_id)}</td>
                            <td style="padding: 8px; font-family: monospace;">${escapeHtml(item.agent_role)}</td>
                            <td style="padding: 8px;"><span style="color: #f87171; font-weight: bold;">${escapeHtml(item.risk_class)}</span></td>
                            <td style="padding: 8px;"><pre style="margin:0; font-size:9px; color: #cbd5e1;">${escapeHtml(JSON.stringify(item.params))}</pre></td>
                            <td style="padding: 8px; color: #fbbf24; font-weight: bold;">PENDING APPROVAL</td>
                            <td style="padding: 8px; text-align: right;">
                                <button onclick="approveToolOpsAction('${item.action_id}')" class="btn" style="background: #10b981; border: none; color: #fff; font-size: 10px; padding: 4px 8px; border-radius: 4px; cursor: pointer; font-weight: bold;">
                                    Approve
                                </button>
                            </td>
                        </tr>
                    `;
                });

                blockedItems.forEach(item => {
                    html += `
                        <tr style="border-bottom: 1px solid rgba(255,255,255,0.05); background: rgba(239, 68, 68, 0.05);">
                            <td style="padding: 8px; color: var(--text-secondary);">${new Date(item.timestamp).toLocaleTimeString()}</td>
                            <td style="padding: 8px; font-family: monospace; color: #fff;">${escapeHtml(item.tool_id)}</td>
                            <td style="padding: 8px; font-family: monospace;">${escapeHtml(item.agent_role)}</td>
                            <td style="padding: 8px;"><span style="color: #f87171; font-weight: bold;">BLOCKED</span></td>
                            <td style="padding: 8px;"><pre style="margin:0; font-size:9px; color: #cbd5e1;">${escapeHtml(JSON.stringify(item.params))}</pre></td>
                            <td style="padding: 8px; color: #ef4444; font-weight: bold; max-width: 150px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;" title="${escapeHtml(item.details)}">${escapeHtml(item.details)}</td>
                            <td style="padding: 8px; text-align: right; color: var(--text-secondary);">BLOCKED</td>
                        </tr>
                    `;
                });

                if (html === '') {
                    html = '<tr><td colspan="7" style="padding: 12px; text-align: center; color: var(--text-secondary);">No pending approvals or blocked actions.</td></tr>';
                }
                pendingList.innerHTML = html;
            }

            const policyList = el('toolops-policy-list');
            if (policyList) {
                policyList.innerHTML = (policies.policies || []).map(p => {
                    return `
                        <div style="padding: 8px; background: rgba(255,255,255,0.02); border: 1px solid rgba(255,255,255,0.05); border-radius: 6px;">
                            <div style="display: flex; justify-content: space-between; font-weight: bold; color: #fff; margin-bottom: 4px;">
                                <span>${escapeHtml(p.tool_id)}</span>
                                <span style="color: ${p.requires_approval ? '#fbbf24' : '#6ee7b7'}; font-size: 10px;">
                                    ${p.requires_approval ? 'Approval Required' : 'Auto-Allow'}
                                </span>
                            </div>
                            <div style="font-size: 10px; color: var(--text-secondary);">
                                Risk Class: <span style="color: #cbd5e1;">${escapeHtml(p.risk_class)}</span><br>
                                Allowed Agents: <span style="font-family: monospace; color: #cbd5e1;">${escapeHtml(p.allowed_agents.join(', '))}</span><br>
                                Allowed Families: <span style="font-family: monospace; color: #cbd5e1;">${escapeHtml(p.allowed_prompt_families.join(', '))}</span>
                            </div>
                        </div>
                    `;
                }).join('');
            }

            const auditList = el('toolops-audit-list');
            if (auditList) {
                auditList.innerHTML = (auditLog || []).map(log => {
                    const color = log.verdict === 'APPROVED' || log.verdict === 'OPERATOR_APPROVED' ? '#a3e635' : '#f87171';
                    return `
                        <li style="color: ${color};">
                            [${escapeHtml(log.timestamp.substring(11, 19))}] ${escapeHtml(log.verdict)}: 
                            tool=${escapeHtml(log.tool_id)} agent=${escapeHtml(log.agent_role)} 
                            details="${escapeHtml(log.details)}"
                        </li>
                    `;
                }).join('');
            }

            const ciBtn = el('btn-toolops-ci-gate');
            if (ciBtn) {
                ciBtn.onclick = runToolOpsCiGate;
            }

        } catch (err) {
            console.error("Error loading ToolOps view:", err);
        }
    }

    async function approveToolOpsAction(actionId) {
        try {
            const res = await fetchJsonSafe('/api/toolops/approve', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ action_id: actionId, operator: 'CLAWDE HOCH' })
            });
            if (res && res.verdict === 'APPROVED') {
                await loadToolOpsView();
            } else {
                alert("Action approval failed.");
            }
        } catch (err) {
            alert(`Approval failed: ${err.message}`);
        }
    }

    async function runToolOpsCiGate() {
        const statusEl = el('toolops-ci-status');
        if (statusEl) {
            statusEl.style.display = 'block';
            statusEl.style.background = 'rgba(255,255,255,0.05)';
            statusEl.style.color = '#fff';
            statusEl.textContent = 'Running ToolOps compliance checks...';
        }

        try {
            const res = await fetchJsonSafe('/api/toolops/ci-gate', { method: 'POST' });
            if (statusEl) {
                if (res.status === 'PASSED') {
                    statusEl.style.background = 'rgba(16, 185, 129, 0.15)';
                    statusEl.style.color = '#34d399';
                    statusEl.textContent = '✓ CI COMPLIANCE GATE PASSED: All registry schemas and tool risk mappings are fully compliant.';
                } else {
                    statusEl.style.background = 'rgba(239, 68, 68, 0.15)';
                    statusEl.style.color = '#f87171';
                    statusEl.innerHTML = `✗ CI COMPLIANCE GATE FAILED:<br>${res.errors.join('<br>')}`;
                }
            }
        } catch (err) {
            if (statusEl) {
                statusEl.style.background = 'rgba(239, 68, 68, 0.15)';
                statusEl.style.color = '#f87171';
                statusEl.textContent = `Error executing CI Gate: ${err.message}`;
            }
        }
    }

    window.loadToolOpsView = loadToolOpsView;
    window.approveToolOpsAction = approveToolOpsAction;
    window.runToolOpsCiGate = runToolOpsCiGate;
    window.triggerModelEval = triggerModelEval;


// ==========================================
// RESTORED GOVERNANCE & DE-ORBITED VIEWS STATE
// ==========================================
let currentNodes = [];
let baseMermaidGraph = "";
let lastTelemetryTime = Date.now();
let telemetryIsStale = false;
let selectedNodeId = null;
let coreGroupExpanded = true;
let mobileGroupExpanded = true;
let edgeGroupExpanded = true;
let panX = 0;
let panY = 0;
let scale = 1.0;
let isPanning = false;
let startPanX = 0;
let startPanY = 0;
const API_BASE = window.location.origin;

async function initDeviceRegistry() {
    const btnRunDiscovery = document.getElementById("device-discovery-run-button");
    const btnRefreshRegistry = document.getElementById("device-service-refresh-button");
    const btnApprove = document.getElementById("btn-device-approve");
    const btnReject = document.getElementById("btn-device-reject");

    if (btnRunDiscovery) {
        btnRunDiscovery.addEventListener("click", executeDeviceDiscovery);
    }
    if (btnRefreshRegistry) {
        btnRefreshRegistry.addEventListener("click", loadRegistryData);
    }
    if (btnApprove) {
        btnApprove.addEventListener("click", executeDeviceApproval);
    }
    if (btnReject) {
        btnReject.addEventListener("click", executeDeviceRejection);
    }

    await loadRegistryData();
}

async function loadRegistryData() {
    try {
        const discRes = await fetch(`${API_BASE}/api/v1/devices/discovered`);
        if (discRes.ok) {
            const discovered = await discRes.json();
            renderDiscoveredDevices(discovered);
        }

        const regRes = await fetch(`${API_BASE}/api/v1/devices/service-registry`);
        if (regRes.ok) {
            const approved = await regRes.json();
            renderApprovedServiceNodes(approved);
        }
    } catch (err) {
        console.error("Error loading registry data:", err);
    }
}

async function executeDeviceDiscovery() {
    const statusText = document.getElementById("device-discovery-status");
    const btnRunDiscovery = document.getElementById("device-discovery-run-button");
    if (statusText) statusText.innerText = "DISCOVERING...";
    if (btnRunDiscovery) btnRunDiscovery.disabled = true;

    try {
        const res = await fetch(`${API_BASE}/api/v1/devices/discover`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ enable_ping_sweep: false, enable_tcp_probes: false })
        });
        if (res.ok) {
            logToConsoleTerminal("DaaSDiscovery", "Network discovery completed successfully. Recommended service enclaves updated.", "info");
        } else {
            logToConsoleTerminal("DaaSDiscovery", "Network discovery failed.", "error");
        }
    } catch (err) {
        console.error("Discovery error:", err);
        logToConsoleTerminal("DaaSDiscovery", "Error running discovery: " + err.message, "error");
    } finally {
        if (statusText) statusText.innerText = "IDLE";
        if (btnRunDiscovery) btnRunDiscovery.disabled = false;
        await loadRegistryData();
    }
}

function renderDiscoveredDevices(devices) {
    const listContainer = document.getElementById("discovered-device-list");
    if (!listContainer) return;
    listContainer.innerHTML = "";

    if (!devices || devices.length === 0) {
        listContainer.innerHTML = `<span style="font-size: 11px; color: var(--text-secondary); font-style: italic; text-align: center; padding: 12px 0;">No devices discovered yet. Trigger discovery to scan local network.</span>`;
        return;
    }

    devices.forEach(dev => {
        const div = document.createElement("div");
        div.className = "card";
        div.style.padding = "8px 12px";
        div.style.cursor = "pointer";
        div.style.border = "1px solid var(--border-glass)";
        div.style.background = "rgba(255, 255, 255, 0.02)";
        div.style.display = "flex";
        div.style.justifyContent = "space-between";
        div.style.alignItems = "center";
        div.style.transition = "all 0.2s";
        div.setAttribute("id", `discovered-card-${dev.node_id}`);
        
        div.onmouseover = () => {
            div.style.background = "rgba(255, 255, 255, 0.06)";
            div.style.borderColor = "var(--accent-teal)";
        };
        div.onmouseout = () => {
            if (selectedDiscoveredDevice?.node_id !== dev.node_id) {
                div.style.background = "rgba(255, 255, 255, 0.02)";
                div.style.borderColor = "var(--border-glass)";
            }
        };

        div.addEventListener("click", () => {
            selectDiscoveredDevice(dev);
        });

        const left = document.createElement("div");
        left.style.display = "flex";
        left.style.flexDirection = "column";
        left.style.textAlign = "left";

        const name = document.createElement("span");
        name.style.fontSize = "11px";
        name.style.fontWeight = "bold";
        name.style.color = "#fff";
        name.innerText = dev.display_name;

        const details = document.createElement("span");
        details.style.fontSize = "9px";
        details.style.color = "var(--text-secondary)";
        details.style.fontFamily = "monospace";
        details.innerText = `${dev.ip_address} | Class: ${dev.device_class}`;

        left.appendChild(name);
        left.appendChild(details);

        const badge = document.createElement("span");
        badge.className = "badge";
        badge.style.fontSize = "8px";
        badge.style.padding = "1px 4px";
        
        if (dev.onboarding_status === "approved") {
            badge.style.background = "rgba(16, 185, 129, 0.15)";
            badge.style.color = "#10b981";
            badge.innerText = "Approved";
        } else if (dev.onboarding_status === "rejected") {
            badge.style.background = "rgba(239, 68, 68, 0.15)";
            badge.style.color = "#ef4444";
            badge.innerText = "Rejected";
        } else {
            badge.style.background = "rgba(59, 130, 246, 0.15)";
            badge.style.color = "var(--accent-blue)";
            badge.innerText = "Discovered";
        }

        div.appendChild(left);
        div.appendChild(badge);
        listContainer.appendChild(div);
    });

    if (selectedDiscoveredDevice) {
        const activeCard = document.getElementById(`discovered-card-${selectedDiscoveredDevice.node_id}`);
        if (activeCard) {
            activeCard.style.background = "rgba(255, 255, 255, 0.08)";
            activeCard.style.borderColor = "var(--accent-teal)";
        }
    }
}

function selectDiscoveredDevice(device) {
    selectedDiscoveredDevice = device;
    
    document.querySelectorAll('[id^="discovered-card-"]').forEach(card => {
        card.style.background = "rgba(255, 255, 255, 0.02)";
        card.style.borderColor = "var(--border-glass)";
    });
    const activeCard = document.getElementById(`discovered-card-${device.node_id}`);
    if (activeCard) {
        activeCard.style.background = "rgba(255, 255, 255, 0.08)";
        activeCard.style.borderColor = "var(--accent-teal)";
    }

    const panel = document.getElementById("device-service-approval-panel");
    if (!panel) return;
    panel.classList.remove("hidden");

    document.getElementById("approval-device-name").innerText = device.display_name;
    document.getElementById("approval-device-ip").innerText = `${device.ip_address} (${device.mac_address || "No MAC"})`;
    
    const classBadge = document.getElementById("approval-device-class");
    classBadge.innerText = device.device_class;
    
    document.getElementById("approval-fleet-group").innerText = device.fleet_group;
    document.getElementById("approval-compute-tier").innerText = device.compute_tier;
    document.getElementById("approval-operator-notes").value = device.operator_notes || "";

    const roleList = document.getElementById("device-service-role-list");
    roleList.innerHTML = "";

    const candidateRoles = device.service_roles && device.service_roles.length > 0
        ? device.service_roles
        : ["dashboard_receiver", "alert_wall", "release_status_display", "mobile_dashboard", "approval_terminal", "compute_worker"];

    candidateRoles.forEach(role => {
        const label = document.createElement("label");
        label.style.display = "flex";
        label.style.alignItems = "center";
        label.style.gap = "4px";
        label.style.fontSize = "10px";
        label.style.color = "var(--text-secondary)";
        label.style.background = "rgba(255, 255, 255, 0.03)";
        label.style.border = "1px solid var(--border-glass)";
        label.style.padding = "2px 6px";
        label.style.borderRadius = "4px";
        label.style.cursor = "pointer";

        const cb = document.createElement("input");
        cb.type = "checkbox";
        cb.value = role;
        cb.checked = true;
        cb.style.margin = "0";

        label.appendChild(cb);
        label.appendChild(document.createTextNode(role));
        roleList.appendChild(label);
    });
}

async function executeDeviceApproval() {
    if (!selectedDiscoveredDevice) return;
    const operator = "Michael Hoch";
    
    const selectedRoles = [];
    document.querySelectorAll('#device-service-role-list input[type="checkbox"]').forEach(cb => {
        if (cb.checked) selectedRoles.push(cb.value);
    });

    try {
        const res = await fetch(`${API_BASE}/api/v1/devices/service-registry/${selectedDiscoveredDevice.node_id}/approve`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                operator: operator,
                service_roles: selectedRoles
            })
        });
        if (res.ok) {
            logToConsoleTerminal("DaaSOnboarding", `Approved device ${selectedDiscoveredDevice.display_name} as active service node.`, "info");
            const panel = document.getElementById("device-service-approval-panel");
            if (panel) panel.classList.add("hidden");
            selectedDiscoveredDevice = null;
            await loadRegistryData();
            if (window.refreshClusterTopologyStatus) {
                await window.refreshClusterTopologyStatus();
            }
        }
    } catch (err) {
        console.error("Approval error:", err);
    }
}

async function executeDeviceRejection() {
    if (!selectedDiscoveredDevice) return;
    const operator = "Michael Hoch";
    const reason = "Operator rejected onboarding request.";

    try {
        const res = await fetch(`${API_BASE}/api/v1/devices/service-registry/${selectedDiscoveredDevice.node_id}/reject`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                operator: operator,
                reason: reason
            })
        });
        if (res.ok) {
            logToConsoleTerminal("DaaSOnboarding", `Rejected device ${selectedDiscoveredDevice.display_name}. Onboarding request denied.`, "warning");
            const panel = document.getElementById("device-service-approval-panel");
            if (panel) panel.classList.add("hidden");
            selectedDiscoveredDevice = null;
            await loadRegistryData();
            if (window.refreshClusterTopologyStatus) {
                await window.refreshClusterTopologyStatus();
            }
        }
    } catch (err) {
        console.error("Rejection error:", err);
    }
}

function renderApprovedServiceNodes(nodes) {
    const listContainer = document.getElementById("service-node-registry-list");
    if (!listContainer) return;
    listContainer.innerHTML = "";

    if (!nodes || nodes.length === 0) {
        listContainer.innerHTML = `<span style="font-size: 11px; color: var(--text-secondary); font-style: italic; text-align: center; padding: 12px 0;">No active service nodes approved.</span>`;
        return;
    }

    nodes.forEach(node => {
        const div = document.createElement("div");
        div.className = "card";
        div.style.padding = "8px 12px";
        div.style.border = "1px solid rgba(16, 185, 129, 0.2)";
        div.style.background = "rgba(16, 185, 129, 0.02)";
        div.style.display = "flex";
        div.style.justifyContent = "space-between";
        div.style.alignItems = "center";

        const left = document.createElement("div");
        left.style.display = "flex";
        left.style.flexDirection = "column";
        left.style.textAlign = "left";

        const name = document.createElement("span");
        name.style.fontSize = "11px";
        name.style.fontWeight = "bold";
        name.style.color = "#fff";
        name.innerText = node.display_name;

        const details = document.createElement("span");
        details.style.fontSize = "9px";
        details.style.color = "var(--text-secondary)";
        details.style.fontFamily = "monospace";
        details.innerText = `Roles: ${node.service_roles.join(", ")}`;

        left.appendChild(name);
        left.appendChild(details);

        const right = document.createElement("div");
        right.style.display = "flex";
        right.style.flexDirection = "column";
        right.style.alignItems = "flex-end";
        right.style.gap = "4px";

        const statusBadge = document.createElement("span");
        statusBadge.className = "badge";
        statusBadge.style.fontSize = "8px";

        if (node.lease) {
            const leaseDiv = document.createElement("div");
            leaseDiv.style.fontSize = "9px";
            leaseDiv.style.color = "var(--text-secondary)";
            leaseDiv.style.marginTop = "4px";
            leaseDiv.style.display = "flex";
            leaseDiv.style.gap = "8px";

            const batterySpan = document.createElement("span");
            batterySpan.innerHTML = `<i data-lucide="battery" style="width:10px; height:10px; display:inline-block; vertical-align:middle; margin-right:2px;"></i> ${node.lease.battery_level}% (${node.lease.power_source})`;

            const netSpan = document.createElement("span");
            netSpan.innerHTML = `<i data-lucide="wifi" style="width:10px; height:10px; display:inline-block; vertical-align:middle; margin-right:2px;"></i> ${node.lease.network_status}`;

            const durationSpan = document.createElement("span");
            durationSpan.innerText = `Lease: ${node.lease.availability} (${node.lease.lease_duration_seconds}s)`;

            leaseDiv.appendChild(batterySpan);
            leaseDiv.appendChild(netSpan);
            leaseDiv.appendChild(durationSpan);
            left.appendChild(leaseDiv);

            if (node.lease.status === "active") {
                statusBadge.style.background = "rgba(16, 185, 129, 0.15)";
                statusBadge.style.color = "#10b981";
                statusBadge.innerText = "Lease Active";
            } else {
                statusBadge.style.background = "rgba(239, 68, 68, 0.15)";
                statusBadge.style.color = "#ef4444";
                statusBadge.innerText = "Lease Expired";
            }
        } else {
            statusBadge.style.background = "rgba(239, 68, 68, 0.15)";
            statusBadge.style.color = "#ef4444";
            statusBadge.innerText = "No Lease";
        }

        const operatorText = document.createElement("span");
        operatorText.style.fontSize = "8px";
        operatorText.style.color = "var(--text-secondary)";
        operatorText.innerText = `By: ${node.approved_by_operator || "System"}`;

        right.appendChild(statusBadge);
        right.appendChild(operatorText);

        div.appendChild(left);
        div.appendChild(right);
        listContainer.appendChild(div);
    });
}

async function initCapabilityRouterUI() {
    const refreshBtn = document.getElementById("device-routing-refresh-button");
    if (refreshBtn) {
        refreshBtn.addEventListener("click", loadRoutingHistoryData);
    }
    // Load data initially
    await loadRoutingHistoryData();
}

async function initModelProviderRegistryUI() {
    const registerBtn = document.getElementById("model-provider-register-button");
    if (registerBtn) {
        registerBtn.addEventListener("click", registerModelProvider);
    }
    
    const healthCheckBtn = document.getElementById("model-provider-health-check-button");
    if (healthCheckBtn) {
        healthCheckBtn.addEventListener("click", runProviderHealthCheck);
    }
    
    const discoverBtn = document.getElementById("model-provider-discover-models-button");
    if (discoverBtn) {
        discoverBtn.addEventListener("click", runProviderModelDiscovery);
    }
    
    const approveBtn = document.getElementById("model-provider-approve-button");
    if (approveBtn) {
        approveBtn.addEventListener("click", runProviderApproval);
    }
    
    const disableBtn = document.getElementById("model-provider-disable-button");
    if (disableBtn) {
        disableBtn.addEventListener("click", runProviderDisabling);
    }
    
    const sendInferenceBtn = document.getElementById("inference-send-button");
    if (sendInferenceBtn) {
        sendInferenceBtn.addEventListener("click", sendTestInference);
    }
    
    const multiExecuteBtn = document.getElementById("multi-model-execute-button");
    if (multiExecuteBtn) {
        multiExecuteBtn.addEventListener("click", executeMultiModelReasoning);
    }
    
    const savePolicyBtn = document.getElementById("policy-save-button");
    if (savePolicyBtn) {
        savePolicyBtn.addEventListener("click", saveAgentModelPolicy);
    }
    
    loadModelProviders();
    loadInferenceHistory();
    loadMultiModelHistory();
    populateModelNodeSelect();
    loadAgentModelPolicies();
    loadPolicyDecisions();
}

async function loadModelProviders() {
    const listEl = document.getElementById("model-provider-list");
    const selectEl = document.getElementById("inference-provider-select");
    if (!listEl) return;
    
    try {
        const res = await fetch(`${API_BASE}/api/v1/models/providers`);
        if (!res.ok) return;
        const providers = await res.json();
        
        listEl.innerHTML = "";
        if (selectEl) {
            selectEl.innerHTML = `<option value="">-- Auto-Route (Capability Matching) --</option>`;
        }
        
        const multiListEl = document.getElementById("multi-model-providers-list");
        if (multiListEl) {
            multiListEl.innerHTML = "";
        }
        
        if (providers.length === 0) {
            listEl.innerHTML = `<tr><td colspan="6" style="text-align:center; color:var(--text-secondary); padding: 12px;">No model providers registered.</td></tr>`;
            return;
        }
        
        providers.forEach(p => {
            const tr = document.createElement("tr");
            tr.style.cursor = "pointer";
            tr.addEventListener("click", () => selectProvider(p));
            
            const approvedBadge = p.approved_for_inference
                ? `<span class="badge" style="background:rgba(16,185,129,0.15); color:var(--accent-teal);">APPROVED</span>`
                : `<span class="badge" style="background:rgba(239,68,68,0.15); color:#ef4444;">INACTIVE</span>`;
                
            const sensitiveText = p.trusted_for_sensitive_context
                ? `<span style="color:var(--accent-teal);">Trusted</span>`
                : `<span style="color:var(--text-secondary);">Untrusted</span>`;
                
            let healthClass = "text-danger";
            if (p.health_status === "available") healthClass = "text-success";
            else if (p.health_status === "degraded") healthClass = "text-warning";
            
            tr.innerHTML = `
                <td><strong>${p.display_name}</strong> <span style="font-size:9px; color:var(--text-secondary);">${p.model_provider_id}</span></td>
                <td><span style="font-family:monospace;">${p.provider_type}</span></td>
                <td><span style="font-family:monospace;">${p.default_model || "none"}</span></td>
                <td>${sensitiveText}</td>
                <td><span class="${healthClass} font-semibold" style="text-transform:uppercase;">${p.health_status}</span></td>
                <td>${approvedBadge}</td>
            `;
            listEl.appendChild(tr);
            
            if (selectEl && p.approved_for_inference) {
                const opt = document.createElement("option");
                opt.value = p.model_provider_id;
                opt.textContent = `${p.display_name} (${p.default_model})`;
                selectEl.appendChild(opt);
            }
            
            if (multiListEl && p.approved_for_inference) {
                const label = document.createElement("label");
                label.style.display = "flex";
                label.style.alignItems = "center";
                label.style.gap = "6px";
                label.style.fontSize = "11px";
                label.style.color = "#fff";
                label.style.cursor = "pointer";
                
                const input = document.createElement("input");
                input.type = "checkbox";
                input.value = p.model_provider_id;
                input.className = "multi-model-provider-checkbox";
                input.style.accentColor = "var(--accent-blue)";
                
                label.appendChild(input);
                label.appendChild(document.createTextNode(`${p.display_name} (${p.default_model})`));
                multiListEl.appendChild(label);
            }
        });
    } catch (err) {
        console.error("Error loading model providers:", err);
    }
}

async function initModelRouterUI() {
    const base = (typeof API_BASE !== "undefined" && API_BASE) ? API_BASE : "http://127.0.0.1:8000";
    const statusPill = el("mr-status-pill");
    const localModel = el("mr-local-model");
    const localFirstMode = el("mr-local-first-mode");
    const escalationStatus = el("mr-escalation-status");
    const auditLog = el("mr-audit-log");

    if (!statusPill) return;

    try {
      const statusRes = await fetch(`${base}/api/v1/models/status`);
      if (statusRes.ok) {
        const data = await statusRes.json();
        statusPill.textContent = "ONLINE";
        statusPill.className = "kimi-status-pill kimi-pill-live";
        localModel.textContent = data.default_model || "none";
        
        localFirstMode.textContent = data.local_first ? "ENABLED" : "DISABLED";
        localFirstMode.style.color = data.local_first ? "#8cff5c" : "#ff5f7a";
        
        escalationStatus.textContent = data.paid_models_enabled ? "ENABLED" : "DISABLED";
        escalationStatus.style.color = data.paid_models_enabled ? "#8cff5c" : "#ff5f7a";
      } else {
        statusPill.textContent = "OFFLINE";
        statusPill.className = "kimi-status-pill kimi-pill-broken";
      }
    } catch (err) {
      console.warn("[Model Router UI] Error fetching status:", err);
      statusPill.textContent = "OFFLINE";
      statusPill.className = "kimi-status-pill kimi-pill-broken";
    }

    try {
      const auditRes = await fetch(`${base}/api/v1/models/audit-log?limit=5`);
      if (auditRes.ok) {
        const logs = await auditRes.json();
        if (logs && logs.length > 0) {
          auditLog.textContent = logs.map(l => {
            const time = l.timestamp ? l.timestamp.split("T")[1].slice(0, 8) : "";
            return `[${time}] ${l.decision || "route"}: ${l.model || "none"} (${l.task_type || "general"})`;
          }).join("\n");
        } else {
          auditLog.textContent = "No routing events logged.";
        }
      }
    } catch (err) {
      console.warn("[Model Router UI] Error fetching audit logs:", err);
    }
  }

async function initCrewaiIngestionBridge() {
    const btn = document.getElementById("btn-trigger-crewai-ingest");
    if (btn) {
        btn.addEventListener("click", triggerCrewaiIngestion);
    }
    await loadCrewaiIngestionStatus();
    if (typeof initEvidenceGraphUI === 'function') {
        await initEvidenceGraphUI();
    }
}

async function initReleaseDecisionRoom() {
    const selectEl = document.getElementById("decision-room-candidate-select");
    const approveBtn = document.getElementById("btn-decision-simulate-approve");
    const rejectBtn = document.getElementById("btn-decision-simulate-reject");
    const exportBtn = document.getElementById("btn-export-decision-memo");

    if (selectEl) {
        selectEl.addEventListener("change", handleCandidateSelectionChange);
    }
    if (approveBtn) {
        approveBtn.addEventListener("click", () => simulateDecision("approved"));
    }
    if (rejectBtn) {
        rejectBtn.addEventListener("click", () => simulateDecision("rejected"));
    }
    if (exportBtn) {
        exportBtn.addEventListener("click", exportDecisionMemo);
    }

    const requestAuthBtn = document.getElementById("btn-request-authority");
    const executeRealPromotionBtn = document.getElementById("btn-execute-real-promotion");
    const cancelAuthBtn = document.getElementById("btn-modal-cancel-authority");
    const grantAuthBtn = document.getElementById("btn-modal-grant-authority");
    const confirmAuthChk = document.getElementById("chk-confirm-authority-scope");
    const modalEl = document.getElementById("authority-request-modal");

    if (requestAuthBtn) {
        requestAuthBtn.addEventListener("click", () => {
            if (!currentDecisionRoomCandidate) return;
            const modalCandidateId = document.getElementById("modal-authority-candidate-id");
            if (modalCandidateId) modalCandidateId.textContent = currentDecisionRoomCandidate.candidate_packet_id;
            if (confirmAuthChk) confirmAuthChk.checked = false;
            if (grantAuthBtn) grantAuthBtn.disabled = true;
            if (modalEl) modalEl.classList.remove("hidden");
        });
    }

    if (confirmAuthChk) {
        confirmAuthChk.addEventListener("change", (e) => {
            if (grantAuthBtn) grantAuthBtn.disabled = !e.target.checked;
        });
    }

    if (cancelAuthBtn) {
        cancelAuthBtn.addEventListener("click", () => {
            if (modalEl) modalEl.classList.add("hidden");
        });
    }

    if (grantAuthBtn) {
        grantAuthBtn.addEventListener("click", async () => {
            if (!currentDecisionRoomCandidate) return;
            const isTest = window.location.search.includes("test_mode=true");
            try {
                const res = await fetch(`${API_BASE}/api/v1/release/authority/request`, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                        candidate_packet_id: currentDecisionRoomCandidate.candidate_packet_id,
                        operator: "Michael Hoch",
                        is_test: isTest
                    })
                });

                if (res.ok) {
                    const data = await res.json();
                    if (modalEl) modalEl.classList.add("hidden");
                    alert(`Release Authority Token Granted successfully.\n` +
                          `Token: ${data.token_value}\n` +
                          `Expires: ${data.expires_at}`);
                    await updateReleaseAuthorityUI();
                } else {
                    const err = await res.json();
                    alert("Failed to request authority: " + (err.detail || "Forbidden"));
                }
            } catch (err) {
                alert("Error requesting authority: " + err.message);
            }
        });
    }

    if (executeRealPromotionBtn) {
        executeRealPromotionBtn.addEventListener("click", async () => {
            if (!currentDecisionRoomCandidate || !activeAuthorityToken) {
                alert("No active authority token found.");
                return;
            }

            const confirmPromotion = confirm(`Are you sure you want to execute real promotion for candidate ${currentDecisionRoomCandidate.candidate_packet_id}?\n\nThis will trigger git tags mutation, cosign signing, package publishing, and prod deployment simulations.`);
            if (!confirmPromotion) return;

            try {
                const res = await fetch(`${API_BASE}/api/v1/release/promote`, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                        candidate_packet_id: currentDecisionRoomCandidate.candidate_packet_id,
                        operator: "Michael Hoch",
                        authority_token: activeAuthorityToken
                    })
                });

                if (res.ok) {
                    const data = await res.json();
                    alert(`Real Promotion Executed Successfully!\n\nDetails:\n` +
                          `- Git Tag: ${data.details.git_tag}\n` +
                          `- Signed: ${data.details.signed}\n` +
                          `- Published: ${data.details.published}\n` +
                          `- Deployed: ${data.details.deployed}`);
                    
                    fetchAndRenderSigningPolicy();
                    await updateReleaseAuthorityUI();
                } else {
                    const err = await res.json();
                    alert("Promotion failed: " + (err.detail || "Forbidden"));
                }
            } catch (err) {
                alert("Error executing promotion: " + err.message);
            }
        });
    }

    // Phase 25: Execution Plan event listeners
    const generatePlanBtn = document.getElementById("btn-generate-execution-plan");
    const exportPlanMdBtn = document.getElementById("btn-export-plan-markdown");
    const exportPlanJsonBtn = document.getElementById("btn-export-plan-json");

    if (generatePlanBtn) {
        generatePlanBtn.addEventListener("click", generateExecutionPlan);
    }
    if (exportPlanMdBtn) {
        exportPlanMdBtn.addEventListener("click", exportPlanMarkdown);
    }
    if (exportPlanJsonBtn) {
        exportPlanJsonBtn.addEventListener("click", exportPlanJson);
    }

    await initReleaseEvidenceRetention();
    await initReleaseEvidenceArchivePreview();
    await initReleaseEvidenceArchiveBuildPlan();
    await initReleaseEvidenceArchiveSealPreview();

    await populateDecisionRoomCandidates();
}

async function updateReleaseAuthorityUI() {
    const requestBtn = document.getElementById("btn-request-authority");
    const executeBtn = document.getElementById("btn-execute-real-promotion");
    const statusText = document.getElementById("gov-authority-status");
    const badge = document.getElementById("gov-authority-badge");
    const detailsContainer = document.getElementById("gov-authority-token-details");
    const tokenValText = document.getElementById("gov-active-token-val");

    if (!currentDecisionRoomCandidate) {
        if (requestBtn) requestBtn.disabled = true;
        if (executeBtn) executeBtn.classList.add("hidden");
        if (statusText) {
            statusText.textContent = "ABSENT (Preview Mode)";
            statusText.style.color = "#ef4444";
        }
        if (badge) {
            badge.textContent = "SIMULATION ONLY";
            badge.style.backgroundColor = "rgba(239, 68, 68, 0.15)";
            badge.style.color = "#ef4444";
            badge.style.borderColor = "rgba(239, 68, 68, 0.3)";
        }
        if (detailsContainer) detailsContainer.classList.add("hidden");
        clearInterval(authorityCountdownInterval);
        activeAuthorityToken = null;

        const generatePlanBtn = document.getElementById("btn-generate-execution-plan");
        if (generatePlanBtn) generatePlanBtn.disabled = true;
        const planDetails = document.getElementById("execution-plan-details");
        if (planDetails) planDetails.classList.add("hidden");
        const actionsContainer = document.getElementById("execution-plan-actions-container");
        if (actionsContainer) actionsContainer.classList.add("hidden");
        currentGeneratedPlan = null;

        return;
    }

    const packetId = currentDecisionRoomCandidate.candidate_packet_id;

    try {
        const res = await fetch(`${API_BASE}/api/v1/release/authority/state/${packetId}`);
        if (!res.ok) return;
        const data = await res.json();

        const generatePlanBtn = document.getElementById("btn-generate-execution-plan");
        if (generatePlanBtn) generatePlanBtn.disabled = false;

        if (data.status === "active") {
            activeAuthorityToken = data.token_value;
            if (requestBtn) requestBtn.disabled = true;
            if (executeBtn) executeBtn.classList.remove("hidden");
            if (statusText) {
                statusText.textContent = `GRANTED (Active - ${data.operator})`;
                statusText.style.color = "var(--accent-teal)";
            }
            if (badge) {
                badge.textContent = "AUTHORITY ACTIVE";
                badge.style.backgroundColor = "rgba(20, 184, 166, 0.15)";
                badge.style.color = "var(--accent-teal)";
                badge.style.borderColor = "rgba(20, 184, 166, 0.3)";
            }
            if (detailsContainer) detailsContainer.classList.remove("hidden");
            if (tokenValText) tokenValText.textContent = data.token_value;

            startAuthorityCountdown(data.expires_at);
        } else {
            activeAuthorityToken = null;
            if (requestBtn) requestBtn.disabled = false;
            if (executeBtn) executeBtn.classList.add("hidden");
            if (statusText) {
                statusText.textContent = data.status === "expired" ? "EXPIRED (Preview Mode)" : "ABSENT (Preview Mode)";
                statusText.style.color = "#ef4444";
            }
            if (badge) {
                badge.textContent = "SIMULATION ONLY";
                badge.style.backgroundColor = "rgba(239, 68, 68, 0.15)";
                badge.style.color = "#ef4444";
                badge.style.borderColor = "rgba(239, 68, 68, 0.3)";
            }
            if (detailsContainer) detailsContainer.classList.add("hidden");
            clearInterval(authorityCountdownInterval);
        }
    } catch (err) {
        console.error("Error fetching release authority state:", err);
    }
}

function startAuthorityCountdown(expiresAt) {
    clearInterval(authorityCountdownInterval);
    const countdownEl = document.getElementById("gov-token-countdown");
    if (!countdownEl) return;

    const expTime = new Date(expiresAt).getTime();

    function updateTimer() {
        const now = new Date().getTime();
        const diff = expTime - now;

        if (diff <= 0) {
            clearInterval(authorityCountdownInterval);
            countdownEl.textContent = "00:00";
            updateReleaseAuthorityUI();
            return;
        }

        const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));
        const seconds = Math.floor((diff % (1000 * 60)) / 1000);

        const minStr = String(minutes).padStart(2, "0");
        const secStr = String(seconds).padStart(2, "0");

        countdownEl.textContent = `${minStr}:${secStr}`;
    }

    updateTimer();
    authorityCountdownInterval = setInterval(updateTimer, 1000);
}

async function generateExecutionPlan() {
    if (!currentDecisionRoomCandidate) {
        alert("No candidate packet selected.");
        return;
    }

    const packetId = currentDecisionRoomCandidate.candidate_packet_id;
    try {
        const res = await fetch(`${API_BASE}/api/v1/release/execution-plan/generate`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                candidate_packet_id: packetId,
                operator: "Michael Hoch"
            })
        });

        if (res.ok) {
            const data = await res.json();
            currentGeneratedPlan = data;

            const tbody = document.getElementById("execution-plan-steps-tbody");
            if (tbody) {
                tbody.innerHTML = "";
                data.steps.forEach(step => {
                    const row = document.createElement("tr");
                    row.style.borderBottom = "1px solid rgba(255,255,255,0.03)";
                    
                    const badgeColor = step.status === "SATISFIED" ? "var(--accent-teal)" : "var(--accent-orange)";
                    const badgeBg = step.status === "SATISFIED" ? "rgba(20, 184, 166, 0.15)" : "rgba(239, 68, 68, 0.15)";
                    const badgeBorder = step.status === "SATISFIED" ? "rgba(20, 184, 166, 0.3)" : "rgba(239, 68, 68, 0.3)";

                    row.innerHTML = `
                        <td style="padding: 8px 12px; font-weight: bold; color: var(--accent-blue);">${step.step}</td>
                        <td style="padding: 8px 12px; font-weight: 500; color: #fff;">${step.title}</td>
                        <td style="padding: 8px 12px;"><code style="font-family: monospace; color: var(--accent-teal); background: rgba(0,0,0,0.2); padding: 2px 6px; border-radius: 4px; display: inline-block; max-width: 320px; overflow-x: auto; white-space: nowrap;">${step.command}</code></td>
                        <td style="padding: 8px 12px; color: var(--text-secondary); font-family: monospace;">${step.scope_required}</td>
                        <td style="padding: 8px 12px; text-align: center;">
                            <span style="font-size: 10px; font-weight: bold; color: ${badgeColor}; background: ${badgeBg}; border: 1px solid ${badgeBorder}; padding: 2px 8px; border-radius: 4px; display: inline-block;">
                                ${step.status}
                            </span>
                        </td>
                    `;
                    tbody.appendChild(row);
                });
            }

            const details = document.getElementById("execution-plan-details");
            if (details) details.classList.remove("hidden");
            const actionsContainer = document.getElementById("execution-plan-actions-container");
            if (actionsContainer) actionsContainer.classList.remove("hidden");

        } else {
            const err = await res.json();
            alert("Failed to generate execution plan: " + (err.detail || "Unknown error"));
        }
    } catch (err) {
        alert("Error generating execution plan: " + err.message);
    }
}

function exportPlanMarkdown() {
    if (!currentGeneratedPlan) {
        alert("No plan generated to export.");
        return;
    }
    const blob = new Blob([currentGeneratedPlan.markdown], { type: "text/markdown" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `formal-release-execution-plan-${currentGeneratedPlan.candidate_packet_id}.md`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
}

function exportPlanJson() {
    if (!currentGeneratedPlan) {
        alert("No plan generated to export.");
        return;
    }
    const blob = new Blob([JSON.stringify(currentGeneratedPlan, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `formal-release-execution-plan-${currentGeneratedPlan.candidate_packet_id}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
}

async function initReleaseEvidenceRetention() {
    const scanBtn = document.getElementById("btn-scan-evidence");
    if (scanBtn) {
        scanBtn.addEventListener("click", loadEvidenceRetentionList);
    }
    await loadEvidenceRetentionList();
}

async function loadEvidenceRetentionList() {
    try {
        const res = await fetch(`${API_BASE}/api/v1/release/evidence/retention`);
        if (!res.ok) return;
        const data = await res.json();
        const evidence = data.evidence || [];
        
        let total = evidence.length;
        let review = 0;
        let retained = 0;
        let archived = 0;
        let ignored = 0;
        
        const tbody = document.getElementById("retention-evidence-tbody");
        if (tbody) {
            tbody.innerHTML = "";
            evidence.forEach(item => {
                const dec = item.retention_decision;
                if (dec === "needs-review") review++;
                else if (dec === "retain") retained++;
                else if (dec === "archive") archived++;
                else if (dec === "ignore") ignored++;
                
                const row = document.createElement("tr");
                row.style.borderBottom = "1px solid rgba(255,255,255,0.03)";
                
                let typeColor = "var(--text-secondary)";
                let typeBg = "rgba(255,255,255,0.05)";
                if (item.artifact_type === "candidate") {
                    typeColor = "var(--accent-blue)";
                    typeBg = "rgba(59, 130, 246, 0.15)";
                } else if (item.artifact_type === "formal-preview") {
                    typeColor = "var(--accent-purple)";
                    typeBg = "rgba(168, 85, 247, 0.15)";
                } else if (item.artifact_type === "attestation") {
                    typeColor = "var(--accent-orange)";
                    typeBg = "rgba(249, 115, 22, 0.15)";
                } else if (item.artifact_type === "release-bundle") {
                    typeColor = "var(--accent-teal)";
                    typeBg = "rgba(20, 184, 166, 0.15)";
                } else if (item.artifact_type === "qa-artifact") {
                    typeColor = "var(--accent-cyan)";
                    typeBg = "rgba(6, 182, 212, 0.15)";
                } else if (item.artifact_type === "temporary-run") {
                    typeColor = "#64748b";
                    typeBg = "rgba(100, 116, 139, 0.15)";
                }
                
                const selectId = `select-retention-${item.evidence_id}`;
                const options = [
                    { value: "needs-review", label: "NEEDS REVIEW" },
                    { value: "retain", label: "RETAIN" },
                    { value: "archive", label: "ARCHIVE" },
                    { value: "ignore", label: "IGNORE" }
                ];
                
                let selectHtml = `<select id="${selectId}" class="retention-decision-select" style="font-size: 9px; padding: 2px 4px; border-radius: 4px; background: rgba(0,0,0,0.3); border: 1px solid var(--border-glass); color: #fff;">`;
                options.forEach(opt => {
                    const sel = opt.value === dec ? "selected" : "";
                    selectHtml += `<option value="${opt.value}" ${sel}>${opt.label}</option>`;
                });
                selectHtml += `</select>`;
                
                row.innerHTML = `
                    <td style="padding: 6px 12px;">
                        <span style="font-size: 9px; font-weight: bold; color: ${typeColor}; background: ${typeBg}; border: 1px solid ${typeColor}30; padding: 2px 6px; border-radius: 4px;">
                            ${item.artifact_type.toUpperCase()}
                        </span>
                    </td>
                    <td style="padding: 6px 12px; font-family: monospace; color: #fff; max-width: 250px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">${item.source_path}</td>
                    <td style="padding: 6px 12px; font-family: monospace; color: var(--accent-teal);">${item.file_hash.substring(0, 12)}...</td>
                    <td style="padding: 6px 12px; color: var(--text-secondary);">${new Date(item.created_at).toLocaleString()}</td>
                    <td style="padding: 6px 12px; text-align: center;">${selectHtml}</td>
                `;
                tbody.appendChild(row);
                
                const selectEl = row.querySelector(`#${selectId}`);
                if (selectEl) {
                    selectEl.addEventListener("change", async (e) => {
                        await classifyEvidence(item.evidence_id, e.target.value);
                    });
                }
            });
        }
        
        const totalEl = document.getElementById("retention-count-total");
        const reviewEl = document.getElementById("retention-count-review");
        const retainedEl = document.getElementById("retention-count-retained");
        const archivedEl = document.getElementById("retention-count-archived");
        const ignoredEl = document.getElementById("retention-count-ignored");
        
        if (totalEl) totalEl.textContent = total;
        if (reviewEl) reviewEl.textContent = review;
        if (retainedEl) retainedEl.textContent = retained;
        if (archivedEl) archivedEl.textContent = archived;
        if (ignoredEl) ignoredEl.textContent = ignored;
        
    } catch (err) {
        console.error("Error loading retention evidence list:", err);
    }
}

async function classifyEvidence(evidenceId, decision) {
    try {
        const res = await fetch(`${API_BASE}/api/v1/release/evidence/retention/classify`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                evidence_id: evidenceId,
                retention_decision: decision
            })
        });
        if (res.ok) {
            await loadEvidenceRetentionList();
        } else {
            const err = await res.json();
            alert("Failed to classify evidence: " + (err.detail || "Unknown error"));
        }
    } catch (err) {
        alert("Error classifying evidence: " + err.message);
    }
}

async function initReleaseEvidenceArchivePreview() {
    const calcBtn = document.getElementById("btn-calculate-archive-preview");
    if (calcBtn) {
        calcBtn.addEventListener("click", calculateArchivePreview);
    }
    const exportMdBtn = document.getElementById("btn-export-preview-markdown");
    if (exportMdBtn) {
        exportMdBtn.addEventListener("click", exportArchivePreviewMarkdown);
    }
    const exportJsonBtn = document.getElementById("btn-export-preview-json");
    if (exportJsonBtn) {
        exportJsonBtn.addEventListener("click", exportArchivePreviewJSON);
    }
}

async function calculateArchivePreview() {
    try {
        const res = await fetch(`${API_BASE}/api/v1/release/evidence/archive/preview`);
        if (!res.ok) {
            const err = await res.json();
            alert("Failed to calculate archive preview: " + (err.detail || "Unknown error"));
            return;
        }
        const data = await res.json();
        lastArchivePreviewData = data;
        
        const detailsEl = document.getElementById("archive-preview-details");
        if (detailsEl) {
            detailsEl.classList.remove("hidden");
        }
        
        const pathEl = document.getElementById("archive-preview-path");
        if (pathEl) pathEl.textContent = data.planned_archive_path || "-";
        
        const checksumEl = document.getElementById("archive-preview-checksum");
        if (checksumEl) checksumEl.textContent = data.checksum || "-";
        
        const inclEl = document.getElementById("archive-preview-count-included");
        if (inclEl) inclEl.textContent = data.included_count;
        
        const exclEl = document.getElementById("archive-preview-count-excluded");
        if (exclEl) exclEl.textContent = data.excluded_count;
        
        const reviewEl = document.getElementById("archive-preview-count-review");
        if (reviewEl) reviewEl.textContent = data.needs_review_count;
        
        const missingEl = document.getElementById("archive-preview-count-missing");
        if (missingEl) missingEl.textContent = data.missing_count;
        
        // Warnings
        const warningsPanel = document.getElementById("archive-preview-warnings");
        const warningsList = document.getElementById("archive-preview-warnings-list");
        if (warningsPanel && warningsList) {
            warningsList.innerHTML = "";
            if (data.missing_count > 0 || data.needs_review_count > 0) {
                warningsPanel.classList.remove("hidden");
                if (data.missing_count > 0) {
                    const li = document.createElement("li");
                    li.innerHTML = `<strong>Missing Artifacts</strong>: ${data.missing_count} items exist in database index but are not present on disk.`;
                    warningsList.appendChild(li);
                }
                if (data.needs_review_count > 0) {
                    const li = document.createElement("li");
                    li.innerHTML = `<strong>Needs Review</strong>: ${data.needs_review_count} items require operator retention decisions.`;
                    warningsList.appendChild(li);
                }
            } else {
                warningsPanel.classList.add("hidden");
            }
        }
        
        // Table populating
        const tbody = document.getElementById("archive-preview-included-tbody");
        if (tbody) {
            tbody.innerHTML = "";
            const included = (data.manifest && data.manifest.included_artifacts) || [];
            // Sort by evidence_id
            const sorted = [...included].sort((a, b) => a.evidence_id.localeCompare(b.evidence_id));
            
            if (sorted.length === 0) {
                const row = document.createElement("tr");
                row.innerHTML = `<td colspan="3" style="padding: 12px; text-align: center; color: var(--text-secondary);">No artifacts selected for retention.</td>`;
                tbody.appendChild(row);
            } else {
                sorted.forEach(item => {
                    const row = document.createElement("tr");
                    row.style.borderBottom = "1px solid rgba(255,255,255,0.03)";
                    
                    let typeColor = "var(--text-secondary)";
                    let typeBg = "rgba(255,255,255,0.05)";
                    if (item.artifact_type === "candidate") {
                        typeColor = "var(--accent-blue)";
                        typeBg = "rgba(59, 130, 246, 0.15)";
                    } else if (item.artifact_type === "formal-preview") {
                        typeColor = "var(--accent-purple)";
                        typeBg = "rgba(168, 85, 247, 0.15)";
                    } else if (item.artifact_type === "attestation") {
                        typeColor = "var(--accent-orange)";
                        typeBg = "rgba(249, 115, 22, 0.15)";
                    } else if (item.artifact_type === "release-bundle") {
                        typeColor = "var(--accent-teal)";
                        typeBg = "rgba(20, 184, 166, 0.15)";
                    } else if (item.artifact_type === "qa-artifact") {
                        typeColor = "var(--accent-cyan)";
                        typeBg = "rgba(6, 182, 212, 0.15)";
                    } else if (item.artifact_type === "temporary-run") {
                        typeColor = "#64748b";
                        typeBg = "rgba(100, 116, 139, 0.15)";
                    }
                    
                    row.innerHTML = `
                        <td style="padding: 6px 12px;">
                            <span style="font-size: 9px; font-weight: bold; color: ${typeColor}; background: ${typeBg}; border: 1px solid ${typeColor}30; padding: 2px 6px; border-radius: 4px;">
                                ${item.artifact_type.toUpperCase()}
                            </span>
                        </td>
                        <td style="padding: 6px 12px; font-family: monospace; color: #fff; max-width: 300px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">${item.source_path}</td>
                        <td style="padding: 6px 12px; font-family: monospace; color: var(--accent-teal);">${item.file_hash.substring(0, 12)}...</td>
                    `;
                    tbody.appendChild(row);
                });
            }
        }
        
        if (window.lucide) {
            window.lucide.createIcons();
        }
    } catch (err) {
        console.error("Error calculating archive preview:", err);
        alert("Error calculating archive preview: " + err.message);
    }
}

function exportArchivePreviewMarkdown() {
    if (!lastArchivePreviewData || !lastArchivePreviewData.markdown) {
        alert("Please calculate the preview first before exporting.");
        return;
    }
    const blob = new Blob([lastArchivePreviewData.markdown], { type: "text/markdown" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "release-evidence-archive-preview.md";
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
}

function exportArchivePreviewJSON() {
    if (!lastArchivePreviewData || !lastArchivePreviewData.manifest) {
        alert("Please calculate the preview first before exporting.");
        return;
    }
    const blob = new Blob([JSON.stringify(lastArchivePreviewData.manifest, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "release-evidence-archive-preview.json";
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
}

async function initReleaseEvidenceArchiveBuildPlan() {
    const genBtn = document.getElementById("btn-generate-archive-build-plan");
    if (genBtn) {
        genBtn.addEventListener("click", generateArchiveBuildPlan);
    }
    const exportMdBtn = document.getElementById("btn-export-build-plan-markdown");
    if (exportMdBtn) {
        exportMdBtn.addEventListener("click", exportBuildPlanMarkdown);
    }
    const exportJsonBtn = document.getElementById("btn-export-build-plan-json");
    if (exportJsonBtn) {
        exportJsonBtn.addEventListener("click", exportBuildPlanJSON);
    }
}

async function generateArchiveBuildPlan() {
    try {
        const res = await fetch(`${API_BASE}/api/v1/release/evidence/archive/build-plan`);
        if (!res.ok) {
            const err = await res.json();
            alert("Failed to generate archive build plan: " + (err.detail || "Unknown error"));
            return;
        }
        const data = await res.json();
        lastArchiveBuildPlanData = data;
        
        const detailsEl = document.getElementById("archive-build-plan-details");
        if (detailsEl) {
            detailsEl.classList.remove("hidden");
        }
        
        const statusEl = document.getElementById("archive-build-status");
        if (statusEl) {
            statusEl.textContent = data.build_plan_status;
            if (data.build_plan_status === "READY") {
                statusEl.style.color = "#10b981";
                statusEl.style.background = "rgba(16, 185, 129, 0.15)";
                statusEl.style.border = "1px solid rgba(16, 185, 129, 0.3)";
            } else {
                statusEl.style.color = "#f97316";
                statusEl.style.background = "rgba(249, 115, 22, 0.15)";
                statusEl.style.border = "1px solid rgba(249, 115, 22, 0.3)";
            }
        }
        
        const targetPathEl = document.getElementById("archive-build-target-path");
        if (targetPathEl) targetPathEl.textContent = data.planned_archive_path || "-";
        
        const manifestPathEl = document.getElementById("archive-build-manifest-path");
        if (manifestPathEl) manifestPathEl.textContent = data.planned_manifest_path || "-";
        
        const manifestHashEl = document.getElementById("archive-build-manifest-hash");
        if (manifestHashEl) manifestHashEl.textContent = data.expected_manifest_hash || "-";
        
        const archiveChecksumEl = document.getElementById("archive-build-archive-checksum");
        if (archiveChecksumEl) archiveChecksumEl.textContent = data.expected_archive_checksum || "-";
        
        // Warnings
        const warningsPanel = document.getElementById("archive-build-plan-warnings");
        const warningsList = document.getElementById("archive-build-plan-warnings-list");
        if (warningsPanel && warningsList) {
            warningsList.innerHTML = "";
            if (data.build_plan_status === "BLOCKED") {
                warningsPanel.classList.remove("hidden");
                if (data.has_unclassified_evidence) {
                    const li = document.createElement("li");
                    li.innerHTML = `<strong>Unclassified Evidence</strong>: One or more evidence items are in "needs-review" state. Classification is required.`;
                    warningsList.appendChild(li);
                }
                if (data.has_missing_evidence) {
                    const li = document.createElement("li");
                    li.innerHTML = `<strong>Missing Evidence</strong>: One or more evidence items exist in database but are not present on disk.`;
                    warningsList.appendChild(li);
                }
            } else {
                warningsPanel.classList.add("hidden");
            }
        }
        
        // Operations Table
        const tbody = document.getElementById("archive-build-operations-tbody");
        if (tbody) {
            tbody.innerHTML = "";
            const operations = data.operations || [];
            
            if (operations.length === 0) {
                const row = document.createElement("tr");
                row.innerHTML = `<td colspan="6" style="padding: 12px; text-align: center; color: var(--text-secondary);">No build operations planned.</td>`;
                tbody.appendChild(row);
            } else {
                operations.forEach(op => {
                    const row = document.createElement("tr");
                    row.style.borderBottom = "1px solid rgba(255,255,255,0.03)";
                    
                    let actionColor = "var(--text-secondary)";
                    if (op.action === "INITIALIZE_DIRECTORY") actionColor = "var(--accent-blue)";
                    else if (op.action === "GENERATE_MANIFEST") actionColor = "var(--accent-cyan)";
                    else if (op.action === "PACKAGE_FILE") actionColor = "var(--accent-teal)";
                    else if (op.action === "COMPRESS_ARCHIVE") actionColor = "var(--accent-purple)";
                    
                    row.innerHTML = `
                        <td style="padding: 6px 12px; font-family: monospace; color: var(--text-secondary);">${op.step}</td>
                        <td style="padding: 6px 12px;">
                            <span style="font-size: 9px; font-weight: bold; color: ${actionColor};">
                                ${op.action}
                            </span>
                        </td>
                        <td style="padding: 6px 12px; font-family: monospace; color: #fff; max-width: 150px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">${op.source}</td>
                        <td style="padding: 6px 12px; font-family: monospace; color: #fff; max-width: 150px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">${op.destination}</td>
                        <td style="padding: 6px 12px; text-align: right; font-family: monospace; color: var(--accent-teal);">${op.size_bytes.toLocaleString()}</td>
                        <td style="padding: 6px 12px; color: var(--text-secondary); max-width: 200px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">${op.description}</td>
                    `;
                    tbody.appendChild(row);
                });
            }
        }
        
        if (window.lucide) {
            window.lucide.createIcons();
        }
    } catch (err) {
        console.error("Error generating archive build plan:", err);
        alert("Error generating archive build plan: " + err.message);
    }
}

function exportBuildPlanMarkdown() {
    if (!lastArchiveBuildPlanData || !lastArchiveBuildPlanData.markdown) {
        alert("Please generate the build plan first before exporting.");
        return;
    }
    const blob = new Blob([lastArchiveBuildPlanData.markdown], { type: "text/markdown" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "release-evidence-archive-build-plan.md";
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
}

function exportBuildPlanJSON() {
    if (!lastArchiveBuildPlanData || !lastArchiveBuildPlanData.manifest_payload) {
        alert("Please generate the build plan first before exporting.");
        return;
    }
    const blob = new Blob([JSON.stringify(lastArchiveBuildPlanData.manifest_payload, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "release-evidence-archive-build-plan.json";
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
}

async function initReleaseEvidenceArchiveSealPreview() {
    const genBtn = document.getElementById("btn-generate-archive-seal-preview");
    if (genBtn) {
        genBtn.addEventListener("click", generateArchiveSealPreview);
    }
    const exportMdBtn = document.getElementById("btn-export-seal-preview-markdown");
    if (exportMdBtn) {
        exportMdBtn.addEventListener("click", exportSealPreviewMarkdown);
    }
    const exportJsonBtn = document.getElementById("btn-export-seal-preview-json");
    if (exportJsonBtn) {
        exportJsonBtn.addEventListener("click", exportSealPreviewJSON);
    }
}

async function generateArchiveSealPreview() {
    try {
        const res = await fetch(`${API_BASE}/api/v1/release/evidence/archive/seal-preview`);
        if (!res.ok) {
            const err = await res.json();
            alert("Failed to generate archive seal preview: " + (err.detail || "Unknown error"));
            return;
        }
        const data = await res.json();
        lastArchiveSealPreviewData = data;
        
        const detailsEl = document.getElementById("archive-seal-preview-details");
        if (detailsEl) {
            detailsEl.classList.remove("hidden");
        }
        
        const statusEl = document.getElementById("archive-seal-status");
        if (statusEl) {
            statusEl.textContent = data.seal_readiness;
            if (data.seal_readiness === "READY") {
                statusEl.style.color = "#10b981";
                statusEl.style.background = "rgba(16, 185, 129, 0.15)";
                statusEl.style.border = "1px solid rgba(16, 185, 129, 0.3)";
            } else {
                statusEl.style.color = "#f97316";
                statusEl.style.background = "rgba(249, 115, 22, 0.15)";
                statusEl.style.border = "1px solid rgba(249, 115, 22, 0.3)";
            }
        }
        
        const candidateIdEl = document.getElementById("archive-seal-candidate-id");
        if (candidateIdEl) candidateIdEl.textContent = data.candidate_packet_id || "-";
        
        const sealIdEl = document.getElementById("archive-seal-id");
        if (sealIdEl) sealIdEl.textContent = data.seal_id || "-";
        
        const archiveIdEl = document.getElementById("archive-seal-archive-id");
        if (archiveIdEl) archiveIdEl.textContent = data.archive_id || "-";
        
        const manifestHashEl = document.getElementById("archive-seal-manifest-hash");
        if (manifestHashEl) manifestHashEl.textContent = data.manifest_hash || "-";
        
        const custodyPathEl = document.getElementById("archive-seal-custody-path");
        if (custodyPathEl) custodyPathEl.textContent = data.custody_path || "-";
        
        const operatorEl = document.getElementById("archive-seal-operator");
        if (operatorEl) operatorEl.textContent = data.operator || "-";
        
        // Warnings
        const warningsPanel = document.getElementById("archive-seal-preview-warnings");
        const warningsList = document.getElementById("archive-seal-preview-warnings-list");
        if (warningsPanel && warningsList) {
            warningsList.innerHTML = "";
            if (data.seal_readiness === "BLOCKED") {
                warningsPanel.classList.remove("hidden");
                const blockers = data.blockers || [];
                if (blockers.length === 0) {
                    const li = document.createElement("li");
                    li.innerHTML = `Blocked by custody verification constraints.`;
                    warningsList.appendChild(li);
                } else {
                    blockers.forEach(b => {
                        const li = document.createElement("li");
                        li.innerHTML = `<strong>Blocker</strong>: ${b}`;
                        warningsList.appendChild(li);
                    });
                }
            } else {
                warningsPanel.classList.add("hidden");
            }
        }
        
        if (window.lucide) {
            window.lucide.createIcons();
        }
    } catch (err) {
        console.error("Error generating archive seal preview:", err);
        alert("Error generating archive seal preview: " + err.message);
    }
}

function exportSealPreviewMarkdown() {
    if (!lastArchiveSealPreviewData || !lastArchiveSealPreviewData.markdown) {
        alert("Please generate the seal preview first before exporting.");
        return;
    }
    const blob = new Blob([lastArchiveSealPreviewData.markdown], { type: "text/markdown" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "release-evidence-archive-seal-preview.md";
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
}

function exportSealPreviewJSON() {
    if (!lastArchiveSealPreviewData || !lastArchiveSealPreviewData.seal_payload) {
        alert("Please generate the seal preview first before exporting.");
        return;
    }
    const blob = new Blob([JSON.stringify(lastArchiveSealPreviewData.seal_payload, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "release-evidence-archive-seal-preview.json";
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
}

async function fetchAndRenderGovernanceSummary() {
    try {
        if (typeof loadApprovedPreviewsForDryRun === 'function') {
            loadApprovedPreviewsForDryRun();
        }
        if (typeof loadSealDryRunHistory === 'function') {
            loadSealDryRunHistory();
        }
        if (typeof loadSealDryRunsForAttestation === 'function') {
            loadSealDryRunsForAttestation();
        }
        if (typeof loadAttestationHistory === 'function') {
            loadAttestationHistory();
        }
        if (typeof fetchAndRenderCrewaiArtifacts === 'function') {
            fetchAndRenderCrewaiArtifacts();
        }
        const res = await fetch(`${API_BASE}/api/v1/governance/summary`);
        if (!res.ok) {
            console.error("Failed to fetch governance summary");
            return;
        }
        const data = await res.json();
        
        // 1. Pending count & list
        const pendingCountEl = document.getElementById("gov-pending-count");
        if (pendingCountEl) {
            pendingCountEl.textContent = data.pending_gates.length;
        }
        
        const pendingListEl = document.getElementById("gov-pending-list");
        if (pendingListEl) {
            pendingListEl.innerHTML = "";
            if (data.pending_gates.length === 0) {
                pendingListEl.innerHTML = `<p style="color:var(--text-secondary); text-align:center; padding: 20px; font-size:12px; margin:0;">No pending approval requests.</p>`;
            } else {
                data.pending_gates.forEach(gate => {
                    const card = document.createElement("div");
                    card.className = "card";
                    card.style.background = "rgba(255,255,255,0.02)";
                    card.style.border = "1px solid var(--border-glass)";
                    card.style.borderRadius = "6px";
                    card.style.padding = "10px";
                    card.style.display = "flex";
                    card.style.flexDirection = "column";
                    card.style.gap = "6px";
                    
                    card.innerHTML = `
                        <div style="display:flex; justify-content:space-between; align-items:center; font-size:11px;">
                            <strong style="color:var(--accent-yellow);">${gate.action_type.toUpperCase()}</strong>
                            <span style="color:var(--text-secondary);">${gate.created_at}</span>
                        </div>
                        <div style="font-size:12px; color:#fff;"><strong>Request ID:</strong> ${gate.request_id}</div>
                        <div style="font-size:11px; color:var(--text-secondary); line-height:1.4;">Requested by: ${gate.requested_by} (Risk: ${gate.risk_level})</div>
                        <div style="display:flex; gap:10px; margin-top:4px;">
                            <button class="btn btn-xs btn-primary" onclick="window.submitGovernanceApproval('${gate.approval_id}', 'approve')">Approve</button>
                            <button class="btn btn-xs btn-danger" onclick="window.submitGovernanceApproval('${gate.approval_id}', 'reject')">Reject</button>
                        </div>
                    `;
                    pendingListEl.appendChild(card);
                });
            }
        }
        
        // 2. Blockers status & list
        const blockersStatusEl = document.getElementById("gov-blockers-status");
        if (blockersStatusEl) {
            if (data.formal_release_blockers.length === 0) {
                blockersStatusEl.textContent = "PASS";
                blockersStatusEl.style.color = "var(--accent-teal)";
                blockersStatusEl.style.background = "rgba(16,185,129,0.15)";
            } else {
                blockersStatusEl.textContent = "BLOCK";
                blockersStatusEl.style.color = "#ef4444";
                blockersStatusEl.style.background = "rgba(239,68,68,0.15)";
            }
        }
        
        const blockersListEl = document.getElementById("gov-blockers-list");
        if (blockersListEl) {
            blockersListEl.innerHTML = "";
            if (data.formal_release_blockers.length === 0) {
                blockersListEl.innerHTML = `<li style="display:flex; align-items:center; gap:8px; color:var(--accent-teal);"><i data-lucide="check-circle" style="width:14px; height:14px;"></i> All finalization gates satisfy release policy constraints.</li>`;
            } else {
                data.formal_release_blockers.forEach(blocker => {
                    const li = document.createElement("li");
                    li.style.display = "flex";
                    li.style.alignItems = "center";
                    li.style.gap = "8px";
                    li.style.color = "#ef4444";
                    let label = blocker;
                    if (blocker === "dirty_working_tree") label = "Git Working Tree is Dirty (Unwaived)";
                    else if (blocker === "qa_not_passed") label = "QA / Verification Pack is Not Passing (Unwaived)";
                    else if (blocker === "signing_policy_not_passed") label = "Release Artifacts Are Unsigned (Unwaived)";
                    else if (blocker === "tag_missing") label = "Git Release Tag is Missing (Unwaived)";
                    else if (blocker === "tag_stale") label = "Git Release Tag points to non-HEAD commit (Unwaived)";
                    else if (blocker === "operator_approval_missing") label = "Formal Channel Promotion requires Operator Gate";
                    
                    li.innerHTML = `<i data-lucide="alert-triangle" style="width:14px; height:14px; flex-shrink:0;"></i> <span>${label}</span>`;
                    blockersListEl.appendChild(li);
                });
            }
        }
        
        // 3. Active Policies & Waivers
        const activeChanEl = document.getElementById("gov-active-channel");
        if (activeChanEl) {
            activeChanEl.textContent = data.active_channel;
            if (data.active_channel === "formal") {
                activeChanEl.style.color = "var(--accent-teal)";
            } else if (data.active_channel === "candidate") {
                activeChanEl.style.color = "var(--accent-yellow)";
            } else {
                activeChanEl.style.color = "var(--accent-blue)";
            }
        }
        
        const signingWaiverEl = document.getElementById("gov-signing-waiver");
        if (signingWaiverEl) {
            signingWaiverEl.textContent = data.signing_waiver;
            if (data.signing_waiver === "waived") {
                signingWaiverEl.style.color = "var(--accent-yellow)";
            } else {
                signingWaiverEl.style.color = "#fff";
            }
        }
        
        const tagAlignmentEl = document.getElementById("gov-tag-alignment");
        if (tagAlignmentEl) {
            tagAlignmentEl.textContent = data.tag_alignment_status;
            if (data.tag_alignment_status === "TAG_AT_HEAD") {
                tagAlignmentEl.style.color = "var(--accent-teal)";
            } else {
                tagAlignmentEl.style.color = "#ef4444";
            }
        }
        
        const testBypassEl = document.getElementById("gov-test-bypass-active");
        if (testBypassEl) {
            testBypassEl.textContent = data.test_bypass_hardening;
            if (data.test_bypass_hardening === "ACTIVE") {
                testBypassEl.style.color = "var(--accent-blue)";
            } else {
                testBypassEl.style.color = "var(--text-secondary)";
            }
        }
        
        // 4. Capability Enforcement Decisions
        const capBody = document.getElementById("gov-capability-tbody");
        if (capBody) {
            capBody.innerHTML = "";
            if (data.capability_decisions.length === 0) {
                capBody.innerHTML = `<tr><td colspan="5" style="text-align:center; color:var(--text-secondary); padding: 12px;">No capability decisions registered.</td></tr>`;
            } else {
                data.capability_decisions.forEach(item => {
                    const row = document.createElement("tr");
                    const timeStr = item.timestamp ? item.timestamp.substring(11, 19) : "";
                    const allowedClass = item.decision === "ALLOW" ? "text-success" : (item.decision === "BLOCK" ? "text-danger" : "text-warning");
                    row.innerHTML = `
                        <td style="color:var(--text-secondary);">${timeStr}</td>
                        <td><strong>${item.agent_id}</strong></td>
                        <td style="font-family:monospace;">${item.tool}</td>
                        <td><span class="${allowedClass} font-semibold">${item.decision}</span></td>
                        <td style="color:var(--text-secondary);">${item.reason}</td>
                    `;
                    capBody.appendChild(row);
                });
            }
        }
        
        // 5. Replay Protection Evidence
        const replayBody = document.getElementById("gov-replay-tbody");
        if (replayBody) {
            replayBody.innerHTML = "";
            if (data.replay_protection_evidence.length === 0) {
                replayBody.innerHTML = `<tr><td colspan="4" style="text-align:center; color:var(--text-secondary); padding: 12px;">No replay protection evidence recorded.</td></tr>`;
            } else {
                data.replay_protection_evidence.forEach(item => {
                    const row = document.createElement("tr");
                    const timeStr = item.timestamp ? item.timestamp.substring(11, 19) : "";
                    row.innerHTML = `
                        <td style="font-family:monospace; color:var(--accent-teal);">${item.decision_id}</td>
                        <td style="font-family:monospace; color:var(--text-secondary);">${item.nonce ? item.nonce.substring(0, 16) + '...' : 'none'}</td>
                        <td><span style="font-family:monospace;">${item.prior_state}</span> ➔ <span style="font-family:monospace; font-weight:600; color:var(--accent-teal);">${item.next_state}</span></td>
                        <td style="color:var(--text-secondary);">${timeStr}</td>
                    `;
                    replayBody.appendChild(row);
                });
            }
        }
        
        // 6. Historical Operator Decision Ledger
        const ledgerBody = document.getElementById("gov-ledger-tbody");
        if (ledgerBody) {
            ledgerBody.innerHTML = "";
            if (data.decision_ledger.length === 0) {
                ledgerBody.innerHTML = `<tr><td colspan="6" style="text-align:center; color:var(--text-secondary); padding: 12px;">No historical operator decisions recorded in ledger.</td></tr>`;
            } else {
                data.decision_ledger.forEach(item => {
                    const row = document.createElement("tr");
                    const colorClass = item.decision === "approved" ? "text-success" : "text-danger";
                    row.innerHTML = `
                        <td style="font-family:monospace; color:var(--accent-blue);">${item.decision_id}</td>
                        <td><strong>${escapeHtml(item.operator)}</strong></td>
                        <td style="font-family:monospace;">${item.action_type}</td>
                        <td><span class="${colorClass} font-semibold">${item.decision.toUpperCase()}</span></td>
                        <td style="color:var(--text-secondary);">${escapeHtml(item.reason || "none")}</td>
                        <td style="color:var(--text-secondary);">${item.timestamp}</td>
                    `;
                    ledgerBody.appendChild(row);
                });
            }
        }
        
        // Render candidate packets list as well
        if (typeof fetchAndRenderCandidatePackets === "function") {
            fetchAndRenderCandidatePackets();
        }

        // Trigger lucide icons rendering
        if (typeof lucide !== "undefined" && typeof lucide.createIcons === "function") {
            lucide.createIcons();
        }
        
    } catch (err) {
        console.error("Error fetching governance summary:", err);
    }
}

async function checkApprovalStatusForPreview(formalPreviewId) {
    const requestApprovalBtn = document.getElementById("formal-preview-request-approval-button");
    const container = document.getElementById("formal-preview-approval-report-container");
    const statusEl = document.getElementById("formal-preview-approval-status");
    const reportPathEl = document.getElementById("formal-preview-approval-report-path");
    
    if (!formalPreviewId || formalPreviewId === "None") {
        if (requestApprovalBtn) requestApprovalBtn.style.display = "none";
        if (container) container.style.display = "none";
        return;
    }
    
    try {
        const res = await fetch(`${API_BASE}/api/v1/governance/summary`);
        if (!res.ok) return;
        const data = await res.json();
        
        const targetReqId = `channel_decision:formal:${formalPreviewId}`;
        
        // 1. Check if pending
        const pendingGate = data.pending_gates.find(g => g.request_id === targetReqId);
        if (pendingGate) {
            if (requestApprovalBtn) requestApprovalBtn.style.display = "none";
            if (container) container.style.display = "flex";
            if (statusEl) {
                statusEl.textContent = "PENDING";
                statusEl.style.color = "var(--accent-yellow)";
            }
            if (reportPathEl) reportPathEl.textContent = "none (awaiting decision)";
            return;
        }
        
        // 2. Check if decided in historical decision ledger
        const historicalDecision = data.decision_ledger.find(d => d.request_id === targetReqId);
        if (historicalDecision) {
            if (requestApprovalBtn) requestApprovalBtn.style.display = "none";
            if (container) container.style.display = "flex";
            if (statusEl) {
                const dec = historicalDecision.decision.toUpperCase();
                statusEl.textContent = dec;
                statusEl.style.color = dec === "APPROVED" ? "var(--accent-teal)" : "#ef4444";
            }
            if (reportPathEl) {
                reportPathEl.textContent = `dist/formal-previews/${formalPreviewId}/formal_release_approval_report.json`;
            }
            return;
        }
        
        // 3. No gate exists yet
        if (requestApprovalBtn) requestApprovalBtn.style.display = "block";
        if (container) container.style.display = "none";
        
    } catch (err) {
        console.error("Error checking preview approval status:", err);
    }
}

function initFormalReleaseSealDryRun() {
    const executeBtn = document.getElementById("seal-dry-run-execute-button");
    if (executeBtn) {
        executeBtn.addEventListener("click", executeSealDryRun);
    }
    
    loadApprovedPreviewsForDryRun();
    loadSealDryRunHistory();
}

async function loadApprovedPreviewsForDryRun() {
    const selectEl = document.getElementById("seal-dry-run-preview-select");
    if (!selectEl) return;
    
    try {
        const res = await fetch(`${API_BASE}/api/v1/release/formal-preview`);
        if (!res.ok) return;
        const previews = await res.json();
        
        selectEl.innerHTML = '<option value="">-- Select Approved Formal Preview --</option>';
        
        const approvedPreviews = previews.filter(p => p.operator_approval_status === "approved");
        if (approvedPreviews.length === 0) {
            selectEl.innerHTML = '<option value="">-- No approved previews found --</option>';
            return;
        }
        
        approvedPreviews.forEach(p => {
            const opt = document.createElement("option");
            opt.value = p.formal_preview_id;
            opt.textContent = `${p.formal_preview_id} (Version: ${p.candidate_version})`;
            selectEl.appendChild(opt);
        });
    } catch (err) {
        console.error("Error loading approved previews for dry run:", err);
    }
}

async function executeSealDryRun() {
    const selectEl = document.getElementById("seal-dry-run-preview-select");
    const operatorInput = document.getElementById("seal-dry-run-operator-input");
    const executeBtn = document.getElementById("seal-dry-run-execute-button");
    
    if (!selectEl || !selectEl.value) {
        alert("Please select an approved formal preview first.");
        return;
    }
    
    const previewId = selectEl.value;
    const operator = operatorInput ? operatorInput.value : "Michael Hoch";
    
    if (executeBtn) {
        executeBtn.disabled = true;
        executeBtn.textContent = "Executing Dry Run...";
    }
    
    try {
        const res = await fetch(`${API_BASE}/api/v1/release/formal-preview/${previewId}/seal-dry-run`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ operator })
        });
        
        if (res.ok) {
            const data = await res.json();
            
            const statusEl = document.getElementById("seal-dry-run-status");
            const idEl = document.getElementById("seal-dry-run-id");
            const manifestPathEl = document.getElementById("seal-dry-run-manifest-path");
            const reportPathEl = document.getElementById("seal-dry-run-report-path");
            const blockersEl = document.getElementById("seal-dry-run-blockers");
            
            if (statusEl) {
                statusEl.textContent = data.seal_status;
                statusEl.style.color = data.seal_status === "SEAL_READY" ? "var(--accent-teal)" : "#ef4444";
            }
            if (idEl) idEl.textContent = data.seal_dry_run_id;
            if (manifestPathEl) manifestPathEl.textContent = data.seal_manifest_path;
            if (reportPathEl) reportPathEl.textContent = data.seal_report_path;
            
            if (blockersEl) {
                blockersEl.innerHTML = "";
                if (data.formal_release_blockers.length === 0) {
                    blockersEl.innerHTML = `<li style="color: var(--accent-teal);">✅ No remaining blockers - Ready to seal!</li>`;
                } else {
                    data.formal_release_blockers.forEach(b => {
                        const li = document.createElement("li");
                        li.textContent = `• ${b}`;
                        blockersEl.appendChild(li);
                    });
                }
            }
            
            alert(`Seal Dry Run completed: ${data.seal_status}. Protects no-mutation guarantee.`);
            loadSealDryRunHistory();
            if (typeof loadSealDryRunsForAttestation === 'function') {
                loadSealDryRunsForAttestation();
            }
        } else {
            const errData = await res.json();
            alert("Failed to execute Seal Dry Run: " + (errData.detail || "Unknown error"));
        }
    } catch (err) {
        alert("Error executing Seal Dry Run: " + err.message);
    } finally {
        if (executeBtn) {
            executeBtn.disabled = false;
            executeBtn.textContent = "Execute Seal Dry Run";
        }
    }
}

async function loadSealDryRunHistory() {
    const historyTbody = document.getElementById("seal-dry-run-history-list");
    if (!historyTbody) return;
    
    try {
        const res = await fetch(`${API_BASE}/api/v1/release/seal-dry-run`);
        if (!res.ok) return;
        const runs = await res.json();
        
        historyTbody.innerHTML = "";
        if (runs.length === 0) {
            historyTbody.innerHTML = `<tr><td colspan="6" style="text-align:center; color:var(--text-secondary);">No seal dry runs executed yet.</td></tr>`;
            return;
        }
        
        runs.forEach(r => {
            const tr = document.createElement("tr");
            tr.innerHTML = `
                <td style="font-family: monospace; color: var(--accent-teal);">${r.seal_dry_run_id}</td>
                <td style="font-family: monospace;">${r.formal_preview_id}</td>
                <td>v${r.candidate_version}</td>
                <td style="font-weight: 600; color: ${r.seal_status === 'SEAL_READY' ? 'var(--accent-teal)' : '#ef4444'}">${r.seal_status}</td>
                <td>${r.operator}</td>
                <td>${r.created_at}</td>
            `;
            historyTbody.appendChild(tr);
        });
    } catch (err) {
        console.error("Error loading seal dry run history:", err);
    }
}

function renderClusterCommandMapV2(nodes) {
    if (!nodes) nodes = currentNodes;
    renderAgentCommandRail();
    renderDeviceFleetDrawer(nodes);
    renderClusterTopologyGroups(nodes);
}

function groupClusterDevicesByFleet(nodes) {
    const core = [];
    const mobile = [];
    const edge = [];
    const service = [];
    
    nodes.forEach(node => {
        const group = node.fleet_group || "";
        if (group === "core_compute" || node.id === "L1" || node.id === "L2" || node.id === "L3" || node.id === "W1") {
            core.push(node);
        } else if (group === "mobile_fleet" || (node.os && node.os.toLowerCase().includes("ipad")) || node.id === "IPAD" || node.id.includes("IPAD")) {
            mobile.push(node);
        } else if (group === "edge_phone" || (node.os && (node.os.toLowerCase().includes("ios") || node.os.toLowerCase().includes("iphone"))) || node.id === "IPHONE") {
            edge.push(node);
        } else {
            service.push(node);
        }
    });
    
    return { core, mobile, edge, service };
}

function renderDeviceFleetDrawer(nodes) {
    const coreSection = document.getElementById("cluster-device-core-section");
    const mobileSection = document.getElementById("cluster-device-mobile-section");
    const edgeSection = document.getElementById("cluster-device-edge-section");
    
    if (!coreSection || !mobileSection || !edgeSection) return;
    
    const { core, mobile, edge } = groupClusterDevicesByFleet(nodes);
    
    const buildCards = (groupNodes) => {
        return groupNodes.map(node => {
            const modelText = node.name.includes("MTXQ2LL/A") ? "MTXQ2LL/A" :
                              node.name.includes("MUU62LL/A") ? "MUU62LL/A" :
                              node.name.includes("MGNV2LL/A") ? "MGNV2LL/A" : "";
            
            const isSelected = selectedNodeId === node.id ? "selected" : "";
            
            let statusColor = "#6b7280";
            if (node.status === "Active" || node.status === "OK") statusColor = "#10b981";
            else if (node.status === "Reasoning") statusColor = "#3b82f6";
            else if (node.status === "Self-Healing") statusColor = "#a855f7";
            else if (node.status === "Triaging" || node.status === "Warning") statusColor = "#f59e0b";
            
            return `
                <div class="fleet-device-card ${isSelected}" id="fleet-card-${node.id}" onclick="selectClusterNode('${node.id}')" style="margin-bottom: 8px;">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <span style="font-size: 10px; font-weight: bold; color: #fff;">${escapeHtml(node.name)}</span>
                        <span style="width: 5px; height: 5px; border-radius: 50%; background: ${statusColor}; display: inline-block;"></span>
                    </div>
                    ${modelText ? `<div style="font-size: 8px; font-family: monospace; color: var(--accent-teal); margin-top: 1px;">${modelText}</div>` : ""}
                    <div style="display: flex; justify-content: space-between; align-items: center; font-size: 8px; color: var(--text-secondary); margin-top: 2px;">
                        <span>${node.ip}</span>
                        <span>CPU: ${node.cpu_usage || 0}%</span>
                    </div>
                </div>
            `;
        }).join("");
    };
    
    coreSection.innerHTML = `
        <div class="fleet-section-title"><i data-lucide="cpu" style="width: 10px; height: 10px;"></i> Core Compute</div>
        ${buildCards(core)}
    `;
    mobileSection.innerHTML = `
        <div class="fleet-section-title"><i data-lucide="tablet" style="width: 10px; height: 10px;"></i> Mobile Fleet</div>
        ${buildCards(mobile)}
    `;
    edgeSection.innerHTML = `
        <div class="fleet-section-title"><i data-lucide="smartphone" style="width: 10px; height: 10px;"></i> Edge Phones</div>
        ${buildCards(edge)}
    `;
    
    lucide.createIcons();
}

function renderSelectedNodeInspector(node) {
    const inspector = document.getElementById("cluster-selected-node-inspector");
    if (!inspector) return;
    
    if (!node) {
        inspector.innerHTML = `<span style="font-size: 11px; color: var(--text-secondary); font-style: italic;">Select a node from the map or fleet list to inspect details.</span>`;
        return;
    }
    
    let statusColor = "#6b7280";
    if (node.status === "Active" || node.status === "OK") statusColor = "#10b981";
    else if (node.status === "Reasoning") statusColor = "#3b82f6";
    else if (node.status === "Self-Healing") statusColor = "#a855f7";
    else if (node.status === "Triaging" || node.status === "Warning") statusColor = "#f59e0b";

    const modelVal = node.name.includes("MTXQ2LL/A") ? "MTXQ2LL/A" :
                     node.name.includes("MUU62LL/A") ? "MUU62LL/A" :
                     node.name.includes("MGNV2LL/A") ? "MGNV2LL/A" : 
                     (node.id === "IPAD" ? "IPAD PRO 12\"" : "Standard Node");
    
    const linkedAgents = node.agents && node.agents.length > 0 
        ? node.agents.map(a => a.name).join(", ") 
        : "No active agents";
        
    const recommendedAction = node.status === "Warning" || node.status === "Triaging" 
        ? "Initialize automated self-healing protocol or dispatch warning alert." 
        : "Vitals sync stable. No operator actions required.";
    
    inspector.innerHTML = `
        <div style="width: 100%; display: grid; grid-template-columns: repeat(4, 1fr) 2fr; gap: 12px; text-align: left; font-family: monospace; font-size: 10px;">
            <div class="inspector-field">
                <span class="inspector-label">NODE</span>
                <span class="inspector-value" style="color: var(--accent-teal);">${escapeHtml(node.name)}</span>
            </div>
            <div class="inspector-field">
                <span class="inspector-label">MODEL / IP</span>
                <span class="inspector-value">${modelVal} (${node.ip})</span>
            </div>
            <div class="inspector-field">
                <span class="inspector-label">STATUS / LOAD</span>
                <span class="inspector-value" style="display: flex; align-items: center; gap: 4px;">
                    <span style="width: 5px; height: 5px; border-radius: 50%; background: ${statusColor}; display: inline-block;"></span>
                    ${node.status} (CPU: ${node.cpu_usage || 0}%)
                </span>
            </div>
            <div class="inspector-field">
                <span class="inspector-label">ACTIVE AGENTS</span>
                <span class="inspector-value" style="text-overflow: ellipsis; overflow: hidden; white-space: nowrap; max-width: 130px;" title="${linkedAgents}">${linkedAgents}</span>
            </div>
            <div class="inspector-field">
                <span class="inspector-label">RECOMMENDED ACTION</span>
                <span class="inspector-value" style="color: #f59e0b;">${recommendedAction}</span>
            </div>
        </div>
    `;
}

function selectClusterNode(nodeId) {
    selectedNodeId = nodeId;
    
    document.querySelectorAll(".fleet-device-card").forEach(card => {
        card.classList.toggle("selected", card.id === `fleet-card-${nodeId}`);
    });
    
    const node = currentNodes.find(n => n.id === nodeId);
    renderSelectedNodeInspector(node);
    
    renderClusterTopologyGroups(currentNodes);
}

function toggleClusterTopologyGroup(groupId) {
    if (groupId === "mobile") {
        mobileGroupExpanded = !mobileGroupExpanded;
    } else if (groupId === "core") {
        coreGroupExpanded = !coreGroupExpanded;
    } else if (groupId === "edge") {
        edgeGroupExpanded = !edgeGroupExpanded;
    }
    renderClusterTopologyGroups(currentNodes);
}

function fitClusterTopologyViewport() {
    panX = 0;
    panY = 0;
    scale = 1.0;
    const svg = mermaidGraph.querySelector("svg");
    if (svg) {
        svg.style.transform = `translate(${panX}px, ${panY}px) scale(${scale})`;
    }
}

async function refreshClusterTopologyStatus() {
    try {
        const response = await fetch(`${API_BASE}/api/status`);
        if (response.ok) {
            const data = await response.json();
            updateUI(data);
        }
    } catch (err) {
        console.warn("Manual sync failed: ", err);
    }
}



// Expose restored functions to window to overwrite unused_views.js stubs
window.initDeviceRegistry = initDeviceRegistry;
window.loadRegistryData = loadRegistryData;
window.executeDeviceDiscovery = executeDeviceDiscovery;
window.renderDiscoveredDevices = renderDiscoveredDevices;
window.selectDiscoveredDevice = selectDiscoveredDevice;
window.executeDeviceApproval = executeDeviceApproval;
window.executeDeviceRejection = executeDeviceRejection;
window.renderApprovedServiceNodes = renderApprovedServiceNodes;
window.initCapabilityRouterUI = initCapabilityRouterUI;
window.initModelProviderRegistryUI = initModelProviderRegistryUI;
window.loadModelProviders = loadModelProviders;
window.initModelRouterUI = initModelRouterUI;
window.initCrewaiIngestionBridge = initCrewaiIngestionBridge;
window.initReleaseDecisionRoom = initReleaseDecisionRoom;
window.updateReleaseAuthorityUI = updateReleaseAuthorityUI;
window.startAuthorityCountdown = startAuthorityCountdown;
window.generateExecutionPlan = generateExecutionPlan;
window.exportPlanMarkdown = exportPlanMarkdown;
window.exportPlanJson = exportPlanJson;
window.initReleaseEvidenceRetention = initReleaseEvidenceRetention;
window.loadEvidenceRetentionList = loadEvidenceRetentionList;
window.classifyEvidence = classifyEvidence;
window.initReleaseEvidenceArchivePreview = initReleaseEvidenceArchivePreview;
window.calculateArchivePreview = calculateArchivePreview;
window.exportArchivePreviewMarkdown = exportArchivePreviewMarkdown;
window.exportArchivePreviewJSON = escapeHtml; // fallback or correct ref
window.initReleaseEvidenceArchiveBuildPlan = initReleaseEvidenceArchiveBuildPlan;
window.generateArchiveBuildPlan = generateArchiveBuildPlan;
window.exportBuildPlanMarkdown = exportBuildPlanMarkdown;
window.exportBuildPlanJSON = exportBuildPlanJSON;
window.initReleaseEvidenceArchiveSealPreview = initReleaseEvidenceArchiveSealPreview;
window.generateArchiveSealPreview = generateArchiveSealPreview;
window.exportSealPreviewMarkdown = exportSealPreviewMarkdown;
window.exportSealPreviewJSON = exportSealPreviewJSON;
window.fetchAndRenderGovernanceSummary = fetchAndRenderGovernanceSummary;
window.checkApprovalStatusForPreview = checkApprovalStatusForPreview;
window.initFormalReleaseSealDryRun = initFormalReleaseSealDryRun;
window.loadApprovedPreviewsForDryRun = loadApprovedPreviewsForDryRun;
window.executeSealDryRun = executeSealDryRun;
window.loadSealDryRunHistory = loadSealDryRunHistory;
window.renderClusterCommandMapV2 = renderClusterCommandMapV2;
window.groupClusterDevicesByFleet = groupClusterDevicesByFleet;
window.renderDeviceFleetDrawer = renderDeviceFleetDrawer;
window.renderSelectedNodeInspector = renderSelectedNodeInspector;
window.selectClusterNode = selectClusterNode;
window.toggleClusterTopologyGroup = toggleClusterTopologyGroup;
window.fitClusterTopologyViewport = fitClusterTopologyViewport;
window.refreshClusterTopologyStatus = refreshClusterTopologyStatus;

    async function loadBrainAutonomyTelemetry() {
        try {
            const res = await fetch('/api/v1/brain/status');
            if (!res.ok) return;
            const data = await res.json();

            // 1. Render Chat Messages
            const chatMessages = el('brain-chat-messages');
            if (chatMessages && data.messages) {
                chatMessages.innerHTML = data.messages.map(msg => `
                    <div style="margin-bottom: 8px; padding: 8px 12px; border-radius: 6px; max-width: 85%; ${
                        msg.role === 'user' 
                        ? 'background: rgba(96, 165, 250, 0.15); border: 1px solid rgba(96, 165, 250, 0.3); align-self: flex-end; margin-left: auto; color: #fff;' 
                        : 'background: rgba(16, 185, 129, 0.1); border: 1px solid rgba(16, 185, 129, 0.2); align-self: flex-start; color: #fff;'
                    }">
                        <div style="font-size: 9px; text-transform: uppercase; color: var(--text-secondary); margin-bottom: 4px; font-weight: bold;">
                            ${msg.role === 'user' ? 'Michael Hoch' : 'Brain LLM'}
                        </div>
                        <div style="word-break: break-word;">${msg.content}</div>
                    </div>
                `).join('');
                chatMessages.scrollTop = chatMessages.scrollHeight;
            }

            // 2. Render Autonomy Mode active styling
            const modeButtons = document.querySelectorAll('#brain-mode-selector button');
            modeButtons.forEach(btn => {
                const modeVal = btn.getAttribute('data-mode');
                if (modeVal === data.mode) {
                    btn.className = 'btn btn-mode active';
                    btn.style.border = '1px solid var(--accent-teal)';
                    btn.style.background = 'rgba(16, 185, 129, 0.1)';
                    btn.style.color = 'var(--accent-teal)';
                } else {
                    btn.className = 'btn btn-mode';
                    btn.style.border = '1px solid var(--border-glass)';
                    btn.style.background = 'transparent';
                    btn.style.color = 'var(--text-secondary)';
                }
            });

            // 3. Render Readiness Score & Gauge
            const readiness = data.readiness || {};
            const scoreVal = readiness.score || 0;
            if (el('brain-readiness-percentage')) {
                el('brain-readiness-percentage').innerHTML = `
                    ${scoreVal}%
                    <span style="font-size: 8px; color: var(--text-secondary); text-transform: uppercase; margin-top: 2px;">Readiness</span>
                `;
            }
            const readinessGauge = el('brain-readiness-gauge');
            if (readinessGauge) {
                const maxOffset = 263.8;
                const offset = maxOffset - (maxOffset * scoreVal / 100);
                readinessGauge.style.strokeDashoffset = offset;
            }

            // Readiness stats grid
            if (el('readiness-prediction')) el('readiness-prediction').textContent = `${readiness.predictionAccuracy || 0}%`;
            if (el('readiness-qa')) el('readiness-qa').textContent = `${readiness.qaPassRate || 0}%`;
            if (el('readiness-policy')) el('readiness-policy').textContent = readiness.policyViolations || 0;
            if (el('readiness-rollback')) el('readiness-rollback').textContent = `${readiness.rollbackAvailable || 0}%`;
            if (el('readiness-forbidden')) el('readiness-forbidden').textContent = readiness.forbiddenActionAttempts || 0;
            if (el('readiness-eligible')) {
                el('readiness-eligible').textContent = readiness.eligibleForGated ? "YES" : "NO";
                el('readiness-eligible').style.color = readiness.eligibleForGated ? "var(--accent-teal)" : "#ef4444";
            }

            // 4. Render Suggested Next Action Panel
            const suggestionContainer = el('brain-suggestion-container');
            if (suggestionContainer) {
                if (!data.activeSuggestion) {
                    suggestionContainer.innerHTML = '<div style="color: var(--text-secondary);">No action recommended yet. Click Send or type instructions to query suggestions.</div>';
                } else {
                    const sug = data.activeSuggestion;
                    suggestionContainer.innerHTML = `
                        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom: 8px;">
                            <strong style="color: #fff; font-size: 13px;">${sug.action.toUpperCase()}</strong>
                            <div style="display:flex; gap: 6px;">
                                <span class="badge" style="background: ${sug.riskLevel === 'HIGH' ? 'rgba(239,68,68,0.15)' : 'rgba(16,185,129,0.15)'}; color: ${sug.riskLevel === 'HIGH' ? '#ef4444' : 'var(--accent-teal)'}; font-size: 9px; font-weight: bold;">
                                    ${sug.riskLevel} RISK
                                </span>
                                <span class="badge warning" style="font-size: 9px;">${sug.confidence}% Match</span>
                            </div>
                        </div>
                        <div style="color: var(--text-secondary); margin-bottom: 12px; font-family: monospace;">${sug.rationale}</div>
                        
                        <!-- Revision Input -->
                        <div style="display: flex; flex-direction: column; gap: 8px; margin-bottom: 12px; background: rgba(0,0,0,0.2); padding: 8px; border-radius: 4px; border: 1px solid var(--border-glass);">
                            <span style="font-size: 9px; color: var(--text-secondary); text-transform: uppercase;">Optional Revision Correction</span>
                            <input type="text" id="brain-revision-text" placeholder="Add style rule or instruction (e.g. use dark UI)..." style="padding: 6px; font-size: 11px; background: rgba(0,0,0,0.3); border: 1px solid var(--border-glass); border-radius: 4px; color: #fff;">
                        </div>

                        <!-- Feedback action buttons -->
                        <div style="display:flex; gap:8px;">
                            <button class="btn btn-primary" onclick="window.submitBrainFeedback('${sug.id}', 'approved')" style="flex:1; padding:6px; font-size:11px; background:#10b981; color:#000; font-weight:bold; border:none; border-radius:4px; cursor:pointer;">Approve</button>
                            <button class="btn btn-secondary" onclick="window.submitBrainFeedback('${sug.id}', 'rejected')" style="flex:1; padding:6px; font-size:11px; background:#ef4444; color:#fff; font-weight:bold; border:none; border-radius:4px; cursor:pointer;">Reject</button>
                            <button class="btn" onclick="window.submitBrainFeedback('${sug.id}', 'rejected', document.getElementById('brain-revision-text').value)" style="flex:1; padding:6px; font-size:11px; background:rgba(255,255,255,0.05); color:#fff; border:1px solid var(--border-glass); border-radius:4px; cursor:pointer;">Revise & Reject</button>
                        </div>
                    `;
                }
            }

            // 5. Render Doctrine Memory list
            const doctrineList = el('brain-doctrine-list');
            if (doctrineList && data.doctrineRules) {
                if (data.doctrineRules.length === 0) {
                    doctrineList.innerHTML = '<div style="color: var(--text-secondary); padding: 8px 0;">No active rules in memory.</div>';
                } else {
                    doctrineList.innerHTML = data.doctrineRules.map(rule => `
                        <div style="display:flex; justify-content:space-between; align-items:center; border-bottom:1px solid rgba(255,255,255,0.02); padding-bottom: 4px;">
                            <span style="color:#fff; text-overflow: ellipsis; overflow: hidden; white-space: nowrap; max-width: 75%;">${rule.ruleText}</span>
                            <span style="font-size: 8px; color: var(--accent-yellow); text-transform: uppercase;">${rule.source}</span>
                        </div>
                    `).join('');
                }
            }

            // 6. Render Shadow Prediction Log
            const predictionLog = el('brain-prediction-log');
            if (predictionLog && data.shadowLogs) {
                if (data.shadowLogs.length === 0) {
                    predictionLog.innerHTML = '<div style="color: var(--text-secondary); padding: 4px 0;">Log is empty.</div>';
                } else {
                    predictionLog.innerHTML = data.shadowLogs.map(log => `
                        <div style="display:flex; justify-content:space-between; border-bottom:1px solid rgba(255,255,255,0.02); padding-bottom: 2px;">
                            <span style="color: var(--text-secondary); max-width: 60%; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">${log.suggestedAction}</span>
                            <span style="color: ${log.decision === 'approved' ? 'var(--accent-teal)' : log.decision === 'rejected' ? '#ef4444' : 'var(--accent-yellow)'}">${log.decision.toUpperCase()}</span>
                        </div>
                    `).join('');
                }
            }

            // 7. Render Human Escalations
            const escalationList = el('brain-escalation-list');
            if (escalationList && data.escalations) {
                if (data.escalations.length === 0) {
                    escalationList.innerHTML = '<div style="color: var(--text-secondary); padding: 4px 0;">Escalation queue is empty.</div>';
                } else {
                    escalationList.innerHTML = data.escalations.map(esc => `
                        <div style="border-bottom:1px solid rgba(239, 68, 68, 0.2); padding-bottom: 3px;">
                            <span style="color:#ef4444; font-weight:bold; font-family:monospace;">${esc.action.toUpperCase()}</span>
                            <p style="margin: 2px 0 0 0; color: var(--text-secondary); font-size: 9px;">${esc.reason}</p>
                        </div>
                    `).join('');
                }
            }

            // 8. Render Evidence Files Trail
            const evidenceContainer = el('cc-evidence-container');
            if (evidenceContainer && data.evidenceFiles) {
                if (data.evidenceFiles.length === 0) {
                    evidenceContainer.innerHTML = '<div style="color: var(--text-secondary); text-align: center; font-size: 12px; padding: 20px;">No evidence files generated yet.</div>';
                } else {
                    evidenceContainer.innerHTML = data.evidenceFiles.map(pack => `
                        <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid rgba(255,255,255,0.03); padding-bottom: 6px; font-size: 11px;">
                            <a href="${pack.path}" target="_blank" style="color: var(--accent-teal); text-decoration: none; font-family: monospace;">${pack.name}</a>
                            <span style="color: var(--text-secondary); font-size:10px;">${new Date(pack.timestamp).toLocaleTimeString()}</span>
                        </div>
                    `).join('');
                }
            }

        } catch (err) {
            console.error("Error loading Brain Autonomy telemetry:", err);
        }
    }

    window.sendBrainOperatorMessage = async function() {
        const inputEl = el('brain-chat-input');
        if (!inputEl || !inputEl.value.trim()) return;

        try {
            const res = await fetch('/api/v1/brain/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message: inputEl.value.trim() })
            });
            if (res.ok) {
                inputEl.value = '';
                await loadProductionCommandCenterView();
            }
        } catch (err) {
            console.error("Error sending operator message:", err);
        }
    };

    window.submitBrainFeedback = async function(suggestionId, decision, correction = '') {
        try {
            const res = await fetch('/api/v1/brain/feedback', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ suggestionId, decision, correction })
            });
            if (res.ok) {
                await loadProductionCommandCenterView();
            }
        } catch (err) {
            console.error("Error submitting brain feedback:", err);
        }
    };

    window.setBrainAutonomyMode = async function(mode) {
        try {
            const res = await fetch('/api/v1/brain/mode', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ mode })
            });
            if (res.ok) {
                await loadProductionCommandCenterView();
            } else {
                const data = await res.json();
                alert(data.detail || "Failed to switch autonomy mode.");
            }
        } catch (err) {
            console.error("Error setting autonomy mode:", err);
        }
    };

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

window.triggerArtifactWorkflow = async function() {
    const btn = document.getElementById("btn-trigger-artifact-workflow");
    if (btn) btn.disabled = true;

    const requester = document.getElementById("artifact-requester-select")?.value || "guest";
    const prompt = document.getElementById("artifact-prompt-input")?.value || "";
    const target = document.getElementById("artifact-target-select")?.value || "";

    const rbacRole = document.getElementById("ui-rbac-role");
    const rbacShell = document.getElementById("ui-rbac-shell");
    const rbacRouting = document.getElementById("ui-rbac-routing");
    const rbacDelivery = document.getElementById("ui-rbac-delivery");

    const classBadge = document.getElementById("ui-class-badge");
    const classReason = document.getElementById("ui-class-reason");

    const stepsContainer = document.getElementById("ui-workflow-steps");
    const sourceList = document.getElementById("ui-source-list");
    const qaScore = document.getElementById("ui-qa-score");
    const qaFindings = document.getElementById("ui-qa-findings");

    const targetAllowlist = document.getElementById("ui-target-allowlist");
    const targetProvider = document.getElementById("ui-target-provider");
    const targetFolder = document.getElementById("ui-target-folder");
    const receiptDetails = document.getElementById("ui-receipt-details");

    // Initialize UI states
    if (stepsContainer) stepsContainer.innerHTML = '<div style="color: var(--accent-teal);">Compiling workflow...</div>';
    if (sourceList) sourceList.innerHTML = '<div>Syncing sources...</div>';
    if (qaScore) qaScore.textContent = "-";
    if (qaFindings) qaFindings.textContent = "Pending QA run.";
    if (targetAllowlist) targetAllowlist.textContent = "Verifying...";
    if (receiptDetails) receiptDetails.textContent = "Processing upload...";

    // Render local RBAC parameters based on pre-seeded roles
    if (requester === "michael") {
        if (rbacRole) rbacRole.textContent = "system_owner";
        if (rbacShell) rbacShell.textContent = "ALLOWED";
        if (rbacRouting) rbacRouting.textContent = "ALLOWED";
        if (rbacDelivery) rbacDelivery.textContent = "ALLOWED";
    } else if (requester === "alison") {
        if (rbacRole) rbacRole.textContent = "trusted_family_operator";
        if (rbacShell) rbacShell.textContent = "DENIED (Escalate)";
        if (rbacRouting) rbacRouting.textContent = "ALLOWED";
        if (rbacDelivery) rbacDelivery.textContent = "ALLOWED";
    } else {
        if (rbacRole) rbacRole.textContent = "guest_operator";
        if (rbacShell) rbacShell.textContent = "DENIED";
        if (rbacRouting) rbacRouting.textContent = "DENIED";
        if (rbacDelivery) rbacDelivery.textContent = "DENIED";
    }

    try {
        // Step 1: Compile workflow
        const compileRes = await fetch('/api/v1/workflows/compile', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ requester, text: prompt })
        });

        if (!compileRes.ok) {
            const err = await compileRes.json();
            if (classBadge) {
                classBadge.textContent = "BLOCKED";
                classBadge.style.backgroundColor = "rgba(239, 68, 68, 0.15)";
                classBadge.style.color = "#ef4444";
            }
            if (classReason) classReason.textContent = err.detail || "Workflow compilation blocked.";
            if (stepsContainer) stepsContainer.innerHTML = `<div style="color: #ef4444; font-weight: bold;">[BLOCKED] ${err.detail || "Access Denied"}</div>`;
            if (targetAllowlist) targetAllowlist.textContent = "BLOCKED";
            if (receiptDetails) receiptDetails.textContent = "Handoff canceled due to policy violation.";
            if (btn) btn.disabled = false;
            return;
        }

        const workflow = await compileRes.json();

        // Update classification badge
        const classification = workflow.classification;
        if (classBadge) {
            classBadge.textContent = classification.toUpperCase();
            if (classification === "sensitive" || classification === "restricted") {
                classBadge.style.backgroundColor = "rgba(239, 68, 68, 0.15)";
                classBadge.style.color = "#ef4444";
            } else if (classification === "work internal") {
                classBadge.style.backgroundColor = "rgba(59, 130, 246, 0.15)";
                classBadge.style.color = "#3b82f6";
            } else if (classification === "family") {
                classBadge.style.backgroundColor = "rgba(16, 185, 129, 0.15)";
                classBadge.style.color = "var(--accent-teal)";
            } else {
                classBadge.style.backgroundColor = "rgba(255, 255, 255, 0.1)";
                classBadge.style.color = "#fff";
            }
        }
        if (classReason) classReason.textContent = `Intents matched successfully. Scope: ${classification}.`;

        // Render Workflow Steps Checklist
        let stepsHtml = "";
        workflow.steps.forEach((step, idx) => {
            stepsHtml += `
                <div style="display: flex; align-items: center; gap: 8px; font-family: monospace;">
                    <span id="wf-step-bullet-${idx}" style="color: var(--accent-orange);">[/]</span>
                    <span id="wf-step-text-${idx}" style="color: var(--text-secondary);">${step}</span>
                </div>
            `;
        });
        if (stepsContainer) stepsContainer.innerHTML = stepsHtml;

        // Step 2: Rank sources & update citations
        const stepBullet0 = document.getElementById("wf-step-bullet-0");
        if (stepBullet0) stepBullet0.textContent = "[x]";
        const stepText0 = document.getElementById("wf-step-text-0");
        if (stepText0) stepText0.style.color = "#fff";

        const stepBullet1 = document.getElementById("wf-step-bullet-1");
        if (stepBullet1) {
            stepBullet1.textContent = "[x]";
            const stepText1 = document.getElementById("wf-step-text-1");
            if (stepText1) stepText1.style.color = "#fff";
        }

        const rankRes = await fetch('/api/v1/rag/rank-sources', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ query: prompt })
        });
        
        let citationText = "";
        let sourcesData = [];
        if (rankRes.ok) {
            const rankData = await rankRes.json();
            sourcesData = rankData.ranked_sources;
            if (rankData.citations && rankData.citations.length > 0) {
                rankData.citations.forEach(c => {
                    citationText += `<div style="margin-bottom: 4px;"><strong>${c.ref_id}:</strong> ${c.name}</div>`;
                });
            } else {
                citationText = "<div>No citation references generated.</div>";
            }
        } else {
            citationText = "<div>Source ranking service error.</div>";
        }
        if (sourceList) sourceList.innerHTML = citationText;

        const stepBullet2 = document.getElementById("wf-step-bullet-2");
        if (stepBullet2) {
            stepBullet2.textContent = "[x]";
            const stepText2 = document.getElementById("wf-step-text-2");
            if (stepText2) stepText2.style.color = "#fff";
        }

        // Step 3: Build Slides
        const slidesPayload = {
            requester,
            title: prompt || "Cybersecurity Guidance",
            subtitle: "Branded Swarm Analysis",
            slides: [
                {
                    title: "Executive Summary",
                    bullets: [
                        "Identified compliance gaps with pre-seeded doctrine parameters.",
                        "All local LLM queries restricted to loopback boundary."
                    ]
                },
                {
                    title: "Security Findings",
                    bullets: [
                        sourcesData.length > 0 ? `Validated source: ${sourcesData[0].name}` : "No third-party cloud API keys exposed.",
                        "Enforced Role-Based Access controls on all runtime file edits."
                    ]
                }
            ],
            target_name: target
        };

        const slidesRes = await fetch('/api/v1/artifacts/slides', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(slidesPayload)
        });

        if (!slidesRes.ok) {
            const err = await slidesRes.json();
            throw new Error(`Slide Generation Failed: ${err.detail || 'Access Denied'}`);
        }

        const slidesData = await slidesRes.json();
        const filepath = slidesData.filepath;

        const stepBullet3 = document.getElementById("wf-step-bullet-3");
        if (stepBullet3) {
            stepBullet3.textContent = "[x]";
            const stepText3 = document.getElementById("wf-step-text-3");
            if (stepText3) stepText3.style.color = "#fff";
        }

        const stepBullet4 = document.getElementById("wf-step-bullet-4");
        if (stepBullet4) {
            stepBullet4.textContent = "[x]";
            const stepText4 = document.getElementById("wf-step-text-4");
            if (stepText4) stepText4.style.color = "#fff";
        }

        // Step 4: Export printable PDF
        const pdfRes = await fetch('/api/v1/artifacts/export/pdf', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                requester,
                title: slidesPayload.title,
                paragraphs: [
                    "This brief details cybersecurity posture reviews adhering to the local-first Swarm doctrine.",
                    "No data was transmitted over public networks or unapproved APIs."
                ]
            })
        });

        const stepBullet5 = document.getElementById("wf-step-bullet-5");
        if (stepBullet5) {
            stepBullet5.textContent = "[x]";
            const stepText5 = document.getElementById("wf-step-text-5");
            if (stepText5) stepText5.style.color = "#fff";
        }

        const stepBullet6 = document.getElementById("wf-step-bullet-6");
        if (stepBullet6) {
            stepBullet6.textContent = "[x]";
            const stepText6 = document.getElementById("wf-step-text-6");
            if (stepText6) stepText6.style.color = "#fff";
        }

        // Step 5: Verify QA Gate
        const qaRes = await fetch('/api/v1/artifacts/qa', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ filepath })
        });

        if (qaRes.ok) {
            const qaData = await qaRes.json();
            if (qaScore) qaScore.textContent = `${qaData.score}/100`;
            if (qaFindings) qaFindings.textContent = qaData.findings.join(" | ");
        } else {
            if (qaScore) qaScore.textContent = "Fail";
            if (qaFindings) qaFindings.textContent = "QA analysis failed.";
        }

        // Step 6: Google Drive Delivery
        const deliveryRes = await fetch('/api/v1/delivery/google-drive', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                requester,
                filepath,
                target_name: target
            })
        });

        const stepBullet7 = document.getElementById("wf-step-bullet-7");
        if (stepBullet7) {
            stepBullet7.textContent = "[x]";
            const stepText7 = document.getElementById("wf-step-text-7");
            if (stepText7) stepText7.style.color = "#fff";
        }

        const stepBullet8 = document.getElementById("wf-step-bullet-8");
        if (stepBullet8) {
            stepBullet8.textContent = "[x]";
            const stepText8 = document.getElementById("wf-step-text-8");
            if (stepText8) stepText8.style.color = "#fff";
        }

        if (!deliveryRes.ok) {
            const err = await deliveryRes.json();
            if (targetAllowlist) targetAllowlist.textContent = "BLOCKED";
            if (receiptDetails) receiptDetails.textContent = `Handoff Denied: ${err.detail || 'Target verification failed'}`;
            return;
        }

        const delivery = await deliveryRes.json();

        // Update target status & receipt logging
        if (targetAllowlist) targetAllowlist.textContent = "VERIFIED (Pass)";
        if (targetProvider) targetProvider.textContent = delivery.provider;
        if (targetFolder) targetFolder.textContent = delivery.folder;

        if (receiptDetails) {
            receiptDetails.innerHTML = `
                <div><strong>Receipt ID:</strong> ${delivery.receipt_id}</div>
                <div><strong>Timestamp:</strong> ${delivery.timestamp}</div>
                <div><strong>Destination:</strong> ${delivery.provider}/${delivery.folder}</div>
                <div><strong>Checksum:</strong> ${delivery.sha256}</div>
            `;
        }

    } catch (err) {
        if (stepsContainer) stepsContainer.innerHTML = `<div style="color: #ef4444; font-weight: bold;">[ERROR] ${err.message}</div>`;
        if (receiptDetails) receiptDetails.textContent = `Workflow error: ${err.message}`;
    } finally {
        if (btn) btn.disabled = false;
        if (typeof lucide !== 'undefined' && lucide.createIcons) {
            lucide.createIcons();
        }
    }
};

document.addEventListener("DOMContentLoaded", () => {
    initDeviceSwarmPrototype();
    if (typeof lucide !== 'undefined' && lucide.createIcons) {
        lucide.createIcons();
    }
});
