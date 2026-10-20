#!/usr/bin/env python3
"""Generate the IPL Fantasy PWA icons (run from web/: python3 scripts/generate-pwa-icons.py).

Design: dark-mode ink background (#09090c, from --color-ink-950) with a
trophy-gold (#f59e0b) cricket ball + seam, centered in the safe zone so the
maskable variants survive the OS safe-zone crop. No external assets.
"""
import math
from PIL import Image, ImageDraw

BG = (0x09, 0x09, 0x0C, 255)      # --color-ink-950 (dark theme)
GOLD = (0xF5, 0x9E, 0x0B, 255)    # --color-trophy-gold
SEAM = (0x09, 0x09, 0x0C, 255)    # dark seam on the gold ball


def draw_ball(size: int, maskable: bool) -> Image.Image:
    img = Image.new("RGBA", (size, size), BG)
    d = ImageDraw.Draw(img)
    cx = cy = size // 2
    # Keep the ball inside the maskable safe zone (~80% diameter) when maskable.
    r = int(size * (0.30 if maskable else 0.36))
    # Ball
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=GOLD)
    # Seam: two curved arcs like a cricket ball's stitching.
    w = max(2, size // 128)
    for offset in (-1, 1):
        d.arc(
            [cx - r + offset * w * 4, cy - r, cx + r + offset * w * 4, cy + r],
            start=250, end=110, fill=SEAM, width=w,
        )
    # Subtle highlight ring so the gold pops on dark chrome.
    d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=(255, 255, 255, 40), width=max(1, size // 256))
    return img


for size in (192, 512):
    draw_ball(size, False).save(f"public/icons/icon-{size}.png")
    draw_ball(size, True).save(f"public/icons/maskable-{size}.png")
    print(f"wrote public/icons/icon-{size}.png and maskable-{size}.png")
