# HOCH PODS Visual Authority Review

- Timestamp UTC: 2026-07-02T19:28:20Z
- Branch: goal-ui-v21-runner-release-hygiene-20260702T184544Z
- Commit: be0a08a

## Current Visual Authority Files
docs/design/approved-visual-authority/hoch-control-plane-authority.png
docs/design/approved-visual-authority/hoch-pods-has-hasf-approved-authority.jpeg
docs/design/approved-visual-authority/hoch-pods-theater-authority.jpeg
docs/design/approved-visual-authority/README_DOCTRINE.md
docs/design/approved-visual-authority/visual-authority-manifest.json

## Inbox Files
docs/design/approved-visual-authority-inbox/README_DROP_APPROVED_IMAGES_HERE.md
docs/design/approved-visual-authority-inbox/README_DROP_CANDIDATES_HERE.md

## Quarantine Files
docs/design/quarantine/README.md

## UI Theme References
backend/pert_server.py:1622:        "hoch_pods_theater": {
backend/pert_server.py:1806:        "hoch_pods_runtime_freshness": panels_freshness.get("hoch_pods_theater", {}),
backend/pert_server.py:1937:            /* HOCH PODS Design Tokens */
backend/pert_server.py:2243:        /* HOCH PODS Theater and Topology Styles */
backend/pert_server.py:2442:        /* HOCH PODS VISUAL FIDELITY COMMAND SURFACE STYLES */
backend/pert_server.py:2587:        #hoch-pods-theater-panel {
backend/pert_server.py:2986:        .theater-capsule {
backend/pert_server.py:3004:        .theater-capsule:hover {
backend/pert_server.py:3191:        #hoch-theater-controls {
backend/pert_server.py:3202:        .theater-btn {
backend/pert_server.py:3212:        .theater-btn:hover, .theater-btn.active {
backend/pert_server.py:3247:            .theater-capsule:hover {
backend/pert_server.py:3256:        .reduce-motion-active .theater-capsule:hover {
backend/pert_server.py:3261:        /* --- HOCH PODS LIVE MOVIE ACTIVATION PATCH --- */
backend/pert_server.py:3297:        /* --- CINEMATIC HOCH PODS THEATER (RC52.1) --- */
backend/pert_server.py:3360:        .theater-stage {
backend/pert_server.py:3546:        #hoch-pods-theater-control-bar {
backend/pert_server.py:3716:        <!-- HOCH PODS SECURE AGENT RUNTIME COCKPIT -->
backend/pert_server.py:3724:                        <h2 style="margin:0; font-size:16px; font-weight:800; color:#fff; border:none; padding:0; text-shadow:0 0 10px rgba(34,246,255,0.4);">HOCH PODS Command Surface</h2>
backend/pert_server.py:3746:                    <div id="hoch-pods-theater-panel" style="margin-top: 10px;">
backend/pert_server.py:3748:            <div id="hoch-pods-theater-control-bar">
backend/pert_server.py:3750:                <button id="toggle-theater-mode" class="theater-btn active">Theater Mode</button>
backend/pert_server.py:3751:                <button id="toggle-data-mode" class="theater-btn">Data Mode</button>
backend/pert_server.py:3752:                <button id="toggle-reduce-motion" class="theater-btn">Reduce Motion</button>
backend/pert_server.py:3753:                <button id="toggle-show-stale" class="theater-btn active">Show Stale Sources</button>
backend/pert_server.py:3754:                <button id="toggle-show-profiles" class="theater-btn active">Show Agent Profiles</button>
backend/pert_server.py:3755:                <button id="toggle-show-scorecards" class="theater-btn active">Show Scorecards</button>
backend/pert_server.py:3756:                <button id="replay-movie" class="theater-btn">Replay Movie</button>
backend/pert_server.py:3758:                    <div class="theater-stage" id="hoch-pods-intro-movie-board">
backend/pert_server.py:3763:        <img class="base-shell" src="/docs/design/assets/hoch-pods-theater-reference.jpeg" alt="HOCH PODS Theater visual shell" />
backend/pert_server.py:3766:        <div class="overlay-container" id="hoch-pods-theater">
backend/pert_server.py:4035:                    <!-- Legacy compatibility layout renders below the theater -->
backend/pert_server.py:4110:                                <button onclick="document.getElementById('hoch-agent-profile-drawer').classList.remove('active')" class="theater-btn" style="margin-top:auto; align-self:flex-end;">Close HUD</button>
backend/pert_server.py:4147:                                <div style="font-size:8px; color:var(--text-secondary);">HOCH PODS</div>
backend/pert_server.py:4180:                        <h3 style="margin-top:0; font-size:12px; font-weight:800; text-transform:uppercase; color:var(--hoch-amber); border-bottom:1px solid rgba(255,255,255,0.05); padding-bottom:6px; margin-bottom:12px;">HOCH PODS Hardening Guide</h3>
backend/pert_server.py:5717:                    const theaterContainer = document.getElementById("hoch-pods-container") || document.getElementById("hoch-pods-theater");
backend/pert_server.py:5718:                    if (theaterContainer) {
backend/pert_server.py:5722:                        theaterContainer.appendChild(launchBay);
backend/pert_server.py:5728:                const theaterMotionContainer = document.getElementById("hoch-pods-container");
backend/pert_server.py:5729:                if (theaterMotionContainer) theaterMotionContainer.classList.remove("reduce-motion-active");
backend/pert_server.py:5749:                    const pt = data.freshness_authority.panels.hoch_pods_theater;
backend/pert_server.py:6165:                    const theaterEl = document.getElementById("hoch-pods-container");
backend/pert_server.py:6166:                    if (theaterEl) {
backend/pert_server.py:6167:                        const tRect = theaterEl.getBoundingClientRect();
backend/pert_server.py:6258:                                <div class="theater-capsule pod-card pod-capsule ${stateClass} ${theatricalClass}" id="pod-card-${podReg.pod_id}" style="width:70px; height:70px;">
backend/pert_server.py:6294:                                            linksContainer.innerHTML += `<a href="/view-doc?path=${encodeURIComponent(l)}" class="theater-btn" target="_blank" style="display:inline-block; margin-right:5px; margin-bottom:5px;">${base}</a>`;
backend/pert_server.py:6327:                                attachDetailsHandler(container.querySelector(".theater-capsule"));
backend/pert_server.py:6363:                                attachDetailsHandler(container.querySelector(".theater-capsule"));
backend/pert_server.py:6376:                // HOCH PODS Scheduler Updates
backend/pert_server.py:6936:        document.getElementById("toggle-theater-mode").addEventListener("click", function() {
backend/pert_server.py:6949:            document.getElementById("toggle-theater-mode").classList.remove("active");
backend/pert_server.py:6956:                document.getElementById("hoch-pods-theater").appendChild(rawJsonEl);
backend/pert_server.py:6975:            const theater = document.getElementById("hoch-pods-container");
backend/pert_server.py:6976:            if (theater) {
backend/pert_server.py:6977:                theater.classList.toggle("reduce-motion-active");
backend/pert_server.py:7430:# HOCH PODS Moonshot Liftoff Control Plane
backend/pert_server.py:7431:@app.get("/ui-moonshot")
backend/pert_server.py:7432:def hoch_pods_moonshot_ui():
backend/pert_server.py:7435:    ui_path = Path("has_live_project_tracker/ui/hoch_pods_liftoff.html")
backend/pert_server.py:7437:        return HTMLResponse("<h1>HOCH PODS Moonshot UI missing</h1>", status_code=404)
has_live_project_tracker/ui/hoch_pods_liftoff.html:6:<title>HOCH PODS Liftoff Control Plane V2</title>
has_live_project_tracker/ui/hoch_pods_liftoff.html:215:    <h1>HOCH PODS Liftoff Control Plane V2</h1>
has_live_project_tracker/ui/hoch_pods_liftoff.html:320:        <pre class="console" id="console">booting HOCH PODS V2...</pre>
has_live_project_tracker/ui/hoch_pods_liftoff.html:385:      ["Visual Authority Agent","Binds HOCH PODS approved theater theme"],
has_live_project_tracker/ui/hoch_pods_liftoff.html:398:      ["UI Theater Pod","HOCH PODS liftoff visual control plane","ACTIVE","V2"],
docs/design/approved-visual-authority/visual-authority-manifest.json:4:  "approved_image_count": 1,
docs/design/approved-visual-authority/visual-authority-manifest.json:5:  "approved_images_only": true,
docs/design/approved-visual-authority/visual-authority-manifest.json:7:  "approved_image": {
docs/design/approved-visual-authority/visual-authority-manifest.json:8:    "canonical_path": "docs/design/approved-visual-authority/hoch-pods-has-hasf-approved-authority.jpeg",
docs/design/approved-visual-authority/visual-authority-manifest.json:9:    "canonical_filename": "hoch-pods-has-hasf-approved-authority.jpeg",
docs/design/approved-visual-authority/visual-authority-manifest.json:47:    "unapproved image references",

## Current Dirty Visual Files
 M docs/design/approved-visual-authority/visual-authority-manifest.json
 M docs/evidence/ui/screenshots/hoch-pods-theater-prototype-current.png
 M docs/evidence/ui/screenshots/hoch-pods-theater-prototype-v2-current.png
?? docs/design/approved-visual-authority-inbox/
?? docs/design/approved-visual-authority/README_DOCTRINE.md
?? docs/design/approved-visual-authority/hoch-pods-has-hasf-approved-authority.jpeg
?? docs/design/quarantine/
?? docs/evidence/runtime/workspace-visual-garbage-cleanup.md
?? docs/evidence/visual_authority/
?? scripts/lock_visual_authority_from_approved_candidates.py
?? scripts/review_visual_authority_candidates.py
?? scripts/verify_visual_authority_doctrine.py
?? scripts/verify_workspace_visual_hygiene.py
?? tests/e2e/rc55-visual-authority-doctrine.spec.ts
?? tools/hoch_pods_theme_guard/hoch_pods_theme_guard/file.png
