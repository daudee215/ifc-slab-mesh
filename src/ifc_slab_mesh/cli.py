# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Daud Tasleem
"""Command-line interface for ifc-slab-mesh."""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path


def _configure_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(format="%(levelname)s %(name)s: %(message)s", level=level)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="ifc-slab-mesh",
        description=(
            "Triangulate IfcSlab elements from an IFC file using constrained "
            "Delaunay triangulation that respects IfcOpeningElement boundaries."
        ),
    )
    parser.add_argument("ifc_file", type=Path, help="Input .ifc file")
    parser.add_argument(
        "-o", "--output-dir", type=Path, default=None,
        help="Directory to write mesh files (default: none)",
    )
    parser.add_argument(
        "--format", choices=["obj", "ply", "npz", "none"], default="obj",
        help="Output format (default: obj)",
    )
    parser.add_argument(
        "--no-quality", action="store_true",
        help="Disable quality refinement (faster but lower-quality meshes)",
    )
    parser.add_argument(
        "--min-angle", type=float, default=20.0,
        help="Minimum interior angle in degrees (default: 20)",
    )
    parser.add_argument(
        "--max-area", type=float, default=None,
        help="Maximum triangle area in m² (default: none)",
    )
    parser.add_argument("-v", "--verbose", action="store_true")
    parser.add_argument("--json", action="store_true", help="Output result as JSON")

    args = parser.parse_args(argv)
    _configure_logging(args.verbose)

    from ifc_slab_mesh.pipeline import triangulate_ifc_file

    if not args.ifc_file.exists():
        print(f"error: file not found: {args.ifc_file}", file=sys.stderr)
        return 1

    result = triangulate_ifc_file(
        args.ifc_file,
        output_dir=args.output_dir,
        fmt=args.format,
        quality=not args.no_quality,
        min_angle=args.min_angle,
        max_area=args.max_area,
    )

    if args.json:
        summary = {
            "ifc_path": result.ifc_path,
            "meshes": [
                {
                    "global_id": m.global_id,
                    "name": m.name,
                    "num_vertices": len(m.vertices),
                    "num_faces": len(m.faces),
                    "area_m2": round(m.area, 4),
                    "num_steiner": m.num_steiner,
                    "num_openings": m.num_openings,
                }
                for m in result.meshes
            ],
            "skipped": result.skipped,
            "total_area_m2": round(result.total_area, 4),
            "total_triangles": result.total_triangles,
        }
        print(json.dumps(summary, indent=2))
    else:
        print(f"Processed: {result.ifc_path}")
        print(f"  Slabs meshed : {len(result.meshes)}")
        print(f"  Slabs skipped: {result.skipped}")
        print(f"  Total area   : {result.total_area:.2f} m²")
        print(f"  Total tris   : {result.total_triangles}")
        for m in result.meshes:
            print(
                f"  [{m.name or m.global_id}] "
                f"{len(m.faces)} tris, {m.area:.2f} m², "
                f"{m.num_openings} openings, {m.num_steiner} Steiner pts"
            )

    return 0


if __name__ == "__main__":
    sys.exit(main())
