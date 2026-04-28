"""Unit tests for ifc_slab_mesh.export module."""

import struct
import tempfile
from pathlib import Path

import numpy as np
import pytest

from ifc_slab_mesh.export import load_npz, to_npz, to_obj, to_ply


VERTICES = np.array([[0, 0, 0], [1, 0, 0], [1, 1, 0], [0, 1, 0]], dtype=np.float64)
FACES = np.array([[0, 1, 2], [0, 2, 3]], dtype=np.int32)


def test_to_obj_creates_file():
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "test.obj"
        to_obj(VERTICES, FACES, out)
        assert out.exists()


def test_to_obj_vertex_count():
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "test.obj"
        to_obj(VERTICES, FACES, out)
        lines = out.read_text().splitlines()
        v_lines = [l for l in lines if l.startswith("v ")]
        f_lines = [l for l in lines if l.startswith("f ")]
        assert len(v_lines) == len(VERTICES)
        assert len(f_lines) == len(FACES)


def test_to_obj_one_based_indices():
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "test.obj"
        to_obj(VERTICES, FACES, out)
        lines = out.read_text().splitlines()
        f_lines = [l for l in lines if l.startswith("f ")]
        for line in f_lines:
            indices = [int(x) for x in line.split()[1:]]
            assert all(i >= 1 for i in indices)


def test_to_ply_creates_file():
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "test.ply"
        to_ply(VERTICES, FACES, out)
        assert out.exists()


def test_to_ply_header():
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "test.ply"
        to_ply(VERTICES, FACES, out)
        content = out.read_bytes()
        header_end = content.find(b"end_header\n") + len(b"end_header\n")
        header = content[:header_end].decode("ascii")
        assert "element vertex 4" in header
        assert "element face 2" in header
        assert "binary_little_endian" in header


def test_to_ply_vertex_data():
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "test.ply"
        to_ply(VERTICES, FACES, out)
        content = out.read_bytes()
        header_end = content.find(b"end_header\n") + len(b"end_header\n")
        body = content[header_end:]
        # 4 vertices × 3 floats × 4 bytes = 48 bytes
        n_vert_bytes = len(VERTICES) * 3 * 4
        vert_data = body[:n_vert_bytes]
        parsed = np.frombuffer(vert_data, dtype="<f4").reshape(-1, 3)
        np.testing.assert_allclose(parsed, VERTICES, atol=1e-6)


def test_npz_round_trip():
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "mesh.npz"
        to_npz(VERTICES, FACES, out)
        v, f = load_npz(out)
        np.testing.assert_array_equal(v, VERTICES)
        np.testing.assert_array_equal(f, FACES)
