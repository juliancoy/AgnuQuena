#!/usr/bin/env python3
"""Prepare a Vulkan-backed 3D acoustic FDTD simulation for an STL model.

The script currently performs the deterministic setup stages that are easy to
verify in this repo: compile the Vulkan compute shader, read the STL, estimate
the simulation grid, and write a run manifest. The shader is the compute kernel
used by the next stage that dispatches timesteps on a Vulkan queue.
"""

from __future__ import annotations

import argparse
import collections.abc
import json
import math
import struct
import subprocess
import sys
from pathlib import Path

import vulkan as vk


def vulkan_devices() -> list[str]:
    app = vk.VkApplicationInfo(
        sType=vk.VK_STRUCTURE_TYPE_APPLICATION_INFO,
        pApplicationName="AgnuQuena acoustic setup",
        applicationVersion=1,
        pEngineName="AgnuQuena",
        engineVersion=1,
        apiVersion=vk.VK_API_VERSION_1_0,
    )
    create_info = vk.VkInstanceCreateInfo(
        sType=vk.VK_STRUCTURE_TYPE_INSTANCE_CREATE_INFO,
        pApplicationInfo=app,
    )
    instance = vk.vkCreateInstance(create_info, None)
    try:
        devices = vk.vkEnumeratePhysicalDevices(instance)
        return [vk.vkGetPhysicalDeviceProperties(device).deviceName for device in devices]
    finally:
        vk.vkDestroyInstance(instance, None)


def read_stl_bounds(path: Path) -> tuple[tuple[float, float, float], tuple[float, float, float], int]:
    data = path.read_bytes()
    triangles: list[tuple[float, float, float]] = []

    if len(data) >= 84:
        tri_count = struct.unpack_from("<I", data, 80)[0]
        expected = 84 + tri_count * 50
        if expected == len(data):
            offset = 84
            for _ in range(tri_count):
                offset += 12
                for _vertex in range(3):
                    triangles.append(struct.unpack_from("<fff", data, offset))
                    offset += 12
                offset += 2
            return bounds_for(triangles, tri_count)

    text = data.decode("utf-8", errors="ignore")
    tri_count = 0
    for line in text.splitlines():
        parts = line.strip().split()
        if len(parts) == 4 and parts[0] == "vertex":
            triangles.append(tuple(float(p) for p in parts[1:4]))
        elif len(parts) >= 2 and parts[0] == "endfacet":
            tri_count += 1
    return bounds_for(triangles, tri_count)


def bounds_for(vertices: list[tuple[float, float, float]], triangles: int):
    if not vertices:
        raise ValueError("STL contains no vertices")
    mins = tuple(min(vertex[i] for vertex in vertices) for i in range(3))
    maxs = tuple(max(vertex[i] for vertex in vertices) for i in range(3))
    return mins, maxs, triangles


def compile_shader(shader: Path, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["glslc", str(shader), "-o", str(output)], check=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stl", default="Quena.stl", help="STL model to simulate")
    parser.add_argument("--cell-mm", type=float, default=8.0, help="voxel edge length in millimeters")
    parser.add_argument("--padding-mm", type=float, default=12.0, help="air padding around the model")
    parser.add_argument("--sample-rate", type=float, default=96000.0, help="output sample rate")
    parser.add_argument("--steps", type=int, default=96000, help="simulation timesteps")
    parser.add_argument("--out-dir", default="acoustics/out", help="output directory")
    args = parser.parse_args()

    stl = Path(args.stl)
    out_dir = Path(args.out_dir)
    shader = Path(__file__).resolve().parent / "shaders" / "fdtd.comp"
    spirv = out_dir / "fdtd.comp.spv"

    compile_shader(shader, spirv)
    devices = vulkan_devices()
    mins, maxs, triangles = read_stl_bounds(stl)

    padded_min = tuple(value - args.padding_mm for value in mins)
    padded_max = tuple(value + args.padding_mm for value in maxs)
    spans = tuple(padded_max[i] - padded_min[i] for i in range(3))
    grid = tuple(max(1, math.ceil(span / args.cell_mm)) for span in spans)
    cells = grid[0] * grid[1] * grid[2]

    speed_of_sound_mm_s = 343000.0
    dt = 1.0 / args.sample_rate
    courant = speed_of_sound_mm_s * dt / args.cell_mm
    stable_limit = 1.0 / math.sqrt(3.0)

    manifest = {
        "stl": str(stl),
        "shader_spirv": str(spirv),
        "vulkan_devices": devices,
        "triangles": triangles,
        "bounds_mm": {"min": padded_min, "max": padded_max},
        "cell_mm": args.cell_mm,
        "grid": {"nx": grid[0], "ny": grid[1], "nz": grid[2], "cells": cells},
        "sample_rate": args.sample_rate,
        "steps": args.steps,
        "courant": courant,
        "courant_stable_limit": stable_limit,
        "stable": courant <= stable_limit,
        "note": "Use cell_mm small enough for the shortest wavelength and sample_rate low enough to satisfy the 3D FDTD Courant limit.",
    }

    out_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = out_dir / "simulation_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    print(f"compiled {spirv}")
    print(f"vulkan devices: {', '.join(devices)}")
    print(f"wrote {manifest_path}")
    print(f"grid {grid[0]}x{grid[1]}x{grid[2]} ({cells:,} cells), courant={courant:.3f}")
    if courant > stable_limit:
        print(
            "warning: unstable Courant number for 3D FDTD; "
            f"use --cell-mm >= {speed_of_sound_mm_s * dt / stable_limit:.2f} "
            f"or --sample-rate >= {speed_of_sound_mm_s / (args.cell_mm * stable_limit):.0f}",
            file=sys.stderr,
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
