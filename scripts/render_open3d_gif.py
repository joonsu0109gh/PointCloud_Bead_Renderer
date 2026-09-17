#!/usr/bin/env python3
"""Rotating GIF of examples/sample_pcd_3000.ply rendered with Open3D's
offscreen renderer as real, per-vertex-lit sphere meshes — the closest a
"standard viewer" gets to Bead Lab's own instanced-sphere rendering. Compare
against the flat-marker approximation in render_matplotlib_gif.py and the
real thing in render_bead_lab_gif.py.

Usage:
  pip install numpy open3d pillow
  python3 scripts/render_open3d_gif.py
"""
import math

import numpy as np
import open3d as o3d
from PIL import Image

from _pointcloud import (
    BEAD_COLOR,
    BEAD_RADIUS,
    BEAD_ROUGHNESS,
    ROOT,
    camera_eye,
    key_light_dir,
    load_reference_cloud,
    save_gif,
)

OUT_PATH = ROOT / "docs" / "images" / "compare_open3d.gif"
FRAMES = 36
DURATION_MS = 70
SIZE = 480
SPHERE_RESOLUTION = 6  # low-poly, similar spirit to Bead Lab's low "tessellation" setting


def build_bead_mesh(points, radius):
    template = o3d.geometry.TriangleMesh.create_sphere(radius=radius, resolution=SPHERE_RESOLUTION)
    tv, tt = np.asarray(template.vertices), np.asarray(template.triangles)
    n_v = tv.shape[0]

    all_verts = (tv[None, :, :] + points[:, None, :]).reshape(-1, 3)
    tri_offsets = (np.arange(len(points))[:, None, None] * n_v)
    all_tris = (tt[None, :, :] + tri_offsets).reshape(-1, 3)

    mesh = o3d.geometry.TriangleMesh()
    mesh.vertices = o3d.utility.Vector3dVector(all_verts)
    mesh.triangles = o3d.utility.Vector3iVector(all_tris)
    mesh.compute_vertex_normals()
    return mesh


def main():
    p, theta0, phi, dist = load_reference_cloud()
    mesh = build_bead_mesh(p, BEAD_RADIUS)

    renderer = o3d.visualization.rendering.OffscreenRenderer(SIZE, SIZE)
    renderer.scene.set_background([1, 1, 1, 1])
    renderer.scene.show_skybox(False)
    renderer.scene.view.set_post_processing(False)  # avoid a tonemapped, off-white background

    mat = o3d.visualization.rendering.MaterialRecord()
    mat.shader = "defaultLit"
    mat.base_color = [*BEAD_COLOR, 1.0]
    mat.base_roughness = BEAD_ROUGHNESS
    mat.base_metallic = 0.0
    renderer.scene.add_geometry("beads", mesh, mat)

    # Sun = Bead Lab's key light direction; the sun/indirect intensities below
    # are hand-tuned for this material and camera framing (Open3D's PBR sun
    # is in lux, not the arbitrary units Three.js uses, so params.lint/amb
    # don't transfer directly) — chosen so the far side of the turntable
    # stays readable, unlike the reference's amb=0.04 tuned for one hero angle.
    L = key_light_dir()
    renderer.scene.scene.enable_sun_light(True)
    renderer.scene.scene.set_sun_light((-L).tolist(), [1.0, 1.0, 1.0], 200_000)
    renderer.scene.scene.enable_indirect_light(True)
    renderer.scene.scene.set_indirect_light_intensity(150_000)

    up = [0, 1, 0]
    frames = []
    for i in range(FRAMES):
        theta = theta0 + 2 * math.pi * i / FRAMES
        eye = camera_eye(theta, phi, dist)
        renderer.setup_camera(35.0, [0, 0, 0], eye.tolist(), up)
        img = np.asarray(renderer.render_to_image())
        frames.append(Image.fromarray(img))

    save_gif(frames, OUT_PATH, DURATION_MS)
    print(f"wrote {OUT_PATH} ({len(frames)} frames)")


if __name__ == "__main__":
    main()
