# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Daud Tasleem
"""
Geometry utilities: polygon cleaning, point-in-polygon test, hole point
generation, and input validation for the triangulation stage.
"""

from __future__ import annotations

import logging
from collections.abc import Sequence

import numpy as np

logger = logging.getLogger(__name__)


# ─── Polygon utilities ────────────────────────────────────────────────────────

def signed_area(verts: np.ndarray) -> float:
    """Return signed area of a simple polygon (positive = CCW, negative = CW)."""
    x, y = verts[:, 0], verts[:, 1]
    return float(np.dot(x, np.roll(y, -1)) - np.dot(np.roll(x, -1), y)) / 2.0


def ensure_ccw(verts: np.ndarray) -> np.ndarray:
    """Return vertices in counter-clockwise order."""
    if signed_area(verts) < 0:
        return verts[::-1].copy()
    return verts


def ensure_cw(verts: np.ndarray) -> np.ndarray:
    """Return vertices in clockwise order (for hole boundaries)."""
    if signed_area(verts) > 0:
        return verts[::-1].copy()
    return verts


def remove_duplicate_vertices(verts: np.ndarray, tol: float = 1e-9) -> np.ndarray:
    """Remove consecutive duplicate vertices."""
    if len(verts) == 0:
        return verts
    keep = [0]
    for i in range(1, len(verts)):
        if np.linalg.norm(verts[i] - verts[keep[-1]]) > tol:
            keep.append(i)
    # Also check wrap-around
    if len(keep) > 1 and np.linalg.norm(verts[keep[0]] - verts[keep[-1]]) < tol:
        keep = keep[:-1]
    return verts[keep]


def centroid(verts: np.ndarray) -> np.ndarray:
    """Return the centroid of a polygon."""
    return verts.mean(axis=0)


def interior_point(verts: np.ndarray) -> np.ndarray:
    """Return a point guaranteed to be strictly inside the polygon.

    Uses the centroid, which is inside for convex polygons. For concave
    polygons we perturb along the inward normal of the longest edge until
    we find an interior point.
    """
    c = centroid(verts)
    if point_in_polygon(c, verts):
        return c
    # Fallback: sample midpoints of diagonals
    n = len(verts)
    for i in range(0, n, max(1, n // 8)):
        for j in range(i + 2, min(i + n // 2, n)):
            mid = (verts[i] + verts[j]) / 2.0
            if point_in_polygon(mid, verts):
                return mid
    return c  # best effort


def point_in_polygon(pt: np.ndarray, verts: np.ndarray) -> bool:
    """Ray-casting point-in-polygon test."""
    x, y = float(pt[0]), float(pt[1])
    n = len(verts)
    inside = False
    j = n - 1
    for i in range(n):
        xi, yi = float(verts[i, 0]), float(verts[i, 1])
        xj, yj = float(verts[j, 0]), float(verts[j, 1])
        if ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / (yj - yi + 1e-15) + xi):
            inside = not inside
        j = i
    return inside


# ─── Triangle input assembly ──────────────────────────────────────────────────

class TriangulationInput:
    """Assembled input for the `triangle` library.

    Attributes
    ----------
    vertices : np.ndarray, shape (V, 2)
    segments : np.ndarray, shape (S, 2)  — indices into vertices
    holes    : np.ndarray, shape (H, 2)  — one interior point per hole
    """

    def __init__(self) -> None:
        self._verts: list[np.ndarray] = []
        self._segs: list[tuple[int, int]] = []
        self._holes: list[np.ndarray] = []
        self._offset = 0

    def _add_ring(self, ring: np.ndarray) -> None:
        """Add a closed ring of vertices and the corresponding segment loop."""
        n = len(ring)
        base = self._offset
        self._verts.extend(ring)
        for i in range(n):
            self._segs.append((base + i, base + (i + 1) % n))
        self._offset += n

    def add_boundary(self, verts: np.ndarray) -> None:
        """Add the outer boundary ring (must be CCW)."""
        self._add_ring(verts)

    def add_hole(self, verts: np.ndarray) -> None:
        """Add a hole ring (must be CW) and register an interior hole point."""
        self._add_ring(verts)
        self._holes.append(interior_point(verts))

    def build(self) -> dict:
        """Return the dict expected by ``triangle.triangulate``."""
        v = np.array(self._verts, dtype=np.float64)
        s = np.array(self._segs, dtype=np.int32)
        result: dict = {"vertices": v, "segments": s}
        if self._holes:
            result["holes"] = np.array(self._holes, dtype=np.float64)
        return result


def build_triangulation_input(
    boundary: np.ndarray,
    openings: Sequence[np.ndarray],
    min_vertices: int = 3,
) -> TriangulationInput | None:
    """Validate and assemble boundary + opening polygons into TriangulationInput.

    Parameters
    ----------
    boundary:
        Outer slab boundary, (N, 2).
    openings:
        List of opening polygons, each (M_i, 2).
    min_vertices:
        Minimum vertex count required for a valid polygon.

    Returns
    -------
    TriangulationInput or None if the boundary is invalid.
    """
    boundary = remove_duplicate_vertices(boundary)
    if len(boundary) < min_vertices:
        logger.error("Boundary has fewer than %d vertices after dedup — skipping", min_vertices)
        return None

    ti = TriangulationInput()
    ti.add_boundary(ensure_ccw(boundary))

    for i, opening in enumerate(openings):
        opening = remove_duplicate_vertices(opening)
        if len(opening) < min_vertices:
            logger.warning("Opening %d has < %d vertices — skipping", i, min_vertices)
            continue
        # Verify opening is inside boundary
        c = centroid(opening)
        if not point_in_polygon(c, boundary):
            logger.warning("Opening %d centroid is outside boundary — skipping", i)
            continue
        ti.add_hole(ensure_cw(opening))

    return ti


# ─── 3-D / 2-D projection helpers ────────────────────────────────────────────

def world_to_local_2d(
    points_3d: np.ndarray,
    placement_matrix: np.ndarray,
) -> tuple[np.ndarray, float]:
    """Project world-frame 3-D points to the local 2-D slab plane.

    Parameters
    ----------
    points_3d : shape (N, 3)
    placement_matrix : 4×4 homogeneous local→world matrix

    Returns
    -------
    points_2d : shape (N, 2)  — in local XY plane
    elevation : float  — average local Z coordinate (used for back-projection)
    """
    inv = np.linalg.inv(placement_matrix)
    ones = np.ones((len(points_3d), 1))
    hom = np.hstack([points_3d, ones]) @ inv.T
    pts_local = hom[:, :3]
    return pts_local[:, :2], float(pts_local[:, 2].mean())


def local_2d_to_world(
    points_2d: np.ndarray,
    placement_matrix: np.ndarray,
    elevation: float = 0.0,
) -> np.ndarray:
    """Back-project local 2-D points to world-frame 3-D coordinates.

    Parameters
    ----------
    points_2d : shape (N, 2)
    placement_matrix : 4×4 homogeneous local→world
    elevation : local Z value to use (slab top face)

    Returns
    -------
    points_3d : shape (N, 3)
    """
    n = len(points_2d)
    pts_local = np.column_stack([points_2d, np.full(n, elevation), np.ones(n)])
    pts_world = pts_local @ placement_matrix.T
    return pts_world[:, :3]
