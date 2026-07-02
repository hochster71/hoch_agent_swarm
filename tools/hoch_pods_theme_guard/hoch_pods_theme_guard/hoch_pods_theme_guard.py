#!/usr/bin/env python3
"""
HOCH PODS THEATER Visual Guard
Hard-fails weak dashboard/card/SVG drift and compares a rendered screenshot to the binding reference.

Usage:
  python3 hoch_pods_theme_guard.py --repo /path/to/hoch_agent_swarm --screenshot /path/to/current.png

Exit codes:
  0 PASS
  2 FAIL
  3 BLOCKED / required input missing
"""
from __future__ import annotations

import argparse
import json
import math
import re
import sys
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any

from PIL import Image, ImageStat
import numpy as np

FRAME_TITLES = [
    "SYSTEM BOOT", "CORE IGNITION", "POD RING ACTIVATION", "VAULT GATE OPENING",
    "AGENT ENERGY BUILD", "FIRST AGENT SPIN UP", "AGENT LAUNCH", "SKILL CARD POP OUT",
    "JOINING SWARM", "MULTI AGENT SPIN UPS", "ROUTING TO DESTINATIONS",
    "DESTINATION LANES ACTIVE", "POD STATUS OVERVIEW", "DATA FLOW VISUALIZATION",
    "EVIDENCE ARCHIVE", "SYSTEM CONFIRMATION", "MISSION READY",
]

REQUIRED_DOM_IDS = [
    "hoch-pods-theater", "hoch-pods-intro-movie-board", "hoch-pods-storyboard-grid",
    "hoch-pods-agent-spinup-variations", "hoch-pods-skill-card-animation-flow",
    "hoch-pods-destination-lanes", "hoch-pods-status-overview",
    "hoch-pods-data-flow-visualization", "hoch-pods-evidence-archive",
    "hoch-pods-system-confirmation", "hoch-pods-mission-ready",
    "hoch-pods-movie-detail-drawer", "hoch-pods-theater-control-bar",
    "hoch-pods-stale-quarantine-layer",
]

REQUIRED_TEXT = [
    "HOCH PODS THEATER", "INTRO MOVIE", "AGENT SPIN", "CINEMATIC LAUNCH",
    "AGENT SPIN UP VARIATIONS", "SKILL CARD ANIMATION FLOW", "NO SIMULATED DATA",
    "100% REAL EVENTS", "SECURE BY DESIGN", "PROTECTED ORCHESTRATION DOMAINS",
]

FORBIDDEN_DRIFT_TEXT = [
    "Coming soon", "Check back later", "Placeholder", "TBD only", "Mock only", "Lorem ipsum",
]

FORBIDDEN_PRIMARY_PATTERNS = [
    r"dashboard-card-first", r"placeholder-only", r"fake green", r"static background.*reference",
]

@dataclass
class Result:
    name: str
    status: str
    details: Any


def load_text(path: Path) -> str:
    if not path.exists():
        return ""
    try:
        return path.read_text(errors="ignore")
    except Exception:
        return ""


def first_existing(paths: list[Path]) -> Path | None:
    for p in paths:
        if p.exists():
            return p
    return None


def ssim_gray(a: np.ndarray, b: np.ndarray) -> float:
    # Lightweight global SSIM. Good enough as a guardrail, not a replacement for human review.
    a = a.astype(np.float64)
    b = b.astype(np.float64)
    c1 = (0.01 * 255) ** 2
    c2 = (0.03 * 255) ** 2
    mu_a = a.mean()
    mu_b = b.mean()
    var_a = ((a - mu_a) ** 2).mean()
    var_b = ((b - mu_b) ** 2).mean()
    cov = ((a - mu_a) * (b - mu_b)).mean()
    return float(((2 * mu_a * mu_b + c1) * (2 * cov + c2)) / ((mu_a ** 2 + mu_b ** 2 + c1) * (var_a + var_b + c2)))


