#!/usr/bin/env python3
"""Estimate AgnuQuena pitches with a calibrated 1D bore model.

This is not a replacement for the planned 3D FDTD path. It is a small,
deterministic acoustic model that turns the current OpenSCAD tone-hole geometry
into pitch estimates and compares them with measured tune-check results.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import re
import sys
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from tools.compare_measurements import parse_scad  # noqa: E402
from acoustics.materials import (  # noqa: E402
    apply_material_to_geometry,
    canonical_material_keys,
    material_keys,
    material_profile,
)


SPEED_OF_SOUND_MM_S = 343_000.0
TARGET_HZ = {
    "G4": 392.00,
    "A4": 440.00,
    "B4": 493.88,
    "C5": 523.25,
    "D5": 587.33,
    "E5": 659.26,
    "F#5": 739.99,
    "G5": 783.99,
}
HOLE_TO_NOTE = {
    "A": "A4",
    "B": "B4",
    "C": "C5",
    "D": "D5",
    "E": "E5",
    "F#": "F#5",
}
NOTE_ORDER = ["G4", "A4", "B4", "C5", "D5", "E5", "F#5", "G5"]
MARKDOWN_ROW_RE = re.compile(r"^\|\s*([A-G](?:#|b)?\d)\s*\|(.+)\|$")


@dataclass(frozen=True)
class Hole:
    name: str
    note: str
    acoustic_mm: float
    diameter_mm: float


@dataclass(frozen=True)
class Geometry:
    source: str
    acoustic_length_mm: float
    holes: list[Hole]
    unacoustic_length_mm: float = 6.0
    mouthpiece_active_length_mm: float = 24.0
    z_adjust_mm: float = -8.0


def hz_to_cents(freq: float, target: float) -> float:
    return 1200.0 * math.log2(freq / target)


def freq_for_length(length_mm: float) -> float:
    return SPEED_OF_SOUND_MM_S / (2.0 * length_mm)


def effective_length_for_freq(freq: float) -> float:
    return SPEED_OF_SOUND_MM_S / (2.0 * freq)


def parse_float(value: str) -> float:
    return float(value.strip().replace("+", ""))


def geometry_from_scad(path: Path) -> Geometry:
    env, holes, _measurements = parse_scad(path.read_text(encoding="utf-8"))
    mouthpiece_active_length = float(env["mouthpiece_active_length"])
    zadj = float(env["zadj"])
    acoustic_holes = []
    for hole in holes:
        name = str(hole["note"])
        note = HOLE_TO_NOTE.get(name)
        if not note:
            continue
        acoustic_mm = float(hole["z_mm"]) + mouthpiece_active_length - zadj
        acoustic_holes.append(
            Hole(
                name=name,
                note=note,
                acoustic_mm=acoustic_mm,
                diameter_mm=float(hole["diameter_mm"]),
            )
        )
    return Geometry(
        source=str(path),
        acoustic_length_mm=float(env["acoustic_length"]),
        holes=acoustic_holes,
        unacoustic_length_mm=float(env["unacoustic_length"]),
        mouthpiece_active_length_mm=mouthpiece_active_length,
        z_adjust_mm=zadj,
    )


def rows_from_history(path: Path, commit: str) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return [row for row in csv.DictReader(handle) if row["commit"] == commit]


def geometry_from_history(commit: str, history_dir: Path) -> Geometry:
    geometry_rows = rows_from_history(history_dir / "geometry_by_commit.csv", commit)
    hole_rows = rows_from_history(history_dir / "holes_by_commit.csv", commit)
    if not geometry_rows or not hole_rows:
        raise SystemExit(f"no generated geometry history found for commit {commit!r}")

    geometry = geometry_rows[0]
    acoustic_length_mm = float(geometry["acoustic_length_mm"])
    holes = []
    for row in hole_rows:
        name = row["note"]
        note = HOLE_TO_NOTE.get(name)
        if not note:
            continue
        # History rows store final z. For the measured geometries we are
        # comparing here, the active-edge coordinate is z + mouthpiece_active
        # - zadj, which is 32 mm in the current history schema.
        acoustic_mm = float(row["z_mm"]) + 32.0
        holes.append(
            Hole(
                name=name,
                note=note,
                acoustic_mm=acoustic_mm,
                diameter_mm=float(row["diameter_mm"]),
            )
        )
    return Geometry(source=f"history:{commit}", acoustic_length_mm=acoustic_length_mm, holes=holes)


def measurements_from_markdown(path: Path, section: str) -> dict[str, dict[str, float]]:
    in_section = False
    measurements: dict[str, dict[str, float]] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("## "):
            in_section = line[3:].strip().lower() == section.lower()
            continue
        if not in_section:
            continue
        match = MARKDOWN_ROW_RE.match(line)
        if not match:
            continue
        note = match.group(1)
        cells = [cell.strip() for cell in match.group(2).split("|")]
        if len(cells) < 5 or cells[0] == "---":
            continue
        try:
            measurements[note] = {
                "frames": float(cells[0]),
                "median_hz": parse_float(cells[1]),
                "target_hz": parse_float(cells[2]),
                "median_cents": parse_float(cells[3]),
            }
        except ValueError:
            continue
    return measurements


def fit_tonehole_correction(geometry: Geometry, measurements: dict[str, dict[str, float]]) -> float:
    corrections = []
    for hole in geometry.holes:
        measured = measurements.get(hole.note)
        if not measured:
            continue
        corrections.append(effective_length_for_freq(measured["median_hz"]) - hole.acoustic_mm)
    if not corrections:
        raise SystemExit("no matching tone-hole measurements available for correction fit")
    corrections.sort()
    middle = len(corrections) // 2
    if len(corrections) % 2:
        return corrections[middle]
    return (corrections[middle - 1] + corrections[middle]) / 2.0


def fit_open_end_correction(geometry: Geometry, measurements: dict[str, dict[str, float]]) -> float:
    measured = measurements.get("G4")
    if measured:
        return effective_length_for_freq(measured["median_hz"]) - geometry.acoustic_length_mm
    return effective_length_for_freq(TARGET_HZ["G4"]) - geometry.acoustic_length_mm


def simulate(
    geometry: Geometry,
    measurements: dict[str, dict[str, float]],
    open_end_correction_mm: float,
    tonehole_correction_mm: float,
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []

    open_effective = geometry.acoustic_length_mm + open_end_correction_mm
    open_predicted = freq_for_length(open_effective)
    rows.append(
        row_for_note(
            note="G4",
            source="open_end",
            acoustic_mm=geometry.acoustic_length_mm,
            diameter_mm="",
            correction_mm=open_end_correction_mm,
            effective_mm=open_effective,
            predicted_hz=open_predicted,
            measured=measurements.get("G4"),
        )
    )

    for hole in geometry.holes:
        effective = hole.acoustic_mm + tonehole_correction_mm
        predicted = freq_for_length(effective)
        rows.append(
            row_for_note(
                note=hole.note,
                source=f"hole_{hole.name}",
                acoustic_mm=hole.acoustic_mm,
                diameter_mm=hole.diameter_mm,
                correction_mm=tonehole_correction_mm,
                effective_mm=effective,
                predicted_hz=predicted,
                measured=measurements.get(hole.note),
            )
        )

    octave_effective = geometry.acoustic_length_mm / 2.0 + open_end_correction_mm / 2.0
    octave_predicted = freq_for_length(octave_effective)
    rows.append(
        row_for_note(
            note="G5",
            source="first_overtone",
            acoustic_mm=geometry.acoustic_length_mm / 2.0,
            diameter_mm="",
            correction_mm=open_end_correction_mm / 2.0,
            effective_mm=octave_effective,
            predicted_hz=octave_predicted,
            measured=measurements.get("G5"),
        )
    )

    return sorted(rows, key=lambda row: NOTE_ORDER.index(str(row["note"])))


def row_for_note(
    note: str,
    source: str,
    acoustic_mm: float,
    diameter_mm: float | str,
    correction_mm: float,
    effective_mm: float,
    predicted_hz: float,
    measured: dict[str, float] | None,
) -> dict[str, object]:
    target = TARGET_HZ[note]
    predicted_cents = hz_to_cents(predicted_hz, target)
    measured_hz = measured["median_hz"] if measured else ""
    measured_cents = measured["median_cents"] if measured else ""
    error_cents = predicted_cents - measured["median_cents"] if measured else ""
    return {
        "note": note,
        "source": source,
        "acoustic_mm": round(acoustic_mm, 4),
        "diameter_mm": diameter_mm if diameter_mm == "" else round(float(diameter_mm), 4),
        "correction_mm": round(correction_mm, 4),
        "effective_mm": round(effective_mm, 4),
        "target_hz": round(target, 4),
        "predicted_hz": round(predicted_hz, 4),
        "predicted_cents": round(predicted_cents, 2),
        "measured_hz": measured_hz if measured_hz == "" else round(float(measured_hz), 4),
        "measured_cents": measured_cents if measured_cents == "" else round(float(measured_cents), 2),
        "prediction_error_cents": error_cents if error_cents == "" else round(float(error_cents), 2),
    }


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scad", default="Quena.scad", help="SCAD file for WORKTREE simulation")
    parser.add_argument("--commit", default="WORKTREE", help="geometry history commit or WORKTREE")
    parser.add_argument("--history-dir", default="measurements/history")
    parser.add_argument("--measurement-note", default="measurements/2026-07-05-quena-tuning-pass.md")
    parser.add_argument("--measurement-section", default="Local rerun with current script")
    parser.add_argument("--tonehole-correction-mm", type=float, default=49.0)
    parser.add_argument("--open-end-correction-mm", type=float, default=None)
    parser.add_argument("--fit-correction", action="store_true", help="fit corrections from measurements")
    parser.add_argument("--out-dir", default="acoustics/out")
    parser.add_argument("--label", default="", help="output filename label; defaults to commit/worktree")
    parser.add_argument("--material", default="pla", choices=material_keys())
    parser.add_argument("--list-materials", action="store_true")
    args = parser.parse_args()

    if args.list_materials:
        for key in canonical_material_keys():
            profile = material_profile(key)
            print(f"{key}: {profile.label} - {profile.notes}")
        print("aliases: carbon, carbon-fiber, carbon_fiber, cf, cfpla, cfpetg")
        return 0

    if args.commit == "WORKTREE":
        geometry = geometry_from_scad(REPO_ROOT / args.scad)
    else:
        geometry = geometry_from_history(args.commit, REPO_ROOT / args.history_dir)
    profile = material_profile(args.material)
    geometry = apply_material_to_geometry(geometry, profile)

    note_path = REPO_ROOT / args.measurement_note
    measurements = measurements_from_markdown(note_path, args.measurement_section) if note_path.exists() else {}

    open_end_correction_mm = (
        args.open_end_correction_mm
        if args.open_end_correction_mm is not None
        else fit_open_end_correction(geometry, measurements)
    )
    open_end_correction_mm += profile.open_end_correction_delta_mm
    tonehole_correction_mm = (
        fit_tonehole_correction(geometry, measurements)
        if args.fit_correction
        else args.tonehole_correction_mm
    )
    tonehole_correction_mm += profile.tonehole_correction_delta_mm

    rows = simulate(geometry, measurements, open_end_correction_mm, tonehole_correction_mm)
    out_dir = REPO_ROOT / args.out_dir
    label = args.label or args.commit.lower().replace("/", "_")
    csv_path = out_dir / f"quena_1d_simulation_{label}.csv"
    json_path = out_dir / f"quena_1d_simulation_{label}.json"
    write_csv(csv_path, rows)

    summary = {
        "geometry": geometry.source,
        "measurement_note": str(note_path) if measurements else "",
        "measurement_section": args.measurement_section if measurements else "",
        "material": profile.to_json(),
        "open_end_correction_mm": round(open_end_correction_mm, 4),
        "tonehole_correction_mm": round(tonehole_correction_mm, 4),
        "rows": rows,
    }
    json_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")

    compared = [row for row in rows if row["prediction_error_cents"] != ""]
    if compared:
        abs_errors = [abs(float(row["prediction_error_cents"])) for row in compared]
        rms = math.sqrt(sum(error * error for error in abs_errors) / len(abs_errors))
        print(
            f"compared {len(compared)} notes: "
            f"median abs error={sorted(abs_errors)[len(abs_errors)//2]:.1f} cents, "
            f"rms error={rms:.1f} cents"
        )
    print(f"wrote {csv_path}")
    print(f"wrote {json_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
