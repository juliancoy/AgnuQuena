#!/usr/bin/env python3
"""Validate rendered AgnuQuena case STL files.

These tests intentionally inspect the exported meshes, not only the OpenSCAD
source, so they catch render regressions before slicing.
"""

from __future__ import annotations

import math
import struct
import subprocess
import tempfile
from collections import defaultdict, deque
from pathlib import Path
from typing import Any

import trimesh


ROOT = Path(__file__).resolve().parents[1]

EXPECTED = {
    "QuenaCaseBottom.stl": {
        "size": (257.6, 68.0, 23.65),
        "min_triangles": 2200,
        "max_components": 4,
    },
    "QuenaCaseLid.stl": {
        "size": (257.6, 69.07, 17.85),
        "min_triangles": 1200,
        "max_components": 4,
    },
    "QuenaCaseHingeCoupon.stl": {
        "size": (58.0, 54.0, 14.2),
        "min_triangles": 3000,
        "max_components": 6,
    },
    "QuenaCaseFullHingeCoupon.stl": {
        "size": (239.6, 56.0, 13.2),
        "min_triangles": 5000,
        "max_components": 12,
    },
    "QuenaCaseLatch.stl": {
        "size": (56.0, 8.3, 11.55),
        "min_triangles": 1200,
        "max_components": 1,
    },
    "QuenaCaseLatchCoupon.stl": {
        "size": (74.0, 9.55, 12.2),
        "min_triangles": 1600,
        "max_components": 1,
    },
    "QuenaCaseAssembly.stl": {
        "size": (257.6, 72.22, 37.0),
        "min_triangles": 4500,
        "max_components": 6,
    },
}

HINGE_OUTER_D = 6.2
HINGE_AXIS_Y = -31.7
HINGE_AXIS_Z = 22.25
LID_CLOSED_Z = 19.45
LID_SWEEP_MAX_DEG = 140
CONTACT_TOLERANCE_MM = 0.05
CLOSED_OVERLAP_VOLUME_TOLERANCE_MM3 = 0.1


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


def rotate_x(point: tuple[float, float, float], radians: float) -> tuple[float, float, float]:
    x, y, z = point
    c = math.cos(radians)
    s = math.sin(radians)
    return (x, y * c - z * s, y * s + z * c)


def add_points(
    left: tuple[float, float, float], right: tuple[float, float, float]
) -> tuple[float, float, float]:
    return tuple(left[i] + right[i] for i in range(3))


def subtract_points(
    left: tuple[float, float, float], right: tuple[float, float, float]
) -> tuple[float, float, float]:
    return tuple(left[i] - right[i] for i in range(3))


def write_obj(
    path: Path, triangles: list[tuple[tuple[float, float, float], ...]]
) -> None:
    with path.open("w") as file:
        for triangle in triangles:
            for x, y, z in triangle:
                file.write(f"v {x:.6f} {y:.6f} {z:.6f}\n")
        for index in range(len(triangles)):
            first_vertex = index * 3 + 1
            file.write(
                f"f {first_vertex} {first_vertex + 1} {first_vertex + 2}\n"
            )


