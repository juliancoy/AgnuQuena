#!/usr/bin/env python3
"""Validate rendered AgnuQuena case STL files.

These tests intentionally inspect the exported meshes, not only the OpenSCAD
source, so they catch render regressions before slicing.
"""

from __future__ import annotations

import math
import struct
from collections import defaultdict, deque
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

EXPECTED = {
    "QuenaCaseBottom.stl": {
        "size": (250.0, 97.0, 19.3),
        "min_triangles": 700,
        "max_components": 2,
    },
    "QuenaCaseLid.stl": {
        "size": (250.0, 97.0, 17.7),
        "min_triangles": 1200,
        "max_components": 4,
    },
}


def read_stl_triangles(path: Path) -> list[tuple[tuple[float, float, float], ...]]:
    data = path.read_bytes()
    if data.startswith(b"solid"):
        return read_ascii_stl(path)
    return read_binary_stl(data)


def read_ascii_stl(path: Path) -> list[tuple[tuple[float, float, float], ...]]:
    vertices: list[tuple[float, float, float]] = []
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line.startswith("vertex "):
            continue
        _, x, y, z = line.split()
        vertices.append((float(x), float(y), float(z)))

    if len(vertices) % 3 != 0:
        raise AssertionError(f"{path.name}: vertex count is not divisible by 3")

    return [
        (vertices[i], vertices[i + 1], vertices[i + 2])
        for i in range(0, len(vertices), 3)
    ]


def read_binary_stl(data: bytes) -> list[tuple[tuple[float, float, float], ...]]:
    if len(data) < 84:
        raise AssertionError("binary STL is too small")

    triangle_count = struct.unpack("<I", data[80:84])[0]
    expected_size = 84 + triangle_count * 50
    if len(data) != expected_size:
        raise AssertionError(
            f"binary STL length mismatch: expected {expected_size}, got {len(data)}"
        )

    triangles = []
    offset = 84
    for _ in range(triangle_count):
        offset += 12
        tri = []
        for _ in range(3):
            tri.append(struct.unpack("<fff", data[offset : offset + 12]))
            offset += 12
        offset += 2
        triangles.append(tuple(tri))
    return triangles


def bounds(
    triangles: list[tuple[tuple[float, float, float], ...]]
) -> tuple[tuple[float, float, float], tuple[float, float, float]]:
    points = [point for triangle in triangles for point in triangle]
    mins = tuple(min(point[i] for point in points) for i in range(3))
    maxs = tuple(max(point[i] for point in points) for i in range(3))
    return mins, maxs


def component_count(
    triangles: list[tuple[tuple[float, float, float], ...]], tolerance: float = 0.001
) -> int:
    def key(point: tuple[float, float, float]) -> tuple[int, int, int]:
        return tuple(round(coord / tolerance) for coord in point)

    vertex_to_triangles: dict[tuple[int, int, int], list[int]] = defaultdict(list)
    for tri_index, triangle in enumerate(triangles):
        for point in triangle:
            vertex_to_triangles[key(point)].append(tri_index)

    neighbors: list[set[int]] = [set() for _ in triangles]
    for linked_triangles in vertex_to_triangles.values():
        for tri_index in linked_triangles:
            neighbors[tri_index].update(linked_triangles)

    remaining = set(range(len(triangles)))
    components = 0
    while remaining:
        components += 1
        queue = deque([remaining.pop()])
        while queue:
            current = queue.popleft()
            for neighbor in neighbors[current]:
                if neighbor in remaining:
                    remaining.remove(neighbor)
                    queue.append(neighbor)
    return components


def assert_close(actual: float, expected: float, label: str, tolerance: float = 0.15) -> None:
    if not math.isclose(actual, expected, abs_tol=tolerance):
        raise AssertionError(f"{label}: expected {expected:.2f}, got {actual:.2f}")


def main() -> None:
    for name, expected in EXPECTED.items():
        path = ROOT / name
        if not path.exists():
            raise AssertionError(f"{name}: missing; render it with openscad first")
        if path.stat().st_size < 10_000:
            raise AssertionError(f"{name}: unexpectedly small STL")

        triangles = read_stl_triangles(path)
        if len(triangles) < expected["min_triangles"]:
            raise AssertionError(
                f"{name}: expected at least {expected['min_triangles']} triangles, "
                f"got {len(triangles)}"
            )

        mins, maxs = bounds(triangles)
        size = tuple(maxs[i] - mins[i] for i in range(3))
        for axis, actual, target in zip("xyz", size, expected["size"]):
            assert_close(actual, target, f"{name} {axis} size")

        components = component_count(triangles)
        if components > expected["max_components"]:
            raise AssertionError(
                f"{name}: expected no more than {expected['max_components']} "
                f"connected mesh components, got {components}"
            )

        print(
            f"{name}: ok, {len(triangles)} triangles, "
            f"{size[0]:.1f} x {size[1]:.1f} x {size[2]:.1f} mm, "
            f"{components} components"
        )


if __name__ == "__main__":
    main()
