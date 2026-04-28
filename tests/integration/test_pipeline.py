"""
Integration tests: end-to-end from IFC file to triangulated mesh.

Uses the synthetic IFC fixtures in tests/data/.
"""

import tempfile
from pathlib import Path

import numpy as np
import pytest

DATA_DIR = Path(__file__).parent.parent / "data"


# ─── helpers ─────────────────────────────────────────────────────────────────

def _parse_slab_profile_directly(ifc_path: Path):
    """
    Minimal direct parse of our stub IFC files without ifcopenshell.
    Extracts IfcRectangleProfileDef XDim/YDim for testing purposes.
    """
    import re
    text = ifc_path.read_text()
    m = re.search(r"IFCRECTANGLEPROFILEDEF\([^,]*,[^,]*,[^,]*,([0-9.]+),([0-9.]+)\)", text)
    if not m:
        return None
    return float(m.group(1)), float(m.group(2))


# ─── geometry-only pipeline (no ifcopenshell) ────────────────────────────────

def test_geometry_pipeline_simple_slab():
    """Triangulate a manually constructed 10×6 slab — no IFC parsing needed."""
    from ifc_slab_mesh.geometry import build_triangulation_input
    from ifc_slab_mesh.triangulate import triangulate_polygon, validate_result

    boundary = np.array([[0, 0], [10, 0], [10, 6], [0, 6]], dtype=float)
    ti = build_triangulation_input(boundary, [])
    assert ti is not None

    result = triangulate_polygon(ti, quality=True)
    assert result is not None
    assert validate_result(result, expected_area=60.0, area_tol=0.02)


def test_geometry_pipeline_slab_with_two_openings():
    """8×5 slab with two 1×1 openings. Expected area = 40 - 2 = 38 m²."""
    from ifc_slab_mesh.geometry import build_triangulation_input
    from ifc_slab_mesh.triangulate import triangulate_polygon, validate_result

    boundary = np.array([[0, 0], [8, 0], [8, 5], [0, 5]], dtype=float)
    op1 = np.array([[1, 1], [2, 1], [2, 2], [1, 2]], dtype=float)
    op2 = np.array([[5, 3], [6, 3], [6, 4], [5, 4]], dtype=float)
    ti = build_triangulation_input(boundary, [op1, op2])
    assert ti is not None

    result = triangulate_polygon(ti, quality=True)
    assert result is not None
    assert validate_result(result, expected_area=38.0, area_tol=0.02)


def test_geometry_pipeline_l_shaped_slab():
    """L-shaped slab (12 m² with 4 m² corner removed → 8 m²)."""
    from ifc_slab_mesh.geometry import build_triangulation_input
    from ifc_slab_mesh.triangulate import triangulate_polygon

    boundary = np.array([
        [0, 0], [4, 0], [4, 2], [2, 2], [2, 4], [0, 4]
    ], dtype=float)
    ti = build_triangulation_input(boundary, [])
    assert ti is not None

    result = triangulate_polygon(ti, quality=True)
    assert result is not None
    assert result.area == pytest.approx(8.0, rel=0.02)


def test_pipeline_result_3d_coordinates():
    """Verify that 3-D projection produces correct world coordinates."""
    import numpy as np
    from ifc_slab_mesh.geometry import build_triangulation_input, local_2d_to_world
    from ifc_slab_mesh.triangulate import triangulate_polygon

    boundary = np.array([[0, 0], [5, 0], [5, 5], [0, 5]], dtype=float)
    ti = build_triangulation_input(boundary, [])
    result = triangulate_polygon(ti)
    assert result is not None

    # Identity placement — 3D z should be 0
    placement = np.eye(4, dtype=float)
    verts_3d = local_2d_to_world(result.vertices, placement, elevation=0.0)
    assert verts_3d.shape[1] == 3
    np.testing.assert_allclose(verts_3d[:, 2], 0.0, atol=1e-10)


def test_full_pipeline_output_formats():
    """Run triangulate_slabs and verify OBJ, PLY, NPZ export all succeed."""
    import tempfile
    from pathlib import Path
    from ifc_slab_mesh.geometry import build_triangulation_input
    from ifc_slab_mesh.ifc_parser import ProfileData, SlabData
    from ifc_slab_mesh.pipeline import triangulate_slabs
    from ifc_slab_mesh.export import to_obj, to_ply, to_npz, load_npz
    from ifc_slab_mesh.geometry import local_2d_to_world
    from ifc_slab_mesh.triangulate import triangulate_polygon

    boundary = np.array([[0, 0], [6, 0], [6, 4], [0, 4]], dtype=float)
    profile = ProfileData(vertices=boundary)
    slab = SlabData(
        global_id="TEST001",
        name="TestSlab",
        placement_matrix=np.eye(4, dtype=float),
        profile=profile,
        openings=[],
    )
    result = triangulate_slabs([slab])
    assert len(result.meshes) == 1
    mesh = result.meshes[0]

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        to_obj(mesh.vertices, mesh.faces, tmp_path / "out.obj")
        to_ply(mesh.vertices, mesh.faces, tmp_path / "out.ply")
        to_npz(mesh.vertices, mesh.faces, tmp_path / "out.npz")
        v, f = load_npz(tmp_path / "out.npz")

        assert (tmp_path / "out.obj").exists()
        assert (tmp_path / "out.ply").exists()
        np.testing.assert_array_equal(v, mesh.vertices)
        np.testing.assert_array_equal(f, mesh.faces)
