# HOCH PODS Theater Visual Goal Guard

Status: `THEME_VISUAL_GOAL_PASS`

Human visual review required: `true`

## Results
- **reference_image_present**: `PASS` — `/mnt/data/hoch_pods_theme_guard/selftest_repo/docs/design/assets/hoch-pods-theater-intro-movie-agent-spinups-reference.jpeg`
- **doctrine_present**: `PASS` — `/mnt/data/hoch_pods_theme_guard/selftest_repo/docs/design/hoch-pods-theater-doctrine.md`
- **binding_authority_text**: `PASS` — `doctrine must make reference binding`
- **required_dom_ids**: `PASS` — `{'missing': []}`
- **required_17_frame_titles**: `PASS` — `{'missing': []}`
- **required_theme_text**: `PASS` — `{'missing': []}`
- **forbidden_placeholder_text**: `PASS` — `{'hits': []}`
- **no_static_reference_background**: `PASS` — `reference image may not be app background`
- **no_stale_to_healthy_mapping**: `PASS` — `stale/unknown cannot map to healthy/green`
- **current_screenshot_present**: `PASS` — `/mnt/data/hoch_pods_theme_guard/selftest_repo/docs/evidence/ui/screenshots/rc52_1-hoch-pods-theater-current.png`
- **visual_baseline_thresholds**: `PASS` — `{'metrics': {'reference_size': (1536, 1024), 'screenshot_size': (1536, 1024), 'reference_aspect_ratio': 1.5, 'screenshot_aspect_ratio': 1.5, 'pixel_diff_percent': 0.0, 'ssim_score': 1.0, 'layout_match_score': 1.0, 'color_palette_match_score': np.float64(1.0), 'reference_palette_ratios': {'dark': np.float64(0.8328), 'cyan': np.float64(0.0047), 'gold': np.float64(0.0038), 'red': np.float64(0.0006), 'purple': np.float64(0.0037), 'green': np.float64(0.0058)}, 'screenshot_palette_ratios': {'dark': np.float64(0.8328), 'cyan': np.float64(0.0047), 'gold': np.float64(0.0038), 'red': np.float64(0.0006), 'purple': np.float64(0.0037), 'green': np.float64(0.0058)}}, 'checks': {'ssim': True, 'layout': True, 'palette': True, 'pixel_diff': True}}`
- **side_by_side_created**: `PASS` — `/mnt/data/hoch_pods_theme_guard/selftest_repo/docs/evidence/ui/screenshots/rc52_1-reference-vs-current.png`

## Visual Metrics

```json
{
  "reference_size": [
    1536,
    1024
  ],
  "screenshot_size": [
    1536,
    1024
  ],
  "reference_aspect_ratio": 1.5,
  "screenshot_aspect_ratio": 1.5,
  "pixel_diff_percent": 0.0,
  "ssim_score": 1.0,
  "layout_match_score": 1.0,
  "color_palette_match_score": 1.0,
  "reference_palette_ratios": {
    "dark": 0.8328,
    "cyan": 0.0047,
    "gold": 0.0038,
    "red": 0.0006,
    "purple": 0.0037,
    "green": 0.0058
  },
  "screenshot_palette_ratios": {
    "dark": 0.8328,
    "cyan": 0.0047,
    "gold": 0.0038,
    "red": 0.0006,
    "purple": 0.0037,
    "green": 0.0058
  }
}
```
