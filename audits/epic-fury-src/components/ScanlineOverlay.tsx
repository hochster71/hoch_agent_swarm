/**
 * ScanlineOverlay — pure CSS HUD effect, zero JS overhead.
 * Rendered as a fixed overlay above all content.
 */
export function ScanlineOverlay() {
  return (
    <>
      {/* Subtle repeating horizontal lines */}
      <div className="hud-scanlines" aria-hidden="true" />
      {/* Moving scan beam */}
      <div className="hud-scanline-beam" aria-hidden="true" />
      {/* Radial vignette */}
      <div className="hud-vignette" aria-hidden="true" />
    </>
  )
}
