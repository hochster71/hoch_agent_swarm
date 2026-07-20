"""HELM Executive Operations Center — visual reconstruction test.

Captures a 1536x1024 screenshot of the rebuilt /overview and, when the authoritative
reference PNG is present at frontend_live/ref_overview.png, produces a side-by-side and a
per-pixel visual-difference image so the reconstruction can be judged against the spec.

Runs on Michael's machine (needs the live API on https://localhost:8443 and the reference
PNG in place). It is honest by construction: if the reference or server is absent it SKIPS
rather than fabricating a pass.

    pip install playwright pillow --break-system-packages && python -m playwright install chromium
    HELM_BASE=https://localhost:8443 pytest tests/ui/test_overview_visual.py -s

Outputs (under tests/ui/_artifacts/):
    overview_actual.png     — the reconstruction at 1536x1024
    overview_sidebyside.png — reference | actual
    overview_diff.png       — amplified per-pixel difference (only if reference present)
    overview_diff.json      — mean/max diff + % differing pixels
"""
import os, json, pathlib, pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
ART = ROOT / "tests" / "ui" / "_artifacts"; ART.mkdir(parents=True, exist_ok=True)
REF = ROOT / "frontend_live" / "ref_overview.png"
BASE = os.environ.get("HELM_BASE", "https://localhost:8443")
W, H = 1536, 1024


def _shot():
    try:
        from playwright.sync_api import sync_playwright
    except Exception:
        pytest.skip("playwright not installed")
    with sync_playwright() as p:
        b = p.chromium.launch(args=["--ignore-certificate-errors"])
        pg = b.new_context(viewport={"width": W, "height": H},
                           ignore_https_errors=True, device_scale_factor=1).new_page()
        try:
            pg.goto(f"{BASE}/overview", wait_until="networkidle", timeout=15000)
        except Exception as e:
            b.close(); pytest.skip(f"HELM server not reachable at {BASE}: {e}")
        pg.wait_for_timeout(2500)  # let live data + gauges settle
        out = ART / "overview_actual.png"
        pg.screenshot(path=str(out), clip={"x": 0, "y": 0, "width": W, "height": H})
        b.close()
        return out


def test_overview_geometry_and_diff():
    actual = _shot()
    assert actual.exists() and actual.stat().st_size > 5000, "screenshot not captured"
    try:
        from PIL import Image, ImageChops, ImageStat
    except Exception:
        pytest.skip("pillow not installed (screenshot captured, diff skipped)")

    act = Image.open(actual).convert("RGB").resize((W, H))
    if not REF.exists():
        pytest.skip(f"reference PNG absent at {REF} — captured actual only; drop the PNG to enable diff")

    ref = Image.open(REF).convert("RGB").resize((W, H))
    # side-by-side
    sbs = Image.new("RGB", (W * 2 + 20, H), (7, 12, 21))
    sbs.paste(ref, (0, 0)); sbs.paste(act, (W + 20, 0))
    sbs.save(ART / "overview_sidebyside.png")
    # diff
    diff = ImageChops.difference(ref, act)
    diff.point(lambda v: min(255, v * 4)).save(ART / "overview_diff.png")
    stat = ImageStat.Stat(diff)
    mean = sum(stat.mean) / 3.0
    hist = diff.convert("L").histogram()
    differing = sum(hist[16:]) / float(W * H)  # pixels differing beyond a small threshold
    metrics = {"mean_diff": round(mean, 3), "max_diff": max(stat.extrema[i][1] for i in range(3)),
               "pct_pixels_differing": round(differing * 100, 2)}
    (ART / "overview_diff.json").write_text(json.dumps(metrics, indent=2))
    print("VISUAL DIFF:", metrics)
    # geometry sanity: reconstruction should not be wildly off. Not a hard pixel-match gate
    # (fonts/live-data differ), but a gross-layout regression tripwire.
    assert differing < 0.85, f"reconstruction differs from reference on {differing*100:.0f}% of pixels"
