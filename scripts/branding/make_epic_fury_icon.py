"""Generate the Epic Fury 2026 app icon — original design, reproducible.

An electric indigo->magenta->orange gradient with a padded lightning "fury" mark and a
soft energy ring. Emits the 1024 App Store master (RGB, NO alpha, as Apple requires),
a drop-in AppIcon.appiconset (Xcode 14+ single-size universal), and the classic iOS
raster sizes. Run: .venv/bin/python3 scripts/branding/make_epic_fury_icon.py
"""
from __future__ import annotations
import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter

OUT = Path(__file__).resolve().parents[2] / "docs" / "products" / "epic-fury-2026" / "appicon"
S = 2048


def _lerp(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def render() -> Image.Image:
    img = Image.new("RGB", (S, S)); px = img.load()
    c0, c1, c2, c3 = (12, 7, 36), (72, 20, 138), (198, 36, 112), (255, 126, 44)
    for y in range(S):
        for x in range(S):
            t = (x / S) * 0.5 + (y / S) * 0.5
            if t < 0.5:      col = _lerp(c0, c1, t / 0.5)
            elif t < 0.82:   col = _lerp(c1, c2, (t - 0.5) / 0.32)
            else:            col = _lerp(c2, c3, (t - 0.82) / 0.18)
            px[x, y] = col
    glow = Image.new("L", (S, S), 0)
    ImageDraw.Draw(glow).ellipse([S*0.2, S*0.16, S*0.8, S*0.84], fill=100)
    glow = glow.filter(ImageFilter.GaussianBlur(S*0.16))
    img = Image.composite(Image.new("RGB", (S, S), (255, 196, 128)), img, glow.point(lambda v: int(v*0.45)))
    ring = Image.new("L", (S, S), 0)
    ImageDraw.Draw(ring).ellipse([S*0.205, S*0.205, S*0.795, S*0.795], outline=255, width=int(S*0.014))
    ring = ring.filter(ImageFilter.GaussianBlur(S*0.004))
    img = Image.composite(Image.new("RGB", (S, S), (255, 236, 196)), img, ring.point(lambda v: int(v*0.55)))
    cx, cy, k = S*0.5, S*0.5, S*0.163
    bolt = [(cx+0.10*k, cy-2.05*k), (cx-0.95*k, cy+0.15*k), (cx-0.12*k, cy+0.10*k),
            (cx-0.55*k, cy+2.05*k), (cx+1.02*k, cy-0.35*k), (cx+0.12*k, cy-0.30*k), (cx+0.72*k, cy-2.05*k)]
    gl = Image.new("L", (S, S), 0); ImageDraw.Draw(gl).polygon(bolt, fill=255)
    gl = gl.filter(ImageFilter.GaussianBlur(S*0.022))
    img = Image.composite(Image.new("RGB", (S, S), (255, 232, 168)), img, gl.point(lambda v: int(v*0.55)))
    d = ImageDraw.Draw(img, "RGBA")
    d.polygon(bolt, fill=(255, 244, 220, 255))
    d.line(bolt + [bolt[0]], fill=(255, 150, 44, 200), width=int(S*0.0055), joint="curve")
    return img


# (size_px, filename) — common iOS set; Xcode 14+ needs only the 1024 universal.
IOS_SIZES = [1024, 180, 167, 152, 120, 87, 80, 76, 60, 58, 40, 29, 20]


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    aset = OUT / "AppIcon.appiconset"; aset.mkdir(exist_ok=True)
    master = render()
    # App Store master (flatten to RGB, strip any alpha — Apple rejects alpha)
    appstore = master.resize((1024, 1024), Image.LANCZOS).convert("RGB")
    appstore.save(OUT / "EpicFury2026_AppStore_1024.png", "PNG")
    appstore.save(aset / "icon_1024.png", "PNG")
    for s in IOS_SIZES:
        master.resize((s, s), Image.LANCZOS).convert("RGB").save(aset / f"icon_{s}.png", "PNG")
    (aset / "Contents.json").write_text(json.dumps({
        "images": [{"filename": "icon_1024.png", "idiom": "universal",
                    "platform": "ios", "size": "1024x1024"}],
        "info": {"author": "helm", "version": 1},
    }, indent=2))
    print(f"wrote App Store 1024 + AppIcon.appiconset ({len(IOS_SIZES)} sizes) to {OUT}")


if __name__ == "__main__":
    main()
