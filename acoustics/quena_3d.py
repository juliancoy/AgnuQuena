#!/usr/bin/env python3
"""Run a 3D scalar-pressure FDTD simulation for the AgnuQuena bore.

This is a CPU reference implementation of the fluid/acoustic model the Vulkan
path is meant to accelerate later. It uses the current OpenSCAD dimensions to
build a cylindrical air column, reflective bore walls, pressure-release openings,
an impulse source, receiver samples, and FFT-derived pitch estimates.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import trimesh

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from acoustics.quena_1d import (  # noqa: E402
    NOTE_ORDER,
    SPEED_OF_SOUND_MM_S,
    TARGET_HZ,
    geometry_from_scad,
    hz_to_cents,
    measurements_from_markdown,
)
from acoustics.materials import (  # noqa: E402
    apply_material_to_geometry,
    canonical_material_keys,
    material_keys,
    material_profile,
)


@dataclass(frozen=True)
class Opening:
    note: str
    source: str
    acoustic_mm: float
    diameter_mm: float
    physical_mm: float


def fingering_openings(geometry) -> list[Opening]:
    open_end_physical = geometry.acoustic_length_mm + geometry.unacoustic_length_mm
    openings = [Opening("G4", "open_end", geometry.acoustic_length_mm, 0.0, open_end_physical)]
    for hole in geometry.holes:
        physical_mm = hole.acoustic_mm - geometry.mouthpiece_active_length_mm + geometry.z_adjust_mm
        openings.append(Opening(hole.note, f"hole_{hole.name}", hole.acoustic_mm, hole.diameter_mm, physical_mm))
    openings.append(Opening("G5", "first_overtone", geometry.acoustic_length_mm, 0.0, open_end_physical))
    return sorted(openings, key=lambda opening: NOTE_ORDER.index(opening.note))


def gaussian_source(step: int, width_steps: float = 10.0) -> float:
    center = 4.0 * width_steps
    t = (step - center) / width_steps
    return float((1.0 - 2.0 * t * t) * math.exp(-t * t))


def make_bore_mask(nz: int, ny: int, nx: int, cell_mm: float, bore_diameter_mm: float) -> np.ndarray:
    cy = (ny - 1) / 2.0
    cx = (nx - 1) / 2.0
    y = (np.arange(ny) - cy) * cell_mm
    x = (np.arange(nx) - cx) * cell_mm
    yy, xx = np.meshgrid(y, x, indexing="ij")
    cross_section = (xx * xx + yy * yy) <= (bore_diameter_mm / 2.0) ** 2
    return np.broadcast_to(cross_section, (nz, ny, nx)).copy()


def load_air_mask_from_stl(path: Path, cell_mm: float) -> tuple[np.ndarray, tuple[float, float, float]]:
    mesh = trimesh.load(path, force="mesh")
    if not mesh.is_watertight:
        raise SystemExit(f"{path} is not watertight; export or repair the assembled air volume first")
    voxels = mesh.voxelized(cell_mm).fill()
    # trimesh stores matrix axes as x, y, z. The FDTD code uses z, y, x so that
    # the longitudinal axis remains axis 0.
    air = np.transpose(voxels.matrix.astype(bool), (2, 1, 0))
    origin = tuple(float(value) for value in voxels.bounds[0])
    return air, origin


def sample_pressure(field: np.ndarray, air: np.ndarray, axis: int, shift: int) -> np.ndarray:
    shifted = np.roll(field, shift=shift, axis=axis)
    shifted_air = np.roll(air, shift=shift, axis=axis)
    edge = [slice(None)] * field.ndim
    edge[axis] = 0 if shift > 0 else -1
    shifted_air[tuple(edge)] = False
    return np.where(shifted_air, shifted, field)


def build_open_mask(
    air: np.ndarray,
    cell_mm: float,
    opening: Opening,
    hole_opening_scale: float,
    open_end_correction_mm: float,
    tonehole_correction_mm: float,
    use_physical_openings: bool,
    z_origin_mm: float = 0.0,
) -> np.ndarray:
    open_mask = np.zeros_like(air, dtype=bool)
    nz = air.shape[0]
    if use_physical_openings:
        center_mm = opening.physical_mm
        width_mm = max(cell_mm, opening.diameter_mm * hole_opening_scale) if opening.source.startswith("hole_") else cell_mm
    elif opening.source.startswith("hole_"):
        center_mm = opening.acoustic_mm + tonehole_correction_mm
        width_mm = max(cell_mm, opening.diameter_mm * hole_opening_scale)
    else:
        center_mm = opening.acoustic_mm + open_end_correction_mm
        width_mm = cell_mm

    center = min(nz - 2, max(1, int(round((center_mm - z_origin_mm) / cell_mm))))
    half_width = max(0, int(round(width_mm / (2.0 * cell_mm))))
    z0 = max(1, center - half_width)
    z1 = min(nz - 1, center + half_width + 1)
    open_mask[z0:z1, :, :] = air[z0:z1, :, :]
    return open_mask


def fft_peak(
    samples: np.ndarray,
    sample_rate_hz: float,
    target_hz: float,
    search_cents: float,
) -> tuple[float, float]:
    samples = samples - np.mean(samples)
    if np.allclose(samples, 0.0):
        return 0.0, 0.0
    window = np.hanning(len(samples))
    spectrum = np.abs(np.fft.rfft(samples * window))
    freqs = np.fft.rfftfreq(len(samples), d=1.0 / sample_rate_hz)
    low = target_hz * 2.0 ** (-search_cents / 1200.0)
    high = target_hz * 2.0 ** (search_cents / 1200.0)
    band = np.where((freqs >= low) & (freqs <= high))[0]
    if len(band) == 0:
        return 0.0, 0.0
    peak_index = int(band[np.argmax(spectrum[band])])
    if 0 < peak_index < len(spectrum) - 1:
        left = spectrum[peak_index - 1]
        center = spectrum[peak_index]
        right = spectrum[peak_index + 1]
        denom = left - 2.0 * center + right
        if denom != 0:
            offset = max(-0.5, min(0.5, 0.5 * (left - right) / denom))
            bin_hz = freqs[1] - freqs[0]
            return float(freqs[peak_index] + offset * bin_hz), float(center)
    return float(freqs[peak_index]), float(spectrum[peak_index])


def simulate_opening(
    geometry,
    opening: Opening,
    cell_mm: float,
    steps: int,
    courant: float,
    damping: float,
    search_cents: float,
    bore_diameter_mm: float,
    hole_opening_scale: float,
    open_end_correction_mm: float,
    tonehole_correction_mm: float,
    air_mask: np.ndarray | None = None,
    air_origin: tuple[float, float, float] = (0.0, 0.0, 0.0),
) -> dict[str, object]:
    sample_rate_hz = SPEED_OF_SOUND_MM_S * courant / cell_mm
    if air_mask is None:
        domain_length_mm = geometry.acoustic_length_mm + max(open_end_correction_mm, tonehole_correction_mm) + 8.0
        nz = int(math.ceil(domain_length_mm / cell_mm)) + 4
        side_cells = max(5, int(math.ceil((bore_diameter_mm + 2.0 * cell_mm) / cell_mm)))
        if side_cells % 2 == 0:
            side_cells += 1
        air = make_bore_mask(nz, side_cells, side_cells, cell_mm, bore_diameter_mm)
    else:
        air = air_mask
        nz, side_cells, _ = air.shape
    open_mask = build_open_mask(
        air=air,
        cell_mm=cell_mm,
        opening=opening,
        hole_opening_scale=hole_opening_scale,
        open_end_correction_mm=open_end_correction_mm,
        tonehole_correction_mm=tonehole_correction_mm,
        use_physical_openings=air_mask is not None,
        z_origin_mm=air_origin[2],
    )

    previous = np.zeros(air.shape, dtype=np.float64)
    current = np.zeros_like(previous)
    next_field = np.zeros_like(previous)
    center_y = side_cells // 2
    center_x = side_cells // 2
    z_origin = air_origin[2]
    source_z = min(nz - 3, max(1, int(round((8.0 - z_origin) / cell_mm))))
    if air_mask is not None:
        effective_opening_mm = opening.physical_mm
    else:
        effective_opening_mm = opening.acoustic_mm + (
            tonehole_correction_mm if opening.source.startswith("hole_") else open_end_correction_mm
        )
    receiver_z = min(nz - 3, max(1, int(round((max(12.0, effective_opening_mm - 12.0) - z_origin) / cell_mm))))
    if not air[source_z, center_y, center_x]:
        source_candidates = np.argwhere(air[source_z])
        if len(source_candidates):
            center = np.array([center_y, center_x])
            source_y, source_x = source_candidates[np.argmin(np.sum((source_candidates - center) ** 2, axis=1))]
        else:
            source_y, source_x = center_y, center_x
    else:
        source_y, source_x = center_y, center_x
    if not air[receiver_z, center_y, center_x]:
        receiver_candidates = np.argwhere(air[receiver_z])
        if len(receiver_candidates):
            center = np.array([center_y, center_x])
            receiver_y, receiver_x = receiver_candidates[np.argmin(np.sum((receiver_candidates - center) ** 2, axis=1))]
        else:
            receiver_y, receiver_x = center_y, center_x
    else:
        receiver_y, receiver_x = center_y, center_x
    samples = np.zeros(steps, dtype=np.float64)
    courant2 = courant * courant

    for step in range(steps):
        laplacian = (
            sample_pressure(current, air, axis=0, shift=1)
            + sample_pressure(current, air, axis=0, shift=-1)
            + sample_pressure(current, air, axis=1, shift=1)
            + sample_pressure(current, air, axis=1, shift=-1)
            + sample_pressure(current, air, axis=2, shift=1)
            + sample_pressure(current, air, axis=2, shift=-1)
            - 6.0 * current
        )
        next_field[:] = (2.0 * current - previous + courant2 * laplacian) * damping
        next_field[source_z, source_y, source_x] += gaussian_source(step)
        next_field[~air] = 0.0
        next_field[open_mask] = 0.0
        samples[step] = current[receiver_z, receiver_y, receiver_x]
        previous, current, next_field = current, next_field, previous

    skip = min(steps // 5, 4096)
    peak_hz, peak_amplitude = fft_peak(samples[skip:], sample_rate_hz, TARGET_HZ[opening.note], search_cents)
    return {
        "note": opening.note,
        "source": opening.source,
        "grid": f"{nz}x{side_cells}x{side_cells}",
        "air_cells": int(np.count_nonzero(air)),
        "acoustic_mm": round(opening.acoustic_mm, 4),
        "physical_mm": round(opening.physical_mm, 4),
        "diameter_mm": "" if opening.diameter_mm == 0 else round(opening.diameter_mm, 4),
        "target_hz": round(TARGET_HZ[opening.note], 4),
        "predicted_hz": round(peak_hz, 4),
        "predicted_cents": round(hz_to_cents(peak_hz, TARGET_HZ[opening.note]), 2) if peak_hz else "",
        "peak_amplitude": round(peak_amplitude, 8),
    }


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scad", default="Quena.scad")
    parser.add_argument("--measurement-note", default="measurements/2026-07-05-quena-tuning-pass.md")
    parser.add_argument("--measurement-section", default="Local rerun with current script")
    parser.add_argument("--cell-mm", type=float, default=4.0)
    parser.add_argument("--steps", type=int, default=16384)
    parser.add_argument("--courant", type=float, default=0.45)
    parser.add_argument("--damping", type=float, default=0.9995)
    parser.add_argument("--search-cents", type=float, default=100.0)
    parser.add_argument("--bore-diameter-mm", type=float, default=17.5)
    parser.add_argument("--air-stl", default="", help="watertight assembled internal-air STL to voxelize")
    parser.add_argument("--hole-opening-scale", type=float, default=1.0)
    parser.add_argument("--open-end-correction-mm", type=float, default=44.57)
    parser.add_argument("--tonehole-correction-mm", type=float, default=105.0)
    parser.add_argument("--note", choices=NOTE_ORDER + ["all"], default="all")
    parser.add_argument("--label", default="worktree")
    parser.add_argument("--out-dir", default="acoustics/out")
    parser.add_argument("--material", default="pla", choices=material_keys())
    parser.add_argument("--list-materials", action="store_true")
    args = parser.parse_args()

    if args.list_materials:
        for key in canonical_material_keys():
            profile = material_profile(key)
            print(f"{key}: {profile.label} - {profile.notes}")
        print("aliases: carbon, carbon-fiber, carbon_fiber, cf, cfpla, cfpetg")
        return 0

    if args.courant >= 1.0 / math.sqrt(3.0):
        raise SystemExit("3D FDTD is unstable: use --courant below 0.577")

    profile = material_profile(args.material)
    geometry = apply_material_to_geometry(geometry_from_scad(REPO_ROOT / args.scad), profile)
    measurements = measurements_from_markdown(REPO_ROOT / args.measurement_note, args.measurement_section)
    air_mask = None
    air_origin = (0.0, 0.0, 0.0)
    open_end_correction_mm = args.open_end_correction_mm + profile.open_end_correction_delta_mm
    tonehole_correction_mm = args.tonehole_correction_mm + profile.tonehole_correction_delta_mm
    if args.air_stl:
        air_mask, air_origin = load_air_mask_from_stl(REPO_ROOT / args.air_stl, args.cell_mm)
        open_end_correction_mm = 0.0
        tonehole_correction_mm = 0.0
    openings = fingering_openings(geometry)
    if args.note != "all":
        openings = [opening for opening in openings if opening.note == args.note]

    rows = []
    for opening in openings:
        row = simulate_opening(
            geometry=geometry,
            opening=opening,
            cell_mm=args.cell_mm,
            steps=args.steps,
            courant=args.courant,
            damping=args.damping * profile.fdtd_damping_multiplier,
            search_cents=args.search_cents,
            bore_diameter_mm=max(1.0, args.bore_diameter_mm + profile.bore_diameter_delta_mm),
            hole_opening_scale=args.hole_opening_scale,
            open_end_correction_mm=open_end_correction_mm,
            tonehole_correction_mm=tonehole_correction_mm,
            air_mask=air_mask,
            air_origin=air_origin,
        )
        measured = measurements.get(opening.note)
        row["measured_hz"] = round(measured["median_hz"], 4) if measured else ""
        row["measured_cents"] = round(measured["median_cents"], 2) if measured else ""
        row["prediction_error_cents"] = (
            round(float(row["predicted_cents"]) - measured["median_cents"], 2)
            if measured and row["predicted_cents"] != ""
            else ""
        )
        rows.append(row)
        print(
            f"{row['note']}: predicted {row['predicted_hz']} Hz "
            f"({row['predicted_cents']} cents), measured {row['measured_cents']} cents"
        )

    out_dir = REPO_ROOT / args.out_dir
    csv_path = out_dir / f"quena_3d_simulation_{args.label}.csv"
    json_path = out_dir / f"quena_3d_simulation_{args.label}.json"
    write_csv(csv_path, rows)
    json_path.write_text(
        json.dumps(
            {
                "model": "3d_fdtd_assembled_air_stl" if args.air_stl else "3d_fdtd_cylindrical_bore",
                "scad": args.scad,
                "cell_mm": args.cell_mm,
                "steps": args.steps,
                "courant": args.courant,
                "sample_rate_hz": SPEED_OF_SOUND_MM_S * args.courant / args.cell_mm,
                "damping": args.damping * profile.fdtd_damping_multiplier,
                "material": profile.to_json(),
                "search_cents": args.search_cents,
                "bore_diameter_mm": max(1.0, args.bore_diameter_mm + profile.bore_diameter_delta_mm),
                "air_stl": args.air_stl,
                "air_origin": air_origin,
                "hole_opening_scale": args.hole_opening_scale,
                "open_end_correction_mm": open_end_correction_mm,
                "tonehole_correction_mm": tonehole_correction_mm,
                "rows": rows,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    compared = [row for row in rows if row["prediction_error_cents"] != ""]
    if compared:
        errors = [abs(float(row["prediction_error_cents"])) for row in compared]
        print(
            f"compared {len(compared)} notes: "
            f"median abs error={np.median(errors):.1f} cents, "
            f"rms error={math.sqrt(sum(error * error for error in errors) / len(errors)):.1f} cents"
        )
    print(f"wrote {csv_path}")
    print(f"wrote {json_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
