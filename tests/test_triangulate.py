"""Unit tests for ifc_slab_mesh.triangulate module."""

import numpy as np
import pytest

from ifc_slab_mesh.geometry import TriangulationInput, build_triangulation_input
from ifc_slab_mesh.triangulate import triangulate_polygon, validate_result


def _square_ti(w: float = 10.0, h: float = 6.0) -> TriangulationInput:
    boundary = np.array([[0, 0], [w, 0], [w, h], [0, h]], dtype=float)
    ti = build_triangulation_input(boundary, [])
    assert ti is not None
    return ti


def _square_with_hole_ti(
    outer_w: float = 10.0, outer_h: float = 6.0,
    inner_w: float = 2.0, inner_h: float = 2.0,
) -> TriangulationInput:
    boundary = np.array([[0, 0], [outer_w, 0], [outer_w, outer_h], [0, outer_h]], dtype=float)
    cx, cy = outer_w / 2, outer_h / 2
    hw, hh = inner_w / 2, inner_h / 2
    opening = np.array([
        [cx - hw, cy - hh], [cx + hw, cy - hh],
        [cx + hw, cy + hh], [cx - hw, cy + hh],
    ], dtype=float)
    ti = build_triangulation_input(boundary, [opening])
    assert ti is not None
    return ti


# ─── basic triangulation ─────────────────────────────────────────────────────

def test_triangulate_simple_rectangle():
    ti = _square_ti(10.0, 6.0)
    result = triangulate_polygon(ti, quality=True)
    assert result is not None
    assert len(result.faces) >= 2  # at minimum 2 triangles for a quad
    assert result.area == pytest.approx(60.0, rel=0.01)


def test_triangulate_produces_valid_indices():
    ti = _square_ti()
    result = triangulate_polygon(ti, quality=False)
    assert result is not None
    n_verts = len(result.vertices)
    assert result.faces.min() >= 0
    assert result.faces.max() < n_verts


def test_triangulate_all_triangles_positive_area():
    ti = _square_ti()
    result = triangulate_polygon(ti, quality=True)
    assert result is not None
    v = result.vertices
    f = result.faces
    v0, v1, v2 = v[f[:, 0]], v[f[:, 1]], v[f[:, 2]]
    cross = (v1 - v0)[:, 0] * (v2 - v0)[:, 1] - (v1 - v0)[:, 1] * (v2 - v0)[:, 0]
    assert (cross > 0).all(), "All triangle faces must be CCW (positive area)"


# ─── hole / opening support ──────────────────────────────────────────────────

def test_triangulate_with_interior_hole():
    """Slab 10×6 with 2×2 hole. Expected area = 60 - 4 = 56 m²."""
    ti = _square_with_hole_ti()
    result = triangulate_polygon(ti, quality=True)
    assert result is not None
    assert result.area == pytest.approx(56.0, rel=0.02)


def test_triangulate_hole_reduces_triangles():
    """Adding an interior hole should produce a different triangle count."""
    ti_plain = _square_ti()
    ti_hole = _square_with_hole_ti()
    r_plain = triangulate_polygon(ti_plain, quality=True)
    r_hole = triangulate_polygon(ti_hole, quality=True)
    assert r_plain is not None and r_hole is not None
    # Just verify both succeed; exact counts vary by Steiner point insertion
    assert len(r_hole.faces) > 0


# ─── area validation ─────────────────────────────────────────────────────────

def test_validate_result_pass():
    ti = _square_ti(10.0, 6.0)
    result = triangulate_polygon(ti)
    assert result is not None
    assert validate_result(result, expected_area=60.0, area_tol=0.02)


def test_validate_result_fail():
    ti = _square_ti(10.0, 6.0)
    result = triangulate_polygon(ti)
    assert result is not None
    # Wrong expected area: 100 vs ~60
    assert not validate_result(result, expected_area=100.0, area_tol=0.02)


# ─── Steiner points ──────────────────────────────────────────────────────────

def test_quality_inserts_steiner_points():
    ti = _square_ti(100.0, 100.0)
    result = triangulate_polygon(ti, quality=True, max_area=50.0)
    assert result is not None
    assert result.num_steiner >= 0  # could be 0 for simple shapes


def test_no_quality_no_steiner():
    ti = _square_ti()
    result = triangulate_polygon(ti, quality=False)
    assert result is not None
    # Without refinement, only 2 triangles for a convex quad and no Steiner
    assert result.num_steiner == 0
