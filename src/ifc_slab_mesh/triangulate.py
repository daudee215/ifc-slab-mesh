# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Daud Tasleem
"""
Constrained Delaunay triangulation via Shewchuk's Triangle library.

This module wraps the `triangle` Python package and adds:
  - quality constraints (minimum angle 20°)
  - maximum triangle area enforcement
  - output normalisation to (vertices_2d, faces) numpy arrays
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

import numpy as np

from ifc_slab_mesh.geometry import TriangulationInput

logger = logging.getLogger(__name__)


@dataclass
class TriangulationResult:
    """Output of a successful CDT operation."""

    vertices: np.ndarray  # shape (V, 2), float64 — 2-D coords in slab local frame
    faces: np.ndarray     # shape (F, 3), int32  — triangle vertex indices
    area: float           # total area of the triangulated domain (m²)
    num_steiner: int      # Steiner points inserted by Triangle


def triangulate_polygon(
    tri_input: TriangulationInput,
    quality: bool = True,
    min_angle: float = 20.0,
    max_area: float | None = None,
) -> TriangulationResult | None:
    """Run constrained Delaunay triangulation on the assembled input.

    Parameters
    ----------
    tri_input:
        Assembled boundary + holes from ``geometry.build_triangulation_input``.
    quality:
        If True, enables Ruppert's refinement for minimum angle guarantee.
    min_angle:
        Minimum interior angle in degrees (applies only when quality=True).
        Values > 28.6° may cause non-termination for some inputs.
    max_area:
        Maximum triangle area in square metres. If None, no area constraint.

    Returns
    -------
    TriangulationResult or None on failure.
    """
    try:
        import triangle as tr  # type: ignore[import]
    except ImportError as exc:
        raise ImportError(
            "triangle is required: pip install triangle"
        ) from exc

    data = tri_input.build()
    n_input_verts = len(data["vertices"])

    # Build Triangle flags:
    # p  = constrained Delaunay (respect segments)
    # q  = quality with min angle
    # a  = max area
    # z  = zero-based indexing
    # Q  = quiet mode
    flags = "pzQ"
    if quality:
        flags += f"q{min_angle:.1f}"
    if max_area is not None:
        flags += f"a{max_area:.6f}"

    try:
        result = tr.triangulate(data, flags)
    except Exception as exc:
        logger.error("Triangle library raised: %s", exc)
        return None

    verts = result.get("vertices")
    tris = result.get("triangles")

    if verts is None or tris is None or len(tris) == 0:
        logger.error("Triangle produced no triangles")
        return None

    verts = np.asarray(verts, dtype=np.float64)
    tris = np.asarray(tris, dtype=np.int32)

    # Compute total area
    v0 = verts[tris[:, 0]]
    v1 = verts[tris[:, 1]]
    v2 = verts[tris[:, 2]]
    cross = (v1 - v0)[:, 0] * (v2 - v0)[:, 1] - (v1 - v0)[:, 1] * (v2 - v0)[:, 0]
    total_area = float(np.abs(cross).sum() / 2.0)

    n_steiner = len(verts) - n_input_verts

    logger.debug(
        "CDT: %d input verts → %d verts, %d triangles, %d Steiner points, area=%.4f m²",
        n_input_verts, len(verts), len(tris), n_steiner, total_area,
    )

    return TriangulationResult(
        vertices=verts,
        faces=tris,
        area=total_area,
        num_steiner=n_steiner,
    )


def validate_result(
    result: TriangulationResult,
    expected_area: float,
    area_tol: float = 0.01,
) -> bool:
    """Verify that the triangulation area matches the expected domain area.

    Parameters
    ----------
    result:
        Output from ``triangulate_polygon``.
    expected_area:
        Domain area computed analytically (slab_area - sum(opening_areas)).
    area_tol:
        Relative tolerance: ``|result.area - expected_area| / expected_area < tol``.

    Returns
    -------
    bool: True if the area check passes.
    """
    if expected_area <= 0:
        return True
    rel_err = abs(result.area - expected_area) / expected_area
    if rel_err > area_tol:
        logger.warning(
            "Area mismatch: triangulated=%.4f expected=%.4f rel_err=%.4f",
            result.area, expected_area, rel_err,
        )
        return False
    return True
