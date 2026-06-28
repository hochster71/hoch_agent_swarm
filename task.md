# PROTO-1 — HOCH Mesh Sentinel Map

## Mission
Spin up the first Kimi-style HOCH prototype using the HOCH theme, but enforce:

LIVE RUNTIME OR DELETE / QUARANTINE.

## Checklist
- [x] Create backend Mesh Sentinel map aggregator
- [x] Add custom CSS classes and `@keyframes led-pulse` to `frontend/index.html` style section
- [x] Update layout of `#view-clawde` card to add `#clawde-phase-cards-container` and `#clawde-selected-status-light` in `frontend/index.html`
- [x] Add `#clawde-gate-lockout-notice` in Gated Execution Control inside `frontend/index.html`
- [x] Update build version headers and app script tag to `UX2` in `frontend/index.html`
- [/] Implement `selectedPhase` state and card selection controller logic in `frontend/app.js`:ui-contract
- [ ] Run E2E runtime checks
- [ ] Run CI pipeline
- [ ] Commit and retag
