"""
Benchmark: triangulate many large slabs with openings.

Generates a synthetic load of N slabs of varying sizes, each with 0–4 openings,
and measures throughput in triangles/second and m²/second.

Usage:
    uv run python benchmarks/bench_large.py
    uv run pytest benchmarks/bench_large.py --benchmark-only
"""

from __future__ import annotations

import time
import random
import numpy as np

from ifc_slab_mesh.geometry import build_triangulation_input
from ifc_slab_mesh.triangulate import triangulate_polygon


def _random_slab(
    rng: random.Random,
    min_dim: float = 5.0,
    max_dim: float = 40.0,
    n_openings: int = 0,
):
    """Return a random rectangular slab profile with n_openings interior holes."""
    w = rng.uniform(min_dim, max_dim)
    h = rng.uniform(min_dim, max_dim)
    boundary = np.array([[0, 0], [w, 0], [w, h], [0, h]], dtype=float)

    openings = []
    for _ in range(n_openings):
        ow = rng.uniform(0.5, min(2.0, w * 0.3))
        oh = rng.uniform(0.5, min(2.0, h * 0.3))
        cx = rng.uniform(ow, w - ow)
        cy = rng.uniform(oh, h - oh)
        op = np.array([
            [cx - ow/2, cy - oh/2], [cx + ow/2, cy - oh/2],
            [cx + ow/2, cy + oh/2], [cx - ow/2, cy + oh/2],
        ], dtype=float)
        openings.append(op)

    return boundary, openings


def run_benchmark(n_slabs: int = 200, seed: int = 42) -> dict:
    rng = random.Random(seed)
    total_tris = 0
    total_area = 0.0
    failures = 0

    t0 = time.perf_counter()

    for i in range(n_slabs):
        n_op = rng.randint(0, 3)
        boundary, openings = _random_slab(rng, n_openings=n_op)
        ti = build_triangulation_input(boundary, openings)
        if ti is None:
            failures += 1
            continue
        result = triangulate_polygon(ti, quality=True, min_angle=20.0)
        if result is None:
            failures += 1
            continue
        total_tris += len(result.faces)
        total_area += result.area

    elapsed = time.perf_counter() - t0

    stats = {
        "n_slabs": n_slabs,
        "n_failures": failures,
        "total_triangles": total_tris,
        "total_area_m2": round(total_area, 2),
        "elapsed_s": round(elapsed, 3),
        "tris_per_second": round(total_tris / elapsed) if elapsed > 0 else 0,
        "m2_per_second": round(total_area / elapsed, 1) if elapsed > 0 else 0,
    }
    return stats


if __name__ == "__main__":
    import json
    print("Running benchmark: 200 random slabs with up to 3 openings each...")
    stats = run_benchmark(n_slabs=200)
    print(json.dumps(stats, indent=2))
    print(f"\nThroughput: {stats['tris_per_second']:,} triangles/s, "
          f"{stats['m2_per_second']:,.0f} m²/s")


# ─── pytest-benchmark harness ─────────────────────────────────────────────────

def test_benchmark_200_slabs(benchmark):
    """Benchmark 200 random slabs; stored in .benchmarks/ for tracking."""
    result = benchmark(run_benchmark, n_slabs=200)
    assert result["n_failures"] == 0
    assert result["total_triangles"] > 1000
