# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Daud Tasleem
"""
IFC file parsing: extracts IfcSlab elements and their associated
IfcOpeningElement voids, plus object placement transforms.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class ProfileData:
    """2-D outer boundary polygon of a slab or opening.

    All coordinates are in the local coordinate system of the containing slab
    (origin = slab insertion point, Z = extrusion direction).
    """

    vertices: np.ndarray  # shape (N, 2), float64
    label: str = ""


@dataclass
class SlabData:
    """All geometry data needed to triangulate one IfcSlab."""

    global_id: str
    name: str
    placement_matrix: np.ndarray  # 4×4 homogeneous, float64 — local → world
    profile: ProfileData
    openings: list[ProfileData] = field(default_factory=list)
    extrusion_depth: float = 0.3  # metres, used for 3-D lift if needed


# ─── IFC helpers ─────────────────────────────────────────────────────────────

def _placement_to_matrix(placement: Any) -> np.ndarray:
    """Convert IfcAxis2Placement3D (or nested IfcLocalPlacement) to a 4×4 matrix."""
    m = np.eye(4, dtype=np.float64)
    if placement is None:
        return m

    loc = getattr(placement, "Location", None)
    if loc is not None:
        m[0, 3] = loc.Coordinates[0]
        m[1, 3] = loc.Coordinates[1]
        m[2, 3] = loc.Coordinates[2] if len(loc.Coordinates) > 2 else 0.0

    axis = getattr(placement, "Axis", None)
    ref = getattr(placement, "RefDirection", None)

    if axis is not None and ref is not None:
        z = np.array(axis.DirectionRatios, dtype=np.float64)
        x = np.array(ref.DirectionRatios, dtype=np.float64)
        z /= np.linalg.norm(z) + 1e-15
        x /= np.linalg.norm(x) + 1e-15
        y = np.cross(z, x)
        m[:3, 0] = x
        m[:3, 1] = y
        m[:3, 2] = z

    return m


def _resolve_local_placement(ifc_placement: Any) -> np.ndarray:
    """Recursively accumulate placement transforms up to the world frame."""
    if ifc_placement is None:
        return np.eye(4, dtype=np.float64)
    relative_to = getattr(ifc_placement, "PlacementRelTo", None)
    parent = _resolve_local_placement(relative_to)
    rel_placement = getattr(ifc_placement, "RelativePlacement", None)
    own = _placement_to_matrix(rel_placement)
    return parent @ own


def _profile_vertices(profile: Any) -> np.ndarray:
    """Extract a (N, 2) vertex array from an IfcProfileDef subtype."""
    ifc_type = profile.is_a()

    if ifc_type == "IfcRectangleProfileDef":
        xdim = float(profile.XDim)
        ydim = float(profile.YDim)
        half_x, half_y = xdim / 2.0, ydim / 2.0
        return np.array(
            [[-half_x, -half_y], [half_x, -half_y], [half_x, half_y], [-half_x, half_y]],
            dtype=np.float64,
        )

    if ifc_type in ("IfcArbitraryClosedProfileDef", "IfcArbitraryProfileDefWithVoids"):
        outer = profile.OuterCurve
        return _polyline_vertices(outer)

    if ifc_type == "IfcCircleProfileDef":
        r = float(profile.Radius)
        n = 32
        angles = np.linspace(0, 2 * np.pi, n, endpoint=False)
        return np.column_stack([r * np.cos(angles), r * np.sin(angles)]).astype(np.float64)

    logger.warning("Unsupported profile type: %s — using empty polygon", ifc_type)
    return np.zeros((0, 2), dtype=np.float64)


def _polyline_vertices(curve: Any) -> np.ndarray:
    """Extract (N, 2) vertices from IfcPolyline or IfcCompositeCurve."""
    ifc_type = curve.is_a()
    if ifc_type == "IfcPolyline":
        pts = curve.Points
        coords = [(float(p.Coordinates[0]), float(p.Coordinates[1])) for p in pts]
        # Remove duplicate closing point if present
        if len(coords) > 1 and np.allclose(coords[0], coords[-1]):
            coords = coords[:-1]
        return np.array(coords, dtype=np.float64)
    # Fallback: try to read Points attribute directly
    pts = getattr(curve, "Points", None)
    if pts:
        coords = [(float(p.Coordinates[0]), float(p.Coordinates[1])) for p in pts]
        return np.array(coords, dtype=np.float64)
    logger.warning("Cannot extract vertices from curve type: %s", ifc_type)
    return np.zeros((0, 2), dtype=np.float64)


def _apply_profile_placement_2d(verts: np.ndarray, position: Any) -> np.ndarray:
    """Apply IfcAxis2Placement2D to a (N, 2) vertex array."""
    if position is None or len(verts) == 0:
        return verts
    loc = getattr(position, "Location", None)
    ref = getattr(position, "RefDirection", None)

    dx, dy = (0.0, 0.0)
    if loc is not None:
        dx = float(loc.Coordinates[0])
        dy = float(loc.Coordinates[1])

    cos_a, sin_a = 1.0, 0.0
    if ref is not None:
        r = ref.DirectionRatios
        cos_a, sin_a = float(r[0]), float(r[1])

    rot = np.array([[cos_a, -sin_a], [sin_a, cos_a]], dtype=np.float64)
    return (verts @ rot.T) + np.array([dx, dy])


# ─── Public API ───────────────────────────────────────────────────────────────

def load_slabs(ifc_path: str | Path) -> list[SlabData]:
    """Parse an IFC file and return SlabData for every IfcSlab found.

    Parameters
    ----------
    ifc_path:
        Path to the ``.ifc`` file (STEP-21 encoding).

    Returns
    -------
    list[SlabData]
        One entry per IfcSlab. Slabs with no resolvable profile are skipped
        with a warning.
    """
    try:
        import ifcopenshell  # type: ignore[import]
    except ImportError as exc:
        raise ImportError(
            "ifcopenshell is required: pip install ifcopenshell"
        ) from exc

    model = ifcopenshell.open(str(ifc_path))
    slabs: list[SlabData] = []

    # Build opening → profile lookup
    opening_profiles: dict[str, list[ProfileData]] = {}
    for rel in model.by_type("IfcRelVoidsElement"):
        slab_id = rel.RelatingBuildingElement.GlobalId
        opening = rel.RelatedOpeningElement
        profiles = _extract_element_profiles(opening)
        opening_profiles.setdefault(slab_id, []).extend(profiles)

    for slab in model.by_type("IfcSlab"):
        gid = slab.GlobalId
        name = slab.Name or ""

        # Resolve world placement
        placement_matrix = _resolve_local_placement(getattr(slab, "ObjectPlacement", None))

        # Extract slab profile
        profiles = _extract_element_profiles(slab)
        if not profiles:
            logger.warning("Slab %s (%s): no profile found — skipping", gid, name)
            continue

        slab_data = SlabData(
            global_id=gid,
            name=name,
            placement_matrix=placement_matrix,
            profile=profiles[0],
            openings=opening_profiles.get(gid, []),
        )
        slabs.append(slab_data)
        logger.debug(
            "Slab %s: %d boundary verts, %d openings",
            name or gid,
            len(profiles[0].vertices),
            len(slab_data.openings),
        )

    logger.info("Loaded %d slabs from %s", len(slabs), ifc_path)
    return slabs


def _extract_element_profiles(element: Any) -> list[ProfileData]:
    """Walk the representation tree and extract 2-D profiles."""
    profiles: list[ProfileData] = []
    rep = getattr(element, "Representation", None)
    if rep is None:
        return profiles

    for shape_rep in rep.Representations:
        for item in shape_rep.Items:
            profile = _profile_from_item(item)
            if profile is not None:
                profiles.append(profile)
    return profiles


def _profile_from_item(item: Any) -> ProfileData | None:
    """Extract a ProfileData from a representation item."""
    ifc_type = item.is_a()

    if ifc_type in ("IfcExtrudedAreaSolid", "IfcExtrudedAreaSolidTapered"):
        profile_def = item.SweptArea
        position = getattr(item, "Position", None)
        raw = _profile_vertices(profile_def)
        if len(raw) == 0:
            return None
        # Apply the solid's own 2-D position
        if position is not None:
            placement_2d = getattr(position, "Location", None)
            ref = getattr(position, "RefDirection", None)
            if placement_2d is not None or ref is not None:
                raw = _apply_profile_placement_2d(raw, position)
        return ProfileData(vertices=raw, label=profile_def.is_a())

    if ifc_type == "IfcFacetedBrep":
        # Extract outer boundary from the shell's first face loop
        outer = item.Outer
        bounds = _shell_outer_boundary(outer)
        if bounds is not None:
            return ProfileData(vertices=bounds, label="IfcFacetedBrep")

    return None


def _shell_outer_boundary(shell: Any) -> np.ndarray | None:
    """Extract the 2-D footprint of a closed shell as its largest face polygon."""
    best_area = -1.0
    best_poly: np.ndarray | None = None

    for face in shell.CfsFaces:
        for bound in face.Bounds:
            loop = bound.Bound
            pts_3d = [
                np.array(v.Coordinates[:3], dtype=np.float64)
                for v in loop.Polygon
            ]
            if len(pts_3d) < 3:
                continue
            # Project to 2-D by dropping the axis with least variance
            arr = np.array(pts_3d)
            variances = arr.var(axis=0)
            drop = int(np.argmin(variances))
            axes = [i for i in range(3) if i != drop]
            poly_2d = arr[:, axes]
            area = _polygon_area(poly_2d)
            if area > best_area:
                best_area = area
                best_poly = poly_2d

    return best_poly


def _polygon_area(verts: np.ndarray) -> float:
    """Shoelace formula for signed polygon area."""
    n = len(verts)
    if n < 3:
        return 0.0
    x, y = verts[:, 0], verts[:, 1]
    return abs(float(np.dot(x, np.roll(y, -1)) - np.dot(np.roll(x, -1), y))) / 2.0
