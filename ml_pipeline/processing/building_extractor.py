"""
Module A — Building extraction.
Input: LiDAR / point cloud + drone imagery.
Output: building points, 2D footprint, 3D envelope (bounding volume).

Uses Open3D when a real point cloud (.ply/.las via a pre-converted .ply) is
supplied. Falls back to a synthetic extruded-footprint point cloud when no
file is given — see the guide's Section 6 "Data & demo risk plan": the
hackathon MVP runs on a synthetic building, same code path as real LiDAR.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

import numpy as np

try:
    import open3d as o3d
    HAS_OPEN3D = True
except ImportError:  # pragma: no cover - demo machines may not have open3d installed
    HAS_OPEN3D = False

logger = logging.getLogger("ulpin3d.building_extractor")


@dataclass
class BuildingEnvelope:
    footprint: List[Tuple[float, float]]   # 2D polygon (lon/lat or local XY)
    z_min: float
    z_max: float
    point_count: int
    source: str = "synthetic"
    points: Optional[np.ndarray] = field(default=None, repr=False)


def load_point_cloud(path: str) -> np.ndarray:
    """Load a point cloud from disk. Requires open3d; raises if unavailable."""
    if not HAS_OPEN3D:
        raise RuntimeError("open3d is not installed — install ml_pipeline/requirements.txt")
    pcd = o3d.io.read_point_cloud(path)
    return np.asarray(pcd.points)


def generate_synthetic_building(
    footprint: Optional[List[Tuple[float, float]]] = None,
    floor_height_m: float = 3.2,
    num_floors: int = 4,
    points_per_floor: int = 2000,
    seed: int = 42,
) -> np.ndarray:
    """
    Synthetic point cloud fallback: extrude a footprint polygon to `num_floors`
    floors of `floor_height_m` each, sampling random points on each floor slab
    plus wall points, so downstream segmentation has realistic elevation bands
    to cluster on. Mirrors the recommended MVP data plan (Section 6).
    """
    rng = np.random.default_rng(seed)
    if footprint is None:
        # simple 12m x 8m rectangle, local metric coordinates
        footprint = [(0, 0), (12, 0), (12, 8), (0, 8)]
    poly = np.array(footprint)
    x_min, y_min = poly.min(axis=0)
    x_max, y_max = poly.max(axis=0)

    all_points = []
    for floor in range(num_floors):
        z0 = floor * floor_height_m
        z1 = z0 + floor_height_m
        xs = rng.uniform(x_min, x_max, points_per_floor)
        ys = rng.uniform(y_min, y_max, points_per_floor)
        # slab points at floor bottom + a thin scatter through the storey (walls/furniture proxy)
        zs = np.concatenate([
            np.full(points_per_floor // 2, z0),
            rng.uniform(z0, z1, points_per_floor - points_per_floor // 2),
        ])
        all_points.append(np.column_stack([xs, ys, zs]))
    return np.vstack(all_points)


def extract_building(points: np.ndarray, source: str = "synthetic") -> BuildingEnvelope:
    """
    Module A core: derive footprint (2D convex hull of XY) and 3D envelope
    (z_min/z_max) from a raw point cloud. This is the heuristic MVP version;
    the roadmap version (Section 7) swaps this for a learned point-transformer
    building segmentation model.
    """
    if points.size == 0:
        raise ValueError("empty point cloud")

    xy = points[:, :2]
    z = points[:, 2]

    footprint = _convex_hull_2d(xy)

    envelope = BuildingEnvelope(
        footprint=[tuple(p) for p in footprint],
        z_min=float(z.min()),
        z_max=float(z.max()),
        point_count=int(points.shape[0]),
        source=source,
        points=points,
    )
    logger.info(
        "Extracted building envelope: %d points, z=[%.2f, %.2f], footprint vertices=%d",
        envelope.point_count, envelope.z_min, envelope.z_max, len(envelope.footprint),
    )
    return envelope


def _convex_hull_2d(points: np.ndarray) -> np.ndarray:
    """Andrew's monotone chain convex hull — avoids a scipy dependency."""
    pts = np.unique(points, axis=0)
    pts = pts[np.lexsort((pts[:, 1], pts[:, 0]))]
    if len(pts) <= 2:
        return pts

    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])

    lower = []
    for p in pts:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], p) <= 0:
            lower.pop()
        lower.append(p)

    upper = []
    for p in pts[::-1]:
        while len(upper) >= 2 and cross(upper[-2], upper[-1], p) <= 0:
            upper.pop()
        upper.append(p)

    return np.array(lower[:-1] + upper[:-1])


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    demo_points = generate_synthetic_building()
    env = extract_building(demo_points)
    print(f"Footprint: {env.footprint}")
    print(f"Z range: {env.z_min:.2f} - {env.z_max:.2f} m over {env.point_count} points")
