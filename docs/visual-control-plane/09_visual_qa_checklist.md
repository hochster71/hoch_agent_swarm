# Visual QA Checklist

Every page, layout, and component iteration must be verified against this visual QA checklist prior to deployment.

## 1. Dark Theme Consistency
- [ ] Primary background matches `--bg-primary` (`#030303`) or `--bg-secondary` (`#0B0B0D`).
- [ ] No pure white `#FFFFFF` text is used for body paragraphs (uses `#F5F7FA` or `#AAB0BD`).
- [ ] Text contrast ratios satisfy WCAG AA (at least `4.5:1` for normal text, `3:1` for large text).
- [ ] Subtle borders (`--border-subtle`) are styled with `#24242E`.

## 2. Route Coverage
- [ ] Path mappings in the router are correctly declared in the design blueprints.
- [ ] Custom pages render for: `/`, `/control-plane`, `/factory`, and `/life`.

## 3. Card State Coverage
- [ ] Live status cards support the required status states: `LIVE`, `DEGRADED`, `PENDING`, `SIMULATED`, `STALE`, `FAIL-CLOSED`, `UNAVAILABLE`, and `UNKNOWN`.
- [ ] Cards display fallback placeholders if backend response is slow or missing.

## 4. No Fake Status Indicators
- [ ] State indicators (`GO`, `COMPLETE`) are rendered only when validated by corresponding backend logs.
- [ ] The dashboard displays `SIMULATED` or `UNAVAILABLE` when a worker node cannot be reached.

## 5. Accessibility Controls
- [ ] Color-only meaning is avoided; all statuses contain text labels or icon symbols (e.g. checkmark, alert).
- [ ] Target elements support keyboard focus-ring highlighting.
- [ ] Interactive buttons have tab indexes and descriptive `aria-label` tags.

## 6. Motion & Reduced Motion
- [ ] Telemetry heartbeats fade with a soft duration of `2s` under normal settings.
- [ ] Media queries for `prefers-reduced-motion: reduce` completely disable sweeps, pulses, and particle paths.

## 7. Prompt-Library Linkability
- [ ] Agent cards render active prompt identifiers (`PR-*`).
- [ ] Clicking a prompt link opens the underlying prompt payload view.

## 8. Dashboard Density & Layout
- [ ] Telemetry grids display data points cleanly without overlap.
- [ ] Text wraps properly without overflowing card borders.
- [ ] Content adjusts gracefully to tablet and mobile screens.
