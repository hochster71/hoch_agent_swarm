#!/usr/bin/env python3
import os
import sys
from PIL import Image

def main():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ref_path = os.path.join(root, "docs", "design", "assets", "hoch-pods-theater-reference.jpeg")
    cur_path = os.path.join(root, "docs", "evidence", "ui", "screenshots", "hoch-pods-theater-cockpit-current.png")
    out_path = os.path.join(root, "docs", "evidence", "ui", "screenshots", "hoch-pods-theater-reference-vs-current.png")

    if not os.path.exists(ref_path):
        print(f"Error: Reference image not found at {ref_path}")
        sys.exit(1)
    if not os.path.exists(cur_path):
        print(f"Error: Current screenshot not found at {cur_path}")
        sys.exit(1)

    ref = Image.open(ref_path).convert("RGB")
    cur = Image.open(cur_path).convert("RGB")

    # Crop the current cockpit screenshot to isolate the theater panel for comparison if needed, 
    # but since they both match in layout, let's just stitch them side-by-side.
    h = max(ref.height, cur.height)
    def scale(im):
        return im.resize((int(im.width * h / im.height), h))

    ref2 = scale(ref)
    cur2 = scale(cur)

    # Create canvas (with 24px separator)
    canvas = Image.new("RGB", (ref2.width + cur2.width + 24, h), (0, 0, 0))
    canvas.paste(ref2, (0, 0))
    canvas.paste(cur2, (ref2.width + 24, 0))

    # Save
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    canvas.save(out_path)
    print(f"Stitched side-by-side saved to: {out_path}")

if __name__ == "__main__":
    main()
