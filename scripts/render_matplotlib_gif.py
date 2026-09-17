#!/usr/bin/env python3
"""Rotating GIF of examples/sample_pcd_3000.ply as shaded matplotlib circles —
a "standard viewer" stand-in that leans as close to Bead Lab's bead look as a
flat 2D marker can get: per-point normals (estimated the same way Bead Lab
estimates them) lit with a simple Lambertian model, at roughly the same bead
size and color as the reference preset. Real per-vertex-lit sphere geometry
is out of reach for matplotlib's 3D toolkit — see render_open3d_gif.py for
that — but the shading gradient reads much more like beads than flat dots.

Usage:
  pip install numpy scipy matplotlib pillow
  python3 scripts/render_matplotlib_gif.py
"""
import io
import math

import matplotlib.pyplot as plt
import numpy as np
from PIL import Image

from _pointcloud import (
    BEAD_COLOR,
    BEAD_RADIUS,
    ROOT,
    camera_basis,
    estimate_normals,
    lambert_shade,
    load_reference_cloud,
    save_gif,
)

OUT_PATH = ROOT / "docs" / "images" / "compare_matplotlib.gif"
FRAMES = 36
DURATION_MS = 70
SIZE_IN = 3.2
DPI = 150
CANVAS_PX = SIZE_IN * DPI
DATA_SPAN = 2.1  # xlim/ylim is (-1.05, 1.05)

# Convert a bead radius in normalized-cloud units to a matplotlib scatter
# marker size (points**2, where diameter in points ~= sqrt(s)).
_px_per_unit = CANVAS_PX / DATA_SPAN
_px_per_pt = DPI / 72
_bead_diam_pt = (2 * BEAD_RADIUS * _px_per_unit) / _px_per_pt
MARKER_SIZE = _bead_diam_pt ** 2


def render_frame(p, colors, theta, phi, dist):
    right, true_up, forward = camera_basis(theta, phi, dist)
    sx, sy, depth = p @ right, p @ true_up, p @ forward
    order = np.argsort(-depth)  # farthest first, so nearer beads draw on top

    fig, ax = plt.subplots(figsize=(SIZE_IN, SIZE_IN), dpi=DPI)
    ax.scatter(sx[order], sy[order], s=MARKER_SIZE, c=colors[order], linewidths=0)
    ax.set_xlim(-1.05, 1.05)
    ax.set_ylim(-1.05, 1.05)
    ax.set_aspect("equal")
    ax.axis("off")
    fig.patch.set_facecolor("white")
    fig.tight_layout(pad=0)
    buf = io.BytesIO()
    fig.savefig(buf, format="png", facecolor="white")
    plt.close(fig)
    buf.seek(0)
    return Image.open(buf).convert("RGB")


def main():
    p, theta0, phi, dist = load_reference_cloud()
    normals = estimate_normals(p)
    brightness = lambert_shade(normals)
    colors = np.clip(np.outer(brightness, BEAD_COLOR), 0, 1)

    frames = [
        render_frame(p, colors, theta0 + 2 * math.pi * i / FRAMES, phi, dist)
        for i in range(FRAMES)
    ]
    save_gif(frames, OUT_PATH, DURATION_MS)
    print(f"wrote {OUT_PATH} ({len(frames)} frames)")


if __name__ == "__main__":
    main()
