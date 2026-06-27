# Design System Tokens

This document defines the CSS variable design tokens for the dark-theme visual control plane.

## Color Palette Tokens

### Backgrounds & Panels
- `--bg-primary`: `#030303` (deep black canvas)
- `--bg-secondary`: `#0B0B0D` (panel container background)
- `--bg-panel-header`: `#111116` (panel top bar background)
- `--bg-panel-active`: `#17171F` (focused/hovered panel background)

### Typography Colors
- `--text-primary`: `#F5F7FA` (high-contrast off-white)
- `--text-secondary`: `#AAB0BD` (neutral secondary gray)
- `--text-muted`: `#686E7A` (disabled/trace labels)

### Borders & Dividers
- `--border-subtle`: `#24242E` (minimalist wireframe lines)
- `--border-focus`: `#3b82f6` (active element focus indicator)

### Semantic Accent Colors
- `--accent-cyan`: `#06b6d4` (active model runtime)
- `--accent-green`: `#10b981` (pass / go / compliance validation success)
- `--accent-amber`: `#f59e0b` (warning / human approval required)
- `--accent-red`: `#ef4444` (fail-closed / blocked / high risk)
- `--accent-violet`: `#8b5cf6` (AI / prompt routing)
- `--accent-blue`: `#3b82f6` (planning / research)

## Typography Tokens
- `--font-sans`: `'Outfit', 'Inter', -apple-system, sans-serif`
- `--font-mono`: `'SFMono-Regular', Consolas, 'Liberation Mono', monospace`
- `--font-size-xs`: `11px` (telemetry labels, heartbeats)
- `--font-size-sm`: `12px` (secondary data, lists)
- `--font-size-base`: `14px` (body copy, card details)
- `--font-size-lg`: `16px` (card headers)
- `--font-size-xl`: `20px` (panel headers)
- `--font-size-xxl`: `32px` (North Star metrics)

## Layout & Spacing
- `--spacing-xs`: `4px`
- `--spacing-sm`: `8px`
- `--spacing-md`: `16px`
- `--spacing-lg`: `24px`
- `--border-radius-sm`: `4px` (badges, pills)
- `--border-radius-md`: `8px` (cards, panels)

## Glassmorphic Tokens
- `--bg-glass`: `rgba(11, 11, 22, 0.4)`
- `--border-glass`: `rgba(36, 36, 46, 0.5)`
- `--backdrop-blur`: `blur(12px)`
