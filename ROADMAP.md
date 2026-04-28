# ROADMAP

## v0.1 — Current

- [x] Parse IfcSlab boundary profiles (IfcRectangleProfileDef, IfcArbitraryClosedProfileDef, IfcCircleProfileDef)
- [x] Parse IfcOpeningElement holes via IfcRelVoidsElement
- [x] Constrained Delaunay triangulation with interior hole support (Shewchuk's Triangle)
- [x] Quality refinement with configurable minimum angle (default 20°)
- [x] Export to OBJ, PLY, NPZ
- [x] CLI: `ifc-slab-mesh <file.ifc>`
- [x] JSON output mode for pipeline integration
- [x] Unit + integration tests
- [x] Benchmark suite

## v0.2 — Next (target: 2026-Q3)

- [ ] Support IfcArbitraryProfileDefWithVoids (slabs with inline void polygons)
- [ ] Handle IfcSweptDiskSolid and IfcRevolvedAreaSolid representations
- [ ] Support IFC2x3 files (currently IFC4 only)
- [ ] Batch processing: triangulate all slabs in a directory
- [ ] glTF export via trimesh integration
- [ ] Parallel processing with multiprocessing (one worker per slab)
- [ ] Per-triangle normal vectors in output mesh
- [ ] Coordinate reference system metadata in output headers

## v1.0 — Stable (target: 2027-Q1)

- [ ] Full IFC4X3 support
- [ ] IfcGeometricRepresentationContext-aware placement
- [ ] 3-D constraint triangulation for non-planar slabs (CGAL 3D CT when Python bindings mature)
- [ ] FEA mesh quality report (aspect ratio, skewness histograms)
- [ ] QGIS plugin wrapper
- [ ] Comprehensive benchmark suite against 50+ real-world IFC files (buildingSMART dataset)
- [ ] Conda-forge package