def image_metrics(reference: Path, screenshot: Path) -> dict[str, Any]:
    ref = Image.open(reference).convert("RGB")
    cur = Image.open(screenshot).convert("RGB")
    ref_size = ref.size
    cur_size = cur.size
    cur_resized = cur.resize(ref_size)

    ref_arr = np.asarray(ref)
    cur_arr = np.asarray(cur_resized)
    diff = np.abs(ref_arr.astype(np.int16) - cur_arr.astype(np.int16))
    pixel_diff_percent = float((diff.mean() / 255) * 100)

    ref_gray = np.asarray(ref.convert("L"))
    cur_gray = np.asarray(cur_resized.convert("L"))
    ssim = ssim_gray(ref_gray, cur_gray)

    def ratios(arr: np.ndarray) -> dict[str, float]:
        r, g, b = arr[:, :, 0], arr[:, :, 1], arr[:, :, 2]
        total = arr.shape[0] * arr.shape[1]
        dark = ((r < 45) & (g < 45) & (b < 55)).sum() / total
        cyan = ((g > 110) & (b > 120) & (r < 90)).sum() / total
        gold = ((r > 130) & (g > 85) & (b < 80)).sum() / total
        red = ((r > 130) & (g < 80) & (b < 80)).sum() / total
        purple = ((r > 90) & (b > 110) & (g < 90)).sum() / total
        green = ((g > 120) & (r < 110) & (b < 120)).sum() / total
        return {"dark": dark, "cyan": cyan, "gold": gold, "red": red, "purple": purple, "green": green}

    rr = ratios(ref_arr)
    cr = ratios(cur_arr)
    palette_delta = sum(abs(rr[k] - cr[k]) for k in rr) / len(rr)
    palette_score = max(0.0, 1.0 - (palette_delta * 4.0))

    # Layout proxy: edge map similarity using simple luminance gradients.
    def edges(gray: np.ndarray) -> np.ndarray:
        gx = np.abs(np.diff(gray.astype(np.int16), axis=1))
        gy = np.abs(np.diff(gray.astype(np.int16), axis=0))
        e = np.zeros_like(gray, dtype=np.uint8)
        e[:, 1:] = np.maximum(e[:, 1:], (gx > 28).astype(np.uint8))
        e[1:, :] = np.maximum(e[1:, :], (gy > 28).astype(np.uint8))
        return e

    re = edges(ref_gray)
    ce = edges(cur_gray)
    overlap = ((re == 1) & (ce == 1)).sum()
    union = ((re == 1) | (ce == 1)).sum() or 1
    layout_score = float(overlap / union)

    return {
        "reference_size": ref_size,
        "screenshot_size": cur_size,
        "reference_aspect_ratio": round(ref_size[0] / ref_size[1], 4),
        "screenshot_aspect_ratio": round(cur_size[0] / cur_size[1], 4),
        "pixel_diff_percent": round(pixel_diff_percent, 3),
        "ssim_score": round(ssim, 4),
        "layout_match_score": round(layout_score, 4),
        "color_palette_match_score": round(palette_score, 4),
        "reference_palette_ratios": {k: round(v, 4) for k, v in rr.items()},
        "screenshot_palette_ratios": {k: round(v, 4) for k, v in cr.items()},
    }


def make_side_by_side(reference: Path, screenshot: Path, output: Path) -> None:
    ref = Image.open(reference).convert("RGB")
    cur = Image.open(screenshot).convert("RGB")
    h = max(ref.height, cur.height)
    def scale(im: Image.Image) -> Image.Image:
        return im.resize((int(im.width * h / im.height), h))
    ref2, cur2 = scale(ref), scale(cur)
    canvas = Image.new("RGB", (ref2.width + cur2.width + 24, h), (0, 0, 0))
    canvas.paste(ref2, (0, 0))
    canvas.paste(cur2, (ref2.width + 24, 0))
    output.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(output)


