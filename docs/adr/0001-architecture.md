# ADR 0001: Triangulation Library and Algorithm Choice

**Date:** 2026-04-28  
**Status:** Accepted  
**Deciders:** Daud Tasleem

---

## Context

`ifc-slab-mesh` must triangulate 2-D polygons with interior holes (representing IFC slabs with openings).
The triangulation must:

1. Respect constraint edges — no edge in the output may cross a boundary or opening boundary.
2. Produce watertight meshes suitable for structural analysis and rendering.
3. Be available as a Python package with no native build toolchain required from the user.
4. Support quality refinement (no small angles) for downstream FEA use.

---

## Decision

**Use Shewchuk's Triangle library via the `triangle` Python package.**

- `triangle.triangulate(data, 'pq20z')` performs constrained Delaunay triangulation
  with Ruppert's quality refinement, respecting all segment constraints.
- The `triangle` wheel ships a pre-compiled C extension — no user compile step.
- Holes are specified as a single interior point per hole region; Triangle flood-fills
  from that point to eliminate triangles inside the hole.

---

## Consequences

- **Positive:** Correct constraint handling, proven numerical robustness (peer-reviewed algorithm),
  quality refinement out of the box, ~10 µs per triangle on modern hardware.
- **Positive:** Python wheel available on PyPI; no CGAL, CMake, or Conda required.
- **Negative:** Triangle is 2-D only — 3-D slabs must be projected to a local plane first
  (handled in `geometry.py`).
- **Negative:** License is custom (Jonathan Shewchuk's Triangle is free for non-commercial use;
  this is noted in NOTICE.md and the README).

---

## Rejected Alternatives

### Alternative 1: CGAL 3D Constrained Triangulations (C++, CGAL 6.1+)

CGAL is the gold standard for computational geometry. Its new 3D constrained triangulation
package (announced 2025) handles the 3-D case directly, eliminating the projection step.

**Rejected because:**
- No maintained Python bindings for the 3D CT package as of April 2026.
- The CGAL wheel (`cgal-python`) covers only 2-D operations; 3-D requires building from source.
- Adding a build dependency on CGAL would break pip-installability for most users.
- The projection approach (2-D → triangulate → 3-D) is correct for planar slabs and avoids
  the added complexity.

### Alternative 2: Mapbox Earcut (via `earcut-python`)

Earcut is a fast, pure-JS (and Python-wrapped) polygon triangulator used in web mapping.

**Rejected because:**
- Earcut does **not** support constrained segment inputs; it only handles holes via the
  standard Earcut API. Boundary edges are not guaranteed to appear in the output mesh.
- For slabs with complex opening shapes, Earcut can generate triangles that cross
  opening boundaries, producing incorrect meshes.

### Alternative 3: Scipy Delaunay (scipy.spatial.Delaunay)

SciPy provides a fast Delaunay triangulation but without constraint support.

**Rejected because:**
- `scipy.spatial.Delaunay` ignores user-specified segment constraints.
- Triangles inside holes must be manually removed by a point-in-polygon pass,
  which is unreliable for concave boundaries and nested holes.
- No quality refinement; results may contain very thin slivers.

---

## References

- Shewchuk, J.R. (1996). "Triangle: Engineering a 2D Quality Mesh Generator and Delaunay Triangulator." *Applied Computational Geometry*.
- CGAL 3D Constrained Triangulations announcement: https://www.cgal.org/2025/06/30/Constrained_triangulation_3/
- triangle Python package: https://pypi.org/project/triangle/
