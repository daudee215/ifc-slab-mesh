"""Unit tests for ifc_slab_mesh.geometry module."""

import numpy as np
import pytest

from ifc_slab_mesh.geometry import (
    build_triangulation_input,
    centroid,
    ensure_ccw,
    ensure_cw,
    interior_point,
    local_2d_to_world,
    point_in_polygon,
    remove_duplicate_vertices,
    signed_area,
    world_to_local_2d,
)


# ─── signed_area ────────────────────────────────────────────────────────────

def test_signed_area_square_ccw():
    square = np.array([[0, 0], [1, 0], [1, 1], [0, 1]], dtype=float)
    assert signed_area(square) == pytest.approx(1.0)


def test_signed_area_square_cw():
    square = np.array([[0, 0], [0, 1], [1, 1], [1, 0]], dtype=float)
    assert signed_area(square) == pytest.approx(-1.0)


def test_signed_area_triangle():
    tri = np.array([[0, 0], [4, 0], [0, 3]], dtype=float)
    assert signed_area(tri) == pytest.approx(6.0)


# ─── ensure_ccw / ensure_cw ─────────────────────────────────────────────────

def test_ensure_ccw_already_ccw():
    verts = np.array([[0, 0], [1, 0], [1, 1], [0, 1]], dtype=float)
    result = ensure_ccw(verts)
    assert signed_area(result) > 0


def test_ensure_ccw_reverses_cw():
    verts = np.array([[0, 0], [0, 1], [1, 1], [1, 0]], dtype=float)
    result = ensure_ccw(verts)
    assert signed_area(result) > 0


def test_ensure_cw_already_cw():
    verts = np.array([[0, 0], [0, 1], [1, 1], [1, 0]], dtype=float)
    result = ensure_cw(verts)
    assert signed_area(result) < 0


# ─── remove_duplicate_vertices ───────────────────────────────────────────────

def test_remove_duplicate_vertices_no_dups():
    verts = np.array([[0, 0], [1, 0], [1, 1]], dtype=float)
    result = remove_duplicate_vertices(verts)
    assert len(result) == 3


def test_remove_duplicate_vertices_with_dups():
    verts = np.array([[0, 0], [0, 0], [1, 0], [1, 0], [1, 1]], dtype=float)
    result = remove_duplicate_vertices(verts)
    assert len(result) == 3


def test_remove_duplicate_vertices_closing():
    # Polygon with closing point repeated
    verts = np.array([[0, 0], [1, 0], [1, 1], [0, 0]], dtype=float)
    result = remove_duplicate_vertices(verts)
    assert len(result) == 3


# ─── point_in_polygon ────────────────────────────────────────────────────────

def test_point_in_polygon_inside():
    square = np.array([[0, 0], [4, 0], [4, 4], [0, 4]], dtype=float)
    assert point_in_polygon(np.array([2.0, 2.0]), square)


def test_point_in_polygon_outside():
    square = np.array([[0, 0], [4, 0], [4, 4], [0, 4]], dtype=float)
    assert not point_in_polygon(np.array([5.0, 2.0]), square)


def test_point_in_polygon_l_shape():
    # L-shaped polygon
    l_shape = np.array([[0, 0], [4, 0], [4, 2], [2, 2], [2, 4], [0, 4]], dtype=float)
    assert point_in_polygon(np.array([1.0, 3.0]), l_shape)
    assert not point_in_polygon(np.array([3.0, 3.0]), l_shape)


# ─── centroid / interior_point ───────────────────────────────────────────────

def test_centroid_square():
    sq = np.array([[0, 0], [2, 0], [2, 2], [0, 2]], dtype=float)
    c = centroid(sq)
    np.testing.assert_allclose(c, [1.0, 1.0])


def test_interior_point_convex():
    sq = np.array([[0, 0], [4, 0], [4, 4], [0, 4]], dtype=float)
    pt = interior_point(sq)
    assert point_in_polygon(pt, sq)


# ─── build_triangulation_input ───────────────────────────────────────────────

def test_build_tri_input_simple():
    boundary = np.array([[0, 0], [10, 0], [10, 6], [0, 6]], dtype=float)
    ti = build_triangulation_input(boundary, [])
    assert ti is not None
    data = ti.build()
    assert len(data["vertices"]) == 4
    assert len(data["segments"]) == 4
    assert "holes" not in data


def test_build_tri_input_with_opening():
    boundary = np.array([[0, 0], [10, 0], [10, 6], [0, 6]], dtype=float)
    opening = np.array([[-1, -1], [1, -1], [1, 1], [-1, 1]], dtype=float)  # outside boundary
    ti = build_triangulation_input(boundary, [opening])
    assert ti is not None
    # Opening outside boundary should be skipped
    data = ti.build()
    assert "holes" not in data


def test_build_tri_input_interior_opening():
    boundary = np.array([[0, 0], [10, 0], [10, 6], [0, 6]], dtype=float)
    opening = np.array([[3, 2], [5, 2], [5, 4], [3, 4]], dtype=float)  # inside
    ti = build_triangulation_input(boundary, [opening])
    assert ti is not None
    data = ti.build()
    assert "holes" in data
    assert len(data["holes"]) == 1


def test_build_tri_input_degenerate():
    # Too few vertices
    ti = build_triangulation_input(np.array([[0, 0], [1, 0]], dtype=float), [])
    assert ti is None


# ─── 3D projections ──────────────────────────────────────────────────────────

def test_round_trip_projection():
    """world_to_local_2d followed by local_2d_to_world should return original points."""
    placement = np.eye(4, dtype=float)
    placement[0, 3] = 5.0  # translate x
    placement[1, 3] = 3.0  # translate y

    pts_2d = np.array([[1.0, 2.0], [3.0, 4.0]])
    pts_3d_local = np.column_stack([pts_2d, np.zeros(len(pts_2d))])

    # Apply placement to get "world" points
    pts_world = (placement[:3, :3] @ pts_3d_local.T).T + placement[:3, 3]

    pts_2d_back, elev = world_to_local_2d(pts_world, placement)
    pts_3d_back = local_2d_to_world(pts_2d_back, placement, elev)

    np.testing.assert_allclose(pts_world, pts_3d_back, atol=1e-10)
