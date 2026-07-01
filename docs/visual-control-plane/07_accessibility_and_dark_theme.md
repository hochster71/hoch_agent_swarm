# Accessibility and Dark Theme Compliance

This document defines the accessibility constraints and dark-theme rendering standards.

## Dark Theme Styling Doctrine
Naively inverting colors is prohibited. We enforce a curated palette that preserves visual clarity:
- **Background Contrast**: Backgrounds must be pure black (`#030303`) or deep slate (`#0b0b0d`) to prevent backlight glare.
- **Text Readability**: Text must use high-contrast grey-whites (`#F5F7FA`) rather than bright pure white (`#FFFFFF`) to reduce eye strain, while ensuring a contrast ratio of at least `4.5:1` against panel backgrounds.
- **Accents**: Accent colors (cyan, violet, green) must maintain appropriate luminance to remain visible against dark panels.

## WCAG Accessibility Controls

### 1. Non-Color Meaning
State and severity must never be communicated using color alone:
- **Pass/Go**: Green color + checkmark icon (`✓`) + text label `PASS`.
- **Warning/Approval**: Amber color + alert icon (`⚠`) + text label `PENDING`.
- **Fail-Closed**: Red color + block icon (`🛑`) + text label `FAIL-CLOSED`.
- **Offline**: Muted gray + moon icon (`☾`) + text label `OFFLINE`.

### 2. Keyboard Navigation
Users must be able to navigate the entire control plane using the keyboard:
- All interactive controls (pills, cards, buttons) must have a logical `tabindex`.
- The focus indicator must be explicitly styled (`outline: 2px solid var(--border-focus)`) with a focus-ring offset.

### 3. Screen Reader Support
- Interactive elements must possess explicit `aria-label` or `aria-describedby` tags.
- Telemetry widgets must include `role="status"` or `role="log"` to declare dynamic content updates.

### 4. Reduced-Motion Media Query
We enforce CSS controls to deactivate transitions and animations when requested by the operating system:
```css
@media (prefers-reduced-motion: reduce) {
  * {
    animation-delay: -1ms !important;
    animation-duration: 1ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0s !important;
    scroll-behavior: auto !important;
  }
}
```