def run_closed_overlap_check() -> None:
    with tempfile.TemporaryDirectory(prefix="quena_case_overlap_") as temp_dir:
        temp_path = Path(temp_dir)
        scad_path = temp_path / "closed_overlap.scad"
        overlap_stl = temp_path / "closed_overlap.stl"
        scad_path.write_text(
            f"""
include <{ROOT / "QuenaCase.scad"}>;
intersection() {{
  bottom_assembly();
  translate([0, 0, lid_closed_z]) lid_assembly();
}}
""".lstrip(),
            encoding="utf-8",
        )
        result = subprocess.run(
            [
                "openscad",
                "-D",
                'part="none"',
                "-o",
                str(overlap_stl),
                str(scad_path),
            ],
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        if "Current top level object is empty" in result.stdout:
            print("QuenaCase closed overlap: ok, OpenSCAD intersection is empty")
            return
        if result.returncode:
            raise AssertionError(
                "QuenaCase closed overlap: OpenSCAD failed\n" + result.stdout
            )
        if not overlap_stl.exists() or overlap_stl.stat().st_size <= 84:
            print("QuenaCase closed overlap: ok, OpenSCAD intersection is empty")
            return

        overlap = trimesh.load(overlap_stl, force="mesh")
        volume = abs(float(overlap.volume))
        if volume > CLOSED_OVERLAP_VOLUME_TOLERANCE_MM3:
            raise AssertionError(
                "QuenaCase closed overlap: "
                f"{volume:.3f} mm^3 intersection, bounds={overlap.bounds.tolist()}"
            )

        print(f"QuenaCase closed overlap: ok, {volume:.3f} mm^3")


def run_mesh_checks() -> None:
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


def run_hinge_sweep_check() -> None:
    try:
        import pybullet as p
    except ImportError:
        print("QuenaCase hinge sweep: skipped, install pybullet to enable")
        return

    bottom_path = ROOT / "QuenaCaseBottom.stl"
    lid_path = ROOT / "QuenaCaseLid.stl"
    for path in (bottom_path, lid_path):
        if not path.exists():
            raise AssertionError(f"{path.name}: missing; render it with openscad first")

    bottom_triangles = read_stl_triangles(bottom_path)
    lid_triangles = read_stl_triangles(lid_path)
    hinge_axis = (0.0, HINGE_AXIS_Y, HINGE_AXIS_Z)
    closed_lid_position = (0.0, 0.0, LID_CLOSED_Z)

    physics_client = p.connect(p.DIRECT)
    try:
        p.setGravity(0, 0, -9.81)
        p.setPhysicsEngineParameter(
            contactBreakingThreshold=CONTACT_TOLERANCE_MM,
            deterministicOverlappingPairs=1,
        )

        with tempfile.TemporaryDirectory(prefix="quena_case_mesh_") as temp_dir:
            temp_path = Path(temp_dir)
            bottom_obj = temp_path / "bottom.obj"
            lid_obj = temp_path / "lid.obj"
            write_obj(bottom_obj, bottom_triangles)
            write_obj(lid_obj, lid_triangles)

            mesh_flags = p.GEOM_FORCE_CONCAVE_TRIMESH
            bottom_collision = p.createCollisionShape(
                p.GEOM_MESH,
                fileName=str(bottom_obj),
                flags=mesh_flags,
            )
            lid_collision = p.createCollisionShape(
                p.GEOM_MESH,
                fileName=str(lid_obj),
                flags=mesh_flags,
            )

            bottom_body = p.createMultiBody(
                baseMass=0,
                baseCollisionShapeIndex=bottom_collision,
                basePosition=[0, 0, 0],
            )
            lid_body = p.createMultiBody(
                baseMass=0,
                baseCollisionShapeIndex=lid_collision,
                basePosition=closed_lid_position,
            )

            for deg in range(LID_SWEEP_MAX_DEG + 1):
                radians = math.radians(deg)
                hinge_to_lid = subtract_points(closed_lid_position, hinge_axis)
                lid_position = add_points(hinge_axis, rotate_x(hinge_to_lid, radians))
                lid_orientation = p.getQuaternionFromEuler([radians, 0, 0])

                p.resetBasePositionAndOrientation(lid_body, lid_position, lid_orientation)
                p.performCollisionDetection()

                penetrating_contacts: list[Any] = [
                    contact
                    for contact in p.getContactPoints(bottom_body, lid_body)
                    if contact[8] <= -CONTACT_TOLERANCE_MM
                ]
                if penetrating_contacts:
                    deepest = min(contact[8] for contact in penetrating_contacts)
                    raise AssertionError(
                        "QuenaCase hinge sweep: collision at "
                        f"{deg} deg, {len(penetrating_contacts)} contacts, "
                        f"deepest penetration {-deepest:.3f} mm"
                    )

        print(
            "QuenaCase hinge sweep: ok, "
            f"0-{LID_SWEEP_MAX_DEG} deg around "
            f"({hinge_axis[0]:.2f}, {hinge_axis[1]:.2f}, {hinge_axis[2]:.2f})"
        )
    finally:
        p.disconnect(physics_client)


def main() -> None:
    run_mesh_checks()
    run_closed_overlap_check()
    run_hinge_sweep_check()


if __name__ == "__main__":
    main()
