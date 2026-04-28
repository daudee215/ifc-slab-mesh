# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Daud Tasleem
"""
High-level pipeline: IFC → triangulated meshes.

This is the main entry point that orchestrates parsing, geometry assembly,
triangulation, and optional export.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

import numpy as np

from ifc_slab_mesh.geometry import build_triangulation_input, local_2d_to_world
from ifc_slab_mesh.ifc_parser import SlabData, load_slabs
from ifc_slab_mesh.triangulate import TriangulationResult, triangulate_polygon

logger = logging.getLogger(__name__)

ExportFormat = Literal["obj", "ply", "npz", "none"]


@dataclass
class SlabMesh:
    """Triangulated mesh for one IfcSlab."""

    global_id: str
    name: str
    vertices: np.ndarray  # shape (V, 3), world-frame metres
    faces: np.ndarray     # shape (F, 3), zero-based indices
    area: float
    num_steiner: int
    num_openings: int


@dataclass
class PipelineResult:
    """Result of a full IFC → mesh pipeline run."""

    ifc_path: str
    meshes: list[SlabMesh] = field(default_factory=list)
    skipped: int = 0
    warnings: list[str] = field(default_factory=list)

    @property
    def total_area(self) -> float:
        return sum(m.area for m in self.meshes)

    @property
    def total_triangles(self) -> int:
        return sum(len(m.faces) for m in self.meshes)


def triangulate_slabs(
    slabs: list[SlabData],
    quality: bool = True,
    min_angle: float = 20.0,
    max_area: float | None = None,
) -> PipelineResult:
    """Triangulate a list of pre-parsed SlabData objects.

    Parameters
    ----------
    slabs:
        Output of ``load_slabs``.
    quality:
        Enable quality refinement (Ruppert's algorithm).
    min_angle:
        Minimum interior angle for quality triangulation.
    max_area:
        Optional maximum triangle area in m².

    Returns
    -------
    PipelineResult containing one SlabMesh per successfully triangulated slab.
    """
    result = PipelineResult(ifc_path="<slabs>")

    for slab in slabs:
        boundary_2d = slab.profile.vertices
        openings_2d = [op.vertices for op in slab.openings]

        ti = build_triangulation_input(boundary_2d, openings_2d)
        if ti is None:
            logger.warning("Slab %s: skipping — invalid geometry", slab.global_id)
            result.skipped += 1
            continue

        tri_result: TriangulationResult | None = triangulate_polygon(
            ti, quality=quality, min_angle=min_angle, max_area=max_area
        )
        if tri_result is None:
            logger.warning("Slab %s: triangulation failed", slab.global_id)
            result.skipped += 1
            continue

        # Project back to 3-D world frame
        verts_3d = local_2d_to_world(
            tri_result.vertices,
            slab.placement_matrix,
            elevation=0.0,
        )

        mesh = SlabMesh(
            global_id=slab.global_id,
            name=slab.name,
            vertices=verts_3d,
            faces=tri_result.faces,
            area=tri_result.area,
            num_steiner=tri_result.num_steiner,
            num_openings=len(slab.openings),
        )
        result.meshes.append(mesh)

    return result


def triangulate_ifc_file(
    ifc_path: str | Path,
    output_dir: str | Path | None = None,
    fmt: ExportFormat = "obj",
    quality: bool = True,
    min_angle: float = 20.0,
    max_area: float | None = None,
) -> PipelineResult:
    """Parse an IFC file and triangulate all slab elements.

    Parameters
    ----------
    ifc_path:
        Path to the ``.ifc`` file.
    output_dir:
        Directory to write mesh files. If None, no files are written.
    fmt:
        Export format: ``"obj"``, ``"ply"``, ``"npz"``, or ``"none"``.
    quality:
        Enable quality triangulation (Ruppert's algorithm).
    min_angle:
        Minimum interior angle in degrees.
    max_area:
        Maximum triangle area in m². None = unlimited.

    Returns
    -------
    PipelineResult
    """
    ifc_path = Path(ifc_path)
    slabs = load_slabs(ifc_path)

    result = triangulate_slabs(slabs, quality=quality, min_angle=min_angle, max_area=max_area)
    result.ifc_path = str(ifc_path)

    if output_dir is not None and fmt != "none" and result.meshes:
        _export_meshes(result.meshes, Path(output_dir), fmt)

    logger.info(
        "Pipeline complete: %d meshes, %d skipped, total_area=%.2f m², total_triangles=%d",
        len(result.meshes), result.skipped, result.total_area, result.total_triangles,
    )
    return result


def _export_meshes(
    meshes: list[SlabMesh],
    output_dir: Path,
    fmt: ExportFormat,
) -> None:
    from ifc_slab_mesh import export

    output_dir.mkdir(parents=True, exist_ok=True)
    writers = {
        "obj": (export.to_obj, ".obj"),
        "ply": (export.to_ply, ".ply"),
        "npz": (export.to_npz, ".npz"),
    }
    writer_fn, ext = writers.get(fmt, (export.to_obj, ".obj"))

    for mesh in meshes:
        safe_name = (mesh.name or mesh.global_id).replace(" ", "_").replace("/", "_")
        out_path = output_dir / f"{safe_name}{ext}"
        if fmt == "obj":
            writer_fn(mesh.vertices, mesh.faces, out_path, name=mesh.name)  # type: ignore[call-arg]
        else:
            writer_fn(mesh.vertices, mesh.faces, out_path)
        logger.info("Wrote %s (%d triangles, %.2f m²)", out_path.name, len(mesh.faces), mesh.area)