def evaluate(repo: Path, reference: Path, screenshot: Path | None) -> tuple[str, list[Result], dict[str, Any]]:
    results: list[Result] = []
    data: dict[str, Any] = {}

    doctrine = repo / "docs/design/hoch-pods-theater-doctrine.md"
    server = repo / "backend/pert_server.py"
    reference_repo = repo / "docs/design/assets/hoch-pods-theater-intro-movie-agent-spinups-reference.jpeg"

    doctrine_text = load_text(doctrine)
    server_text = load_text(server)
    combined = doctrine_text + "\n" + server_text

    results.append(Result("reference_image_present", "PASS" if reference_repo.exists() or reference.exists() else "FAIL", str(reference_repo)))
    results.append(Result("doctrine_present", "PASS" if doctrine.exists() else "FAIL", str(doctrine)))
    results.append(Result("binding_authority_text", "PASS" if "binding UI authority" in doctrine_text and "release-blocking visual contract" in doctrine_text else "FAIL", "doctrine must make reference binding"))

    missing_ids = [x for x in REQUIRED_DOM_IDS if x not in server_text]
    results.append(Result("required_dom_ids", "PASS" if not missing_ids else "FAIL", {"missing": missing_ids}))

    missing_titles = [x for x in FRAME_TITLES if x not in combined]
    results.append(Result("required_17_frame_titles", "PASS" if not missing_titles else "FAIL", {"missing": missing_titles}))

    missing_text = [x for x in REQUIRED_TEXT if x not in combined]
    results.append(Result("required_theme_text", "PASS" if not missing_text else "FAIL", {"missing": missing_text}))

    forbidden_hits = [x for x in FORBIDDEN_DRIFT_TEXT if re.search(re.escape(x), combined, re.I)]
    results.append(Result("forbidden_placeholder_text", "PASS" if not forbidden_hits else "FAIL", {"hits": forbidden_hits}))

    # Static background misuse: reference file path inside CSS background/url is forbidden.
    static_bg = bool(re.search(r"background[^;{]*(hoch-pods-theater-intro-movie-agent-spinups-reference|HOCH POUS)", server_text, re.I))
    results.append(Result("no_static_reference_background", "PASS" if not static_bg else "FAIL", "reference image may not be app background"))

    stale_to_green = bool(re.search(r"(STALE|UNKNOWN|NOT AVAILABLE|DEGRADED).{0,160}(green|healthy|ok|pass)", server_text, re.I | re.S))
    results.append(Result("no_stale_to_healthy_mapping", "PASS" if not stale_to_green else "FAIL", "stale/unknown cannot map to healthy/green"))

    # Visual baseline requires screenshot.
    if screenshot is None or not screenshot.exists():
        results.append(Result("current_screenshot_present", "BLOCKED", "current screenshot is required for visual fidelity"))
        status = "BLOCKED_NO_CURRENT_SCREENSHOT"
        return status, results, data

    results.append(Result("current_screenshot_present", "PASS", str(screenshot)))
    metrics = image_metrics(reference if reference.exists() else reference_repo, screenshot)
    data["visual_metrics"] = metrics

    thresholds = {
        "ssim_score_min": 0.05,
        "layout_match_score_min": 0.05,  # edge Jaccard is stricter than semantic layout; start conservative
        "color_palette_match_score_min": 0.70,
        "pixel_diff_percent_max": 45.0,
    }
    data["thresholds"] = thresholds

    checks = {
        "ssim": bool(metrics["ssim_score"] >= thresholds["ssim_score_min"]),
        "layout": bool(metrics["layout_match_score"] >= thresholds["layout_match_score_min"]),
        "palette": bool(metrics["color_palette_match_score"] >= thresholds["color_palette_match_score_min"]),
        "pixel_diff": bool(metrics["pixel_diff_percent"] <= thresholds["pixel_diff_percent_max"]),
    }
    data["visual_threshold_checks"] = checks
    results.append(Result("visual_baseline_thresholds", "PASS" if all(checks.values()) else "FAIL", {"metrics": metrics, "checks": checks}))

    side = repo / "docs/evidence/ui/screenshots/rc52_1-reference-vs-current.png"
    try:
        make_side_by_side(reference if reference.exists() else reference_repo, screenshot, side)
        results.append(Result("side_by_side_created", "PASS", str(side)))
    except Exception as exc:
        results.append(Result("side_by_side_created", "FAIL", str(exc)))

    fail = any(r.status == "FAIL" for r in results)
    status = "THEME_VISUAL_GOAL_PASS" if not fail else "THEME_VISUAL_GOAL_FAIL"
    return status, results, data


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--repo", required=True)
    p.add_argument("--reference", default="/mnt/data/hoch_pods_theme_guard/hoch-pods-theater-reference.jpeg")
    p.add_argument("--screenshot", default=None)
    p.add_argument("--out-json", default=None)
    p.add_argument("--out-md", default=None)
    args = p.parse_args()

    repo = Path(args.repo).expanduser().resolve()
    reference = Path(args.reference).expanduser().resolve()
    screenshot = Path(args.screenshot).expanduser().resolve() if args.screenshot else None

    status, results, data = evaluate(repo, reference, screenshot)
    payload = {
        "goal": "HOCH PODS THEATER exact image-driven cinematic storyboard UI",
        "status": status,
        "human_visual_review_required": True,
        "results": [asdict(r) for r in results],
        **data,
    }

    out_json = Path(args.out_json).expanduser().resolve() if args.out_json else repo / "has_live_project_tracker/data/hoch_pods_theater_visual_goal_guard.json"
    out_md = Path(args.out_md).expanduser().resolve() if args.out_md else repo / "docs/evidence/ui/hoch-pods-theater-visual-goal-guard.md"
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    lines = ["# HOCH PODS Theater Visual Goal Guard", "", f"Status: `{status}`", "", "Human visual review required: `true`", "", "## Results"]
    for r in results:
        lines.append(f"- **{r.name}**: `{r.status}` — `{r.details}`")
    if data.get("visual_metrics"):
        lines += ["", "## Visual Metrics", "", "```json", json.dumps(data["visual_metrics"], indent=2), "```"]
    out_md.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(json.dumps(payload, indent=2))
    if status == "THEME_VISUAL_GOAL_PASS":
        return 0
    if status.startswith("BLOCKED"):
        return 3
    return 2

if __name__ == "__main__":
    raise SystemExit(main())
