#!/usr/bin/env python3
"""Rotating GIF of Bead Lab rendering examples/sample_pcd_3000.ply with the
reference preset (examples/sample_bead_preset.json) — the same shot as
docs/images/bead_render_3000.png, spun through a full turn for comparison
against scripts/render_matplotlib_gif.py and scripts/render_open3d_gif.py.

Drives the real beed_lab.html in a headless browser: loads the PLY through
the file input, imports the preset, then sweeps the "orbit" slider.

Usage:
  pip install playwright pillow
  python3 scripts/render_bead_lab_gif.py
Requires a Chrome/Chromium install (uses Playwright's channel="chrome").
"""
import io
import math

from PIL import Image
from playwright.sync_api import sync_playwright

from _pointcloud import ROOT, load_preset, save_gif

PLY_PATH = ROOT / "examples" / "sample_pcd_3000.ply"
PRESET_PATH = ROOT / "examples" / "sample_bead_preset.json"
OUT_PATH = ROOT / "docs" / "images" / "compare_bead_lab.gif"
FRAMES = 36
DURATION_MS = 70
CANVAS_SIZE = 480
PANEL_WIDTH = 286  # matches #panel { width:286px } in beed_lab.html


def wrap180(deg):
    return ((deg + 180) % 360) - 180


def main():
    _, theta0, _phi, _dist = load_preset()
    cazim0 = wrap180(math.degrees(theta0))

    with sync_playwright() as pw:
        browser = pw.chromium.launch(channel="chrome")
        page = browser.new_page(viewport={"width": CANVAS_SIZE + PANEL_WIDTH, "height": CANVAS_SIZE})
        page.goto(f"file://{ROOT}/beed_lab.html")
        page.wait_for_selector("#c")
        page.set_input_files("#file", str(PLY_PATH))
        page.wait_for_timeout(300)
        page.set_input_files("#pfile", str(PRESET_PATH))
        page.wait_for_timeout(300)
        # hide the HUD text and axis gizmo so the crop matches a clean "save png" export
        page.evaluate(
            "() => ['hud','gizmo','gizmoTxt','drop'].forEach(id => { "
            "const el = document.getElementById(id); if (el) el.style.display = 'none'; })"
        )
        # The reference preset's ambient (0.04) is tuned for one hero angle with a single
        # key light; spun a full 360 degrees, the far side falls to near-black. Raise it
        # just for this GIF so the whole turntable stays readable.
        page.eval_on_selector(
            "#amb", "(el, v) => { el.value = v; el.dispatchEvent(new Event('input')); }", 0.55
        )
        page.wait_for_timeout(250)  # let a few rAF ticks land before the first capture

        frames = []
        for i in range(FRAMES):
            angle = wrap180(cazim0 + 360 * i / FRAMES)
            page.eval_on_selector(
                "#cazim",
                "(el, v) => { el.value = v; el.dispatchEvent(new Event('input')); }",
                angle,
            )
            page.wait_for_timeout(90)
            png = page.locator("#c").screenshot()
            frames.append(Image.open(io.BytesIO(png)).convert("RGB"))

        browser.close()

    save_gif(frames, OUT_PATH, DURATION_MS)
    print(f"wrote {OUT_PATH} ({len(frames)} frames)")


if __name__ == "__main__":
    main()
