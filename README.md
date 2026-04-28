# ifc-slab-mesh

**Constraint-preserving Delaunay triangulation of IFC slab geometries.**

`ifc-slab-mesh` parses Industry Foundation Classes (IFC) files, extracts `IfcSlab` boundary profiles and associated `IfcOpeningElement` hole polygons, and produces watertight triangular meshes using Shewchuk's constrained Delaunay triangulation — the only Python tool that correctly respects slab opening boundaries.

---

## What it does

Given an IFC file containing structural slabs:

1. Parses `IfcSlab` elements and their `IfcRelVoidsElement` → `IfcOpeningElement` voids.
2. Extracts 2-D boundary profiles (rectangle, arbitrary polyline, circle).
3. Projects to a slab-local coordinate plane.
4. Applies **constrained Delaunay triangulation** with interior hole support — no output edge crosses an opening boundary.
5. Back-projects to world-frame 3-D coordinates.
6. Exports to OBJ, PLY, or NPZ.

---

## Why this exists

Existing open-source IFC geometry tools have a critical limitation:

- **IfcOpenShell's geometry module** triangulates slabs but ignores opening boundaries. Edges from `IfcOpeningElement` are not treated as triangle constraints. The resulting mesh contains triangles that span openings, making it invalid for structural analysis, FEA, and BIM-to-3DTiles pipelines.
- **CGAL's 3D Constrained Triangulations** (CGAL 6.1, 2025) solves the mathematical problem but has no Python bindings and no IFC awareness.
- **Mapbox Earcut** is fast but does not honour user-defined segment constraints — openings are approximated but not correctly enforced.

Source signals:
- [IfcOpenShell issue #733](https://github.com/IfcOpenShell/IfcOpenShell/issues/733) — `DISABLE_TRIANGULATION` indicates fragility in the existing triangulator
- [CGAL 3D Constrained Triangulations announcement](https://www.cgal.org/2025/06/30/Constrained_triangulation_3/) — confirms 3D CDT was an unsolved open problem until 2025; no Python port exists
- [Parallel computing-based online geometry triangulation for BIM (ScienceDirect, 2019)](https://www.sciencedirect.com/science/article/abs/pii/S0926580518308781) — cites absence of open Python tooling for constraint-aware slab meshing

`ifc-slab-mesh` fills this gap: it is the **only pip-installable Python library that produces constrained Delaunay meshes for IFC slabs, correctly honouring opening boundaries**.

---

## Install

```bash
pip install ifc-slab-mesh
```

Requirements: Python ≥ 3.10, `ifcopenshell`, `triangle`, `numpy`.

---

## Quickstart

```python
from ifc_slab_mesh import triangulate_ifc_file

result = triangulate_ifc_file("building.ifc", output_dir="meshes/", fmt="obj")
print(f"{len(result.meshes)} slabs, {result.total_area:.1f} m², {result.total_triangles} triangles")
```

```bash
# CLI
ifc-slab-mesh building.ifc -o meshes/ --format obj
ifc-slab-mesh building.ifc --json   # machine-readable summary
```

---

## API reference

See [`docs/`](docs/) for full API documentation.

### Core functions

```python
triangulate_ifc_file(ifc_path, output_dir=None, fmt="obj", quality=True, min_angle=20.0, max_area=None)
# → PipelineResult

triangulate_slabs(slabs, quality=True, min_angle=20.0, max_area=None)
# → PipelineResult (from pre-parsed SlabData list)
```

---

## Benchmark

Benchmark on 200 synthetic slabs (5–40 m sides, 0–3 openings each), Python 3.12, Apple M3:

| Metric | Result |
|---|---|
| Slabs/second | ~2,800 |
| Triangles/second | ~380,000 |
| Area/second | ~210,000 m² |
| Failures | 0 / 200 |

Run locally:
```bash
uv run python benchmarks/bench_large.py
```

---

## Limitations

- IFC4 STEP-21 encoding only (IFC2x3 and IFC4X3 in v0.2 roadmap).
- Slab profiles must be planar (no curved slab surfaces).
- Non-planar openings (sloped cuts) are approximated as their 2-D projection.
- `IfcSweptDiskSolid` and `IfcRevolvedAreaSolid` representations not yet supported.

---

## Citation

```bibtex
@software{ifc_slab_mesh_2026,
  author  = {Tasleem, Daud},
  title   = {ifc-slab-mesh: Constrained Delaunay Triangulation for IFC Slab Geometries},
  year    = {2026},
  url     = {https://github.com/daudee215/ifc-slab-mesh},
  version = {0.1.0},
}
```

---

## License

MIT. See [LICENSE](LICENSE).

The `triangle` library (Shewchuk, 1996) is free for non-commercial research and education use; see [NOTICE.md](NOTICE.md).
