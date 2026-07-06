#!/usr/bin/env python3
"""Run a 2D FDTD pitch estimate for the AgnuQuena bore.

The model is a longitudinal bore cross-section. Bore walls are reflective;
the distal end and the first open tone hole for each fingering are pressure
release openings. It is intentionally lightweight, deterministic, and designed
to sit between the calibrated 1D estimator and the future full 3D Vulkan FDTD.
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


def fingering_openings(geometry) -> list[Opening]:
    openings = [Opening("G4", "open_end", geometry.acoustic_length_mm, 0.0)]
    for hole in geometry.holes:
        openings.append(Opening(hole.note, f"hole_{hole.name}", hole.acoustic_mm, hole.diameter_mm))
    openings.append(Opening("G5", "first_overtone", geometry.acoustic_length_mm, 0.0))
    return sorted(openings, key=lambda opening: NOTE_ORDER.index(opening.note))


def gaussian_source(step: int, width_steps: float = 10.0) -> float:
    center = 4.0 * width_steps
    t = (step - center) / width_steps
    return float((1.0 - 2.0 * t * t) * math.exp(-t * t))


def sample_pressure(field: np.ndarray, mask: np.ndarray, axis: int, shift: int) -> np.ndarray:
    shifted = np.roll(field, shift=shift, axis=axis)
    shifted_mask = np.roll(mask, shift=shift, axis=axis)
    if axis == 0:
        shifted_mask[0 if shift > 0 else -1, :] = False
    else:
        shifted_mask[:, 0 if shift > 0 else -1] = False
    return np.where(shifted_mask, shifted, field)


def build_open_mask(
    nz: int,
    nr: int,
    dz_mm: float,
    opening: Opening,
    hole_opening_scale: float,
    pressure_release_hole_plane: bool,
    open_end_correction_mm: float,
    tonehole_correction_mm: float,
) -> np.ndarray:
    open_mask = np.zeros((nz, nr), dtype=bool)

    if opening.source.startswith("hole_"):
        center = int(round((opening.acoustic_mm + tonehole_correction_mm) / dz_mm))
        half_width = max(1, int(round((opening.diameter_mm * hole_opening_scale) / (2.0 * dz_mm))))
        z0 = max(1, center - half_width)
        z1 = min(nz - 2, center + half_width + 1)
        if pressure_release_hole_plane:
            open_mask[z0:z1, :] = True
        else:
            # Alternate side holes project to one wall in this 2D section. Opening
            # both walls over-couples the hole; one wall is closer to the physical
            # cross-section of a single drilled tone hole.
            open_mask[z0:z1, -1] = True
    else:
        center = min(nz - 2, int(round((opening.acoustic_mm + open_end_correction_mm) / dz_mm)))
        open_mask[center : center + 1, :] = True

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
            peak_hz = freqs[peak_index] + offset * bin_hz
            return float(peak_hz), float(center)
    return float(freqs[peak_index]), float(spectrum[peak_index])


def simulate_opening(
    geometry,
    opening: Opening,
    cell_mm: float,
    steps: int,
    courant: float,
    damping: float,
    search_cents: float,
    hole_opening_scale: float,
    pressure_release_hole_plane: bool,
    open_end_correction_mm: float,
    tonehole_correction_mm: float,
) -> dict[str, object]:
    sample_rate_hz = SPEED_OF_SOUND_MM_S * courant / cell_mm
    domain_length_mm = geometry.acoustic_length_mm + max(open_end_correction_mm, tonehole_correction_mm) + 8.0
    nz = int(math.ceil(domain_length_mm / cell_mm)) + 4
    nr = max(5, int(math.ceil(17.5 / cell_mm)) + 2)
    air = np.ones((nz, nr), dtype=bool)
    open_mask = build_open_mask(
        nz=nz,
        nr=nr,
        dz_mm=cell_mm,
        opening=opening,
        hole_opening_scale=hole_opening_scale,
        pressure_release_hole_plane=pressure_release_hole_plane,
        open_end_correction_mm=open_end_correction_mm,
        tonehole_correction_mm=tonehole_correction_mm,
    )

    previous = np.zeros((nz, nr), dtype=np.float64)
    current = np.zeros_like(previous)
    next_field = np.zeros_like(previous)
    source_z = min(nz - 3, max(1, int(round(8.0 / cell_mm))))
    source_r = nr // 2
    if opening.source.startswith("hole_"):
        effective_opening_mm = opening.acoustic_mm + tonehole_correction_mm
    else:
        effective_opening_mm = opening.acoustic_mm + open_end_correction_mm
    receiver_z = min(nz - 3, max(1, int(round(max(12.0, effective_opening_mm - 12.0) / cell_mm))))
    receiver_r = nr // 2
    samples = np.zeros(steps, dtype=np.float64)
    courant2 = courant * courant

    for step in range(steps):
        laplacian = (
            sample_pressure(current, air, axis=0, shift=1)
            + sample_pressure(current, air, axis=0, shift=-1)
            + sample_pressure(current, air, axis=1, shift=1)
            + sample_pressure(current, air, axis=1, shift=-1)
            - 4.0 * current
        )
        next_field[:] = (2.0 * current - previous + courant2 * laplacian) * damping
        next_field[source_z, source_r] += gaussian_source(step)
        next_field[open_mask] = 0.0
        samples[step] = current[receiver_z, receiver_r]
        previous, current, next_field = current, next_field, previous

    skip = min(steps // 5, 4096)
    peak_hz, peak_amplitude = fft_peak(samples[skip:], sample_rate_hz, TARGET_HZ[opening.note], search_cents)
    return {
        "note": opening.note,
        "source": opening.source,
        "acoustic_mm": round(opening.acoustic_mm, 4),
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
    parser.add_argument("--cell-mm", type=float, default=2.0)
    parser.add_argument("--steps", type=int, default=32768)
    parser.add_argument("--courant", type=float, default=0.45)
    parser.add_argument("--damping", type=float, default=0.9995)
    parser.add_argument("--search-cents", type=float, default=100.0)
    parser.add_argument("--hole-opening-scale", type=float, default=1.0)
    parser.add_argument("--open-end-correction-mm", type=float, default=44.57)
    parser.add_argument("--tonehole-correction-mm", type=float, default=85.0)
    parser.add_argument(
        "--side-hole-only",
        action="store_true",
        help="model tone holes as wall slots instead of pressure-release planes",
    )
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

    if args.courant >= 1.0 / math.sqrt(2.0):
        raise SystemExit("2D FDTD is unstable: use --courant below 0.707")

    profile = material_profile(args.material)
    geometry = apply_material_to_geometry(geometry_from_scad(REPO_ROOT / args.scad), profile)
    measurements = measurements_from_markdown(REPO_ROOT / args.measurement_note, args.measurement_section)
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
            hole_opening_scale=args.hole_opening_scale,
            pressure_release_hole_plane=not args.side_hole_only,
            open_end_correction_mm=args.open_end_correction_mm + profile.open_end_correction_delta_mm,
            tonehole_correction_mm=args.tonehole_correction_mm + profile.tonehole_correction_delta_mm,
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
    csv_path = out_dir / f"quena_2d_simulation_{args.label}.csv"
    json_path = out_dir / f"quena_2d_simulation_{args.label}.json"
    write_csv(csv_path, rows)
    json_path.write_text(
        json.dumps(
            {
                "model": "2d_fdtd_cross_section",
                "scad": args.scad,
                "cell_mm": args.cell_mm,
                "steps": args.steps,
                "courant": args.courant,
                "sample_rate_hz": SPEED_OF_SOUND_MM_S * args.courant / args.cell_mm,
                "damping": args.damping * profile.fdtd_damping_multiplier,
                "material": profile.to_json(),
                "search_cents": args.search_cents,
                "hole_opening_scale": args.hole_opening_scale,
                "open_end_correction_mm": args.open_end_correction_mm + profile.open_end_correction_delta_mm,
                "tonehole_correction_mm": args.tonehole_correction_mm + profile.tonehole_correction_delta_mm,
                "pressure_release_hole_plane": not args.side_hole_only,
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
