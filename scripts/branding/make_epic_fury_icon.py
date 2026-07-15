"""Generate the Epic Fury 2026 app icon — original, on-brief, reproducible.

Epic Fury 2026 is a dark-mode, military HUD-style tactical intelligence dashboard, so the
icon is a tactical targeting-reticle / radar scope: range rings, a radar sweep, a crosshair
with range ticks, agent "blips", a center target-lock, and an inset HUD frame — amber on
near-black. Emits the 1024 App Store master (RGB, NO alpha), a drop-in AppIcon.appiconset,
and the classic iOS raster sizes.

Run: .venv/bin/python3 scripts/branding/make_epic_fury_icon.py
"""
from __future__ import annotations
import json
import math
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter

OUT = Path(__file__).resolve().parents[2] / "docs" / "products" / "epic-fury-2026" / "appicon"
S = 2048
AMBER = (255, 163, 44)
AMBER_HOT = (255, 209, 128)


def render() -> Image.Image:
    img = Image.new("RGB", (S, S)); px = img.load()
    cx = cy = S / 2; maxd = math.hypot(cx, cy)
    for y in range(S):                     # dark tactical vignette
        for x in range(S):
            t = min(1, (math.hypot(x - cx, y - cy) / maxd) * 1.15)
            base, edge = (18, 23, 31), (5, 7, 11)
            px[x, y] = tuple(int(base[i] + (edge[i] - base[i]) * t) for i in range(3))
    ov = Image.new("RGBA", (S, S), (0, 0, 0, 0)); d = ImageDraw.Draw(ov)
    step = int(S / 14)                     # faint grid
    for i in range(0, S, step):
        d.line([(i, 0), (i, S)], fill=(*AMBER, 16), width=2)
        d.line([(0, i), (S, i)], fill=(*AMBER, 16), width=2)
    for r in (0.37, 0.27, 0.165):          # range rings
        rr = S * r
        d.ellipse([cx - rr, cy - rr, cx + rr, cy + rr], outline=(*AMBER, 140), width=int(S * 0.0035))
    sweep = Image.new("RGBA", (S, S), (0, 0, 0, 0)); sd = ImageDraw.Draw(sweep)
    R, a0 = S * 0.37, -58                   # radar sweep, bright leading edge -> fade
    for j in range(70):
        sd.pieslice([cx - R, cy - R, cx + R, cy + R], a0 - j, a0 - j + 2, fill=(*AMBER, int(70 * (1 - j / 70))))
    lead = math.radians(a0 + 2)
    sd.line([(cx, cy), (cx + R * math.cos(lead), cy + R * math.sin(lead))], fill=(*AMBER_HOT, 220), width=int(S * 0.006))
    ov = Image.alpha_composite(ov, sweep); d = ImageDraw.Draw(ov)
    gap, ext, w = S * 0.05, S * 0.40, int(S * 0.004)   # crosshair + ticks
    for dx, dy in [(1, 0), (-1, 0), (0, 1), (0, -1)]:
        d.line([(cx + dx * gap, cy + dy * gap), (cx + dx * ext, cy + dy * ext)], fill=(*AMBER, 200), width=w)
    for t in range(1, 5):
        off, tk = S * 0.075 * t, S * 0.018
        d.line([(cx + off, cy - tk), (cx + off, cy + tk)], fill=(*AMBER, 180), width=w)
        d.line([(cx - off, cy - tk), (cx - off, cy + tk)], fill=(*AMBER, 180), width=w)
        d.line([(cx - tk, cy + off), (cx + tk, cy + off)], fill=(*AMBER, 180), width=w)
        d.line([(cx - tk, cy - off), (cx + tk, cy - off)], fill=(*AMBER, 180), width=w)
    b, arm, bw = S * 0.075, S * 0.035, int(S * 0.007)   # center target-lock brackets
    for sx in (-1, 1):
        for sy in (-1, 1):
            X, Y = cx + sx * b, cy + sy * b
            d.line([(X, Y), (X - sx * arm, Y)], fill=(*AMBER_HOT, 255), width=bw)
            d.line([(X, Y), (X, Y - sy * arm)], fill=(*AMBER_HOT, 255), width=bw)
    d.ellipse([cx - S * 0.012, cy - S * 0.012, cx + S * 0.012, cy + S * 0.012], fill=(*AMBER_HOT, 255))
    for ang, rad in [(200, 0.27), (320, 0.37), (120, 0.165), (35, 0.27), (255, 0.37)]:   # agent blips
        rr = S * rad; bx, by = cx + rr * math.cos(math.radians(ang)), cy + rr * math.sin(math.radians(ang))
        d.ellipse([bx - S * 0.011, by - S * 0.011, bx + S * 0.011, by + S * 0.011], fill=(*AMBER_HOT, 255))
    m, L, cwd = S * 0.125, S * 0.085, int(S * 0.008)   # HUD frame — INSET so Apple's corner rounding won't clip it
    for ox, oy, sx, sy in [(m, m, 1, 1), (S - m, m, -1, 1), (m, S - m, 1, -1), (S - m, S - m, -1, -1)]:
        d.line([(ox, oy), (ox + sx * L, oy)], fill=(*AMBER, 230), width=cwd)
        d.line([(ox, oy), (ox, oy + sy * L)], fill=(*AMBER, 230), width=cwd)
    glow = ov.split()[3].filter(ImageFilter.GaussianBlur(S * 0.012))   # amber glow pass
    base = Image.alpha_composite(img.convert("RGBA"), ov).convert("RGB")
    base = Image.composite(Image.new("RGB", (S, S), AMBER), base, glow.point(lambda v: int(v * 0.28)))
    return Image.alpha_composite(base.convert("RGBA"), ov).convert("RGB")


IOS_SIZES = [1024, 180, 167, 152, 120, 87, 80, 76, 60, 58, 40, 29, 20]


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    aset = OUT / "AppIcon.appiconset"; aset.mkdir(exist_ok=True)
    master = render()
    appstore = master.resize((1024, 1024), Image.LANCZOS).convert("RGB")  # no alpha
    appstore.save(OUT / "EpicFury2026_AppStore_1024.png", "PNG")
    appstore.save(aset / "icon_1024.png", "PNG")
    for s in IOS_SIZES:
        master.resize((s, s), Image.LANCZOS).convert("RGB").save(aset / f"icon_{s}.png", "PNG")
    (aset / "Contents.json").write_text(json.dumps({
        "images": [{"filename": "icon_1024.png", "idiom": "universal", "platform": "ios", "size": "1024x1024"}],
        "info": {"author": "helm", "version": 1},
    }, indent=2))
    print(f"wrote tactical-HUD App Store 1024 + AppIcon.appiconset ({len(IOS_SIZES)} sizes) to {OUT}")


if __name__ == "__main__":
    main()
