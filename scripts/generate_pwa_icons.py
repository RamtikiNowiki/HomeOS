#!/usr/bin/env python3
"""Generate PNG PWA icons (192, 512, apple-touch) for Chrome install criteria."""
from pathlib import Path

try:
    from PIL import Image, ImageDraw
except ImportError:
    raise SystemExit("Install Pillow first: pip install Pillow")

OUT = Path(__file__).resolve().parents[1] / "app" / "static" / "icons"


def draw_icon(size: int) -> Image.Image:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    pad = size // 16
    radius = size // 5
    # Gradient-ish: indigo top-left → cyan bottom-right via stepped rects
    for i in range(size):
        t = i / max(size - 1, 1)
        r = int(79 + (8 - 79) * t)
        g = int(70 + (145 - 70) * t)
        b = int(229 + (178 - 229) * t)
        draw.line([(0, i), (size, i)], fill=(r, g, b, 255))
    draw.rounded_rectangle([pad, pad, size - pad, size - pad], radius=radius, fill=(79, 70, 229, 255))
    # Simple house glyph
    cx = size // 2
    roof_top = int(size * 0.28)
    roof_w = int(size * 0.36)
    body_top = int(size * 0.42)
    body_bot = int(size * 0.78)
    body_half = int(size * 0.28)
    stroke = max(size // 24, 2)
    white = (255, 255, 255, 240)
    draw.polygon(
        [(cx, roof_top), (cx + roof_w, body_top), (cx - roof_w, body_top)],
        outline=white,
        fill=None,
        width=stroke,
    )
    draw.rectangle(
        [cx - body_half, body_top, cx + body_half, body_bot],
        outline=white,
        width=stroke,
    )
    door_w = int(size * 0.14)
    draw.rectangle(
        [cx - door_w // 2, int(size * 0.58), cx + door_w // 2, body_bot],
        fill=(255, 255, 255, 200),
    )
    return img


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for name, px in [("icon-192.png", 192), ("icon-512.png", 512), ("apple-touch-icon.png", 180)]:
        path = OUT / name
        draw_icon(px).save(path, "PNG")
        print(f"  wrote {path}")
    print("Done.")


if __name__ == "__main__":
    main()
