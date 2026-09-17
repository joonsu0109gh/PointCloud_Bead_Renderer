"""Shared helpers for scripts/render_*_gif.py.

Loads examples/sample_pcd_3000.ply and reproduces Bead Lab's default point
normalization plus the object rotation and camera orbit stored in
examples/sample_bead_preset.json (the preset that produced
docs/images/bead_render_3000.png), so the standard-viewer and Bead Lab
renders line up on the same shape from the same angle.
"""
import json
import math
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
PLY_PATH = ROOT / "examples" / "sample_pcd_3000.ply"
PRESET_PATH = ROOT / "examples" / "sample_bead_preset.json"


def load_ply_xyz(path=PLY_PATH):
    with open(path, "rb") as f:
        header = []
        while True:
            line = f.readline()
            header.append(line)
            if line.strip() == b"end_header":
                break
        text = b"".join(header).decode("ascii")
        if "format ascii" not in text:
            raise ValueError("this script only reads ASCII PLY files")
        n = int(next(l for l in text.splitlines() if l.startswith("element vertex")).split()[-1])
        return np.loadtxt(f, max_rows=n)[:, :3]


def normalize(raw):
    """Match Bead Lab's normalized(): swap x/z, center, scale into a unit sphere."""
    mn, mx = raw.min(axis=0), raw.max(axis=0)
    c = (mn + mx) / 2
    x, y, z = raw[:, 2] - c[2], raw[:, 1] - c[1], raw[:, 0] - c[0]
    p = np.stack([x, y, z], axis=1)
    s = np.max(np.linalg.norm(p, axis=1))
    return p / (s or 1)


def euler_xyz_matrix(rx, ry, rz):
    """Three.js Object3D default 'XYZ' Euler order, angles in radians."""
    c1, s1 = math.cos(rx), math.sin(rx)
    c2, s2 = math.cos(ry), math.sin(ry)
    c3, s3 = math.cos(rz), math.sin(rz)
    return np.array([
        [c2 * c3, -c2 * s3, s2],
        [c1 * s3 + s1 * s2 * c3, c1 * c3 - s1 * s2 * s3, -s1 * c2],
        [s1 * s3 - c1 * s2 * c3, s1 * c3 + c1 * s2 * s3, c1 * c2],
    ])


def load_preset(path=PRESET_PATH):
    p = json.load(open(path))
    params, view = p["params"], p["view"]
    rot_deg = (params["rotx"], params["roty"], params["rotz"])
    return rot_deg, view["theta"], view["phi"], view["dist"]


# Bead Lab's own tint knob (tfloor:1, tstr:1) is neutralized in this preset — the
# visible shading in bead_render_3000.png comes entirely from Three.js's real
# lighting on real sphere geometry. These constants pull the material/light
# values a "standard viewer" would need to approximate that by hand.
BEAD_RADIUS = 0.036          # params.brad, normalized-cloud units
BEAD_COLOR = (0xdf / 255, 0xe3 / 255, 0xe7 / 255)  # params.color "#dfe3e7"
BEAD_ROUGHNESS = 0.65         # params.rough
LIGHT_AZIM_DEG, LIGHT_ELEV_DEG = 180, 17  # params.lazim/lelev
LIGHT_INTENSITY = 0.65        # params.lint
KNN = 42                      # params.knn

# The reference amb (0.04) is tuned for one hero angle under a single key
# light; spun a full 360 degrees the far side falls to near-black (same issue
# fixed for the live Bead Lab capture in render_bead_lab_gif.py). Use the same
# boosted ambient here so all three comparison loops stay readable throughout.
GIF_AMBIENT = 0.55


def key_light_dir(azim_deg=LIGHT_AZIM_DEG, elev_deg=LIGHT_ELEV_DEG):
    """World-space direction to Bead Lab's key light (see updateLight() in beed_lab.html)."""
    a, e = math.radians(azim_deg), math.radians(elev_deg)
    d = np.array([math.cos(e) * math.sin(a), math.sin(e), math.cos(e) * math.cos(a)])
    return d / np.linalg.norm(d)


def estimate_normals(points, k=KNN):
    """Per-point outward normal via local PCA, mirroring estimateNormals() in
    beed_lab.html: k-nearest neighbors, smallest-eigenvector of the local
    covariance, oriented away from the cloud's centroid.
    """
    from scipy.spatial import cKDTree

    tree = cKDTree(points)
    _, idx = tree.query(points, k=min(k + 1, len(points)))
    centroid = points.mean(axis=0)

    normals = np.empty_like(points)
    for i, neighbors in enumerate(idx):
        nbr_pts = points[neighbors]
        cov = np.cov(nbr_pts, rowvar=False)
        eigvals, eigvecs = np.linalg.eigh(cov)
        n = eigvecs[:, 0]  # eigh returns ascending eigenvalues; index 0 = smallest
        if np.dot(n, points[i] - centroid) < 0:
            n = -n
        normals[i] = n
    return normals


def lambert_shade(normals, light_dir=None, ambient=GIF_AMBIENT, intensity=LIGHT_INTENSITY):
    """Simple diffuse brightness per point, approximating Bead Lab's real
    per-sphere lighting closely enough for a flat-marker "standard viewer".
    """
    if light_dir is None:
        light_dir = key_light_dir()
    diffuse = np.clip(normals @ light_dir, 0, None)
    return np.clip(ambient + intensity * diffuse, 0, 1)


def load_reference_cloud():
    """Points normalized + object-rotated exactly like the reference bead render.

    Returns (points, theta0, phi, dist) — theta0/phi/dist are the reference
    camera orbit; vary theta around theta0 for a turntable rotation.
    """
    rot_deg, theta0, phi, dist = load_preset()
    p = normalize(load_ply_xyz())
    rx, ry, rz = (math.radians(d) for d in rot_deg)
    p = p @ euler_xyz_matrix(rx, ry, rz).T
    return p, theta0, phi, dist


def camera_eye(theta, phi, dist):
    return dist * np.array([
        math.sin(phi) * math.sin(theta),
        math.cos(phi),
        math.sin(phi) * math.cos(theta),
    ])


def camera_basis(theta, phi, dist):
    """Right/up axes of the camera looking at the origin from camera_eye()."""
    eye = camera_eye(theta, phi, dist)
    forward = -eye / np.linalg.norm(eye)
    up = np.array([0.0, 1.0, 0.0])
    right = np.cross(forward, up)
    right /= np.linalg.norm(right)
    true_up = np.cross(right, forward)
    return right, true_up, forward


def save_gif(frames, out_path, duration_ms):
    """Save RGB frames as a GIF using one shared, globally-computed palette.

    Quantizing each frame independently (Pillow's default when you just call
    frames[0].save(..., append_images=...)) lets a sparse/blank frame produce
    a poor palette that every other frame then gets crushed into — e.g. a
    near-white first frame can make later gray content clip to black. Build
    the palette from a strip of sampled frames instead.
    """
    from PIL import Image

    sample_n = min(len(frames), 12)
    step = max(1, len(frames) // sample_n)
    strip_frames = frames[::step]
    w, h = frames[0].size
    strip = Image.new("RGB", (w * len(strip_frames), h))
    for i, f in enumerate(strip_frames):
        strip.paste(f, (i * w, 0))
    global_palette = strip.quantize(colors=256)

    quantized = [f.quantize(palette=global_palette, dither=Image.FLOYDSTEINBERG) for f in frames]
    quantized[0].save(
        out_path, save_all=True, append_images=quantized[1:],
        duration=duration_ms, loop=0, disposal=2,
    )
