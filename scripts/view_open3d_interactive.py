#!/usr/bin/env python3
"""Open the same Open3D bead mesh from render_open3d_gif.py in a live,
interactive window — drag to orbit, scroll to zoom, native Open3D controls.
Starts framed the same way as the reference bead render, with the same
material/lighting setup as the GIF (the high-level o3d.visualization.draw()
helper uses its own default lighting and tonemapping, which look noticeably
different from the offscreen renderer's hand-tuned, post-processing-off
setup — this uses the lower-level O3DVisualizer so the two match).

This opens a real GUI window, so it needs a display; it won't run over a
plain headless/SSH session without X forwarding or a virtual display.

Usage:
  pip install numpy open3d
  python3 scripts/view_open3d_interactive.py
"""
import open3d as o3d
import open3d.visualization.gui as gui

from _pointcloud import BEAD_COLOR, BEAD_RADIUS, BEAD_ROUGHNESS, camera_eye, key_light_dir, load_reference_cloud
from render_open3d_gif import build_bead_mesh


def main():
    p, theta0, phi, dist = load_reference_cloud()
    mesh = build_bead_mesh(p, BEAD_RADIUS)

    mat = o3d.visualization.rendering.MaterialRecord()
    mat.shader = "defaultLit"
    mat.base_color = [*BEAD_COLOR, 1.0]
    mat.base_roughness = BEAD_ROUGHNESS
    mat.base_metallic = 0.0

    app = gui.Application.instance
    app.initialize()
    vis = o3d.visualization.O3DVisualizer(
        "Bead Lab — Open3D comparison (drag to orbit, scroll to zoom)", 900, 900
    )
    vis.add_geometry("beads", mesh, mat)

    vis.scene.set_background([1, 1, 1, 1])
    vis.scene.show_skybox(False)
    vis.scene.view.set_post_processing(False)  # match render_open3d_gif.py's exposure

    L = key_light_dir()
    vis.scene.scene.enable_sun_light(True)
    vis.scene.scene.set_sun_light((-L).tolist(), [1.0, 1.0, 1.0], 200_000)
    vis.scene.scene.enable_indirect_light(True)
    vis.scene.scene.set_indirect_light_intensity(150_000)

    eye = camera_eye(theta0, phi, dist)
    vis.setup_camera(35.0, [0.0, 0.0, 0.0], eye.tolist(), [0.0, 1.0, 0.0])

    app.add_window(vis)
    app.run()


if __name__ == "__main__":
    main()
