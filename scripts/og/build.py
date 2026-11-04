"""Build assets/unthinkable-og-equations.png, the share image.

The lettering of assets/unthinkable-og.png, with every post in posts.json packed around it in the
pen font, each equation once, none overlapping. Rebuild it when the feed has grown:

    NODE_PATH=<a node_modules with playwright> python3 scripts/og/build.py

Needs Pillow, and Playwright for node with its Chromium installed.
"""
import json
import subprocess
import tempfile
from pathlib import Path

from PIL import Image, ImageFilter

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
LETTERING = ROOT / "assets" / "unthinkable-og.png"
OUT = ROOT / "assets" / "unthinkable-og-equations.png"
HALO = 14   # px of white kept around every pen stroke of the lettering
CELL = 2    # px per cell of the packing grid
# K: CSS px per output px (no font drops below Chrome's floor); tiers: how many posts get the
# big, mid and small sizes, the rest are fine; minLine: thinnest pen line, in output px.
OPTS = {"K": 3, "pad": 1, "noise": 0.08, "iters": 11, "tiers": [12, 80, 220],
        "big": 2.4, "mid": 1.6, "small": 1.15, "fine": 0.9,
        "inkLo": 0.8, "inkHi": 1, "minLine": 0.5}


def lift(path):
    """The lettering as an ink layer, and the grid of cells the equations must keep out of."""
    src = Image.open(path).convert("L")
    w, h = src.size
    alpha = src.point(lambda v: 0 if v >= 250 else min(255, int((250 - v) * 255 / 250 * 1.15)))
    letters = Image.new("RGBA", (w, h), (20, 20, 20, 0))
    letters.putalpha(alpha)
    halo, grow = src.point(lambda v: 255 if v < 200 else 0), HALO
    while grow > 0:
        step = min(grow, 7)
        halo = halo.filter(ImageFilter.MaxFilter(2 * step + 1))
        grow -= step
    gw, gh = w // CELL, h // CELL
    small = halo.resize((gw, gh), Image.BOX)
    bits = "".join("1" if small.getpixel((x, y)) else "0" for y in range(gh) for x in range(gw))
    return letters, {"cell": CELL, "w": gw, "h": gh, "bits": bits}


def main():
    letters, obstacle = lift(LETTERING)
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        (tmp / "obstacle.json").write_text(json.dumps(obstacle))
        opts = {**OPTS, "posts": str(ROOT / "posts.json"), "obstacle": str(tmp / "obstacle.json"),
                "page": str(HERE / "og.html"), "out": str(tmp / "raw.png")}
        subprocess.run(["node", str(HERE / "render.cjs"), json.dumps(opts)], check=True)
        card = Image.open(tmp / "raw.png").convert("RGB").resize(letters.size, Image.LANCZOS)
    card.paste(letters, (0, 0), letters)
    card.convert("L").save(OUT, optimize=True)
    print(f"{OUT.relative_to(ROOT)}: {OUT.stat().st_size // 1024} KB")


if __name__ == "__main__":
    main()
