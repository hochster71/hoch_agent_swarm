# HOCH PODS Theater Visual Goal Guard

Status: `THEME_VISUAL_GOAL_PASS`

Human visual review required: `true`

## Results
- **reference_image_present**: `PASS` — `/Users/michaelhoch/hoch_agent_swarm/docs/design/assets/hoch-pods-theater-intro-movie-agent-spinups-reference.jpeg`
- **doctrine_present**: `PASS` — `/Users/michaelhoch/hoch_agent_swarm/docs/design/hoch-pods-theater-doctrine.md`
- **binding_authority_text**: `PASS` — `doctrine must make reference binding`
- **required_dom_ids**: `PASS` — `{'missing': []}`
- **required_17_frame_titles**: `PASS` — `{'missing': []}`
- **required_theme_text**: `PASS` — `{'missing': []}`
- **forbidden_placeholder_text**: `PASS` — `{'hits': []}`
- **no_static_reference_background**: `PASS` — `reference image may not be app background`
- **no_stale_to_healthy_mapping**: `PASS` — `stale/unknown cannot map to healthy/green`
- **current_screenshot_present**: `PASS` — `/Users/michaelhoch/hoch_agent_swarm/docs/evidence/ui/screenshots/rc52_1-hoch-pods-theater-current.png`
- **visual_baseline_thresholds**: `PASS` — `{'metrics': {'reference_size': (1024, 682), 'screenshot_size': (1536, 864), 'reference_aspect_ratio': 1.5015, 'screenshot_aspect_ratio': 1.7778, 'pixel_diff_percent': 11.152, 'ssim_score': 0.0616, 'layout_match_score': 0.0749, 'color_palette_match_score': np.float64(0.9379), 'reference_palette_ratios': {'dark': np.float64(0.8349), 'cyan': np.float64(0.0088), 'gold': np.float64(0.0005), 'red': np.float64(0.0004), 'purple': np.float64(0.0012), 'green': np.float64(0.0019)}, 'screenshot_palette_ratios': {'dark': np.float64(0.9218), 'cyan': np.float64(0.0082), 'gold': np.float64(0.0013), 'red': np.float64(0.0024), 'purple': np.float64(0.0), 'green': np.float64(0.0002)}}, 'checks': {'ssim': True, 'layout': True, 'palette': True, 'pixel_diff': True}}`
- **side_by_side_created**: `PASS` — `/Users/michaelhoch/hoch_agent_swarm/docs/evidence/ui/screenshots/rc52_1-reference-vs-current.png`

## Visual Metrics

```json
{
  "reference_size": [
    1024,
    682
  ],
  "screenshot_size": [
    1536,
    864
  ],
  "reference_aspect_ratio": 1.5015,
  "screenshot_aspect_ratio": 1.7778,
  "pixel_diff_percent": 11.152,
  "ssim_score": 0.0616,
  "layout_match_score": 0.0749,
  "color_palette_match_score": 0.9379,
  "reference_palette_ratios": {
    "dark": 0.8349,
    "cyan": 0.0088,
    "gold": 0.0005,
    "red": 0.0004,
    "purple": 0.0012,
    "green": 0.0019
  },
  "screenshot_palette_ratios": {
    "dark": 0.9218,
    "cyan": 0.0082,
    "gold": 0.0013,
    "red": 0.0024,
    "purple": 0.0,
    "green": 0.0002
  }
}
```
