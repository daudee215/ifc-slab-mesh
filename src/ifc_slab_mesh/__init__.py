# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Daud Tasleem
"""
ifc-slab-mesh: Constraint-preserving Delaunay triangulation of IFC slab geometries.

Parses IFC files, extracts IfcSlab boundary profiles and associated
IfcOpeningElement hole polygons, and produces watertight triangular meshes
using constrained Delaunay triangulation (Shewchuk's Triangle library).

Outputs: OBJ, PLY, or raw numpy arrays.
"""

__version__ = "0.1.0"
__all__ = ["triangulate_ifc_file", "triangulate_slabs"]

from ifc_slab_mesh.pipeline import triangulate_ifc_file, triangulate_slabs
