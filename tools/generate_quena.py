#!/usr/bin/env python3
"""Generate production Quena parameters and validation data from one spec.

The generator is deterministic: no timestamps or machine-specific paths are
written to its outputs. Use --check in CI or before exporting production STLs.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import tempfile
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SPEC = REPO_ROOT / "designs" / "quena.json"
DEFAULT_SCAD_OUTPUT = REPO_ROOT / "generated" / "quena_parameters.scad"
DEFAULT_MANIFEST_OUTPUT = REPO_ROOT / "generated" / "quena_manifest.json"


class DesignError(ValueError):
    """Raised when a specification cannot produce a valid instrument."""


def number(value: Any, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise DesignError(f"{field} must be numeric")
    result = float(value)
    if not math.isfinite(result):
        raise DesignError(f"{field} must be finite")
    return result


def positive(value: Any, field: str) -> float:
    result = number(value, field)
    if result <= 0:
        raise DesignError(f"{field} must be greater than zero")
    return result


def semantic_hash(spec: dict[str, Any]) -> str:
    canonical = json.dumps(spec, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def scad_number(value: float) -> str:
    if abs(value) < 5e-13:
        value = 0.0
    text = f"{value:.12g}"
    return text if any(character in text for character in ".eE") else f"{text}.0"


def round_to_increment(value: float, increment: float) -> float:
    return math.floor(value / increment + 0.5 + 1e-12) * increment


def note_frequency_12tet(note: str, concert_a_hz: float = 440.0) -> float:
    """Return the 12-TET frequency for a scientific-pitch note name."""
    names = ("C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B")
    split = 2 if len(note) > 2 and note[1] == "#" else 1
    try:
        pitch_class = names.index(note[:split])
        octave = int(note[split:])
    except (ValueError, IndexError) as exc:
        raise DesignError(f"invalid target note {note!r}") from exc
    midi_note = (octave + 1) * 12 + pitch_class
    return concert_a_hz * 2.0 ** ((midi_note - 69) / 12.0)


def rounded_square_side(diameter_mm: float, corner_ratio: float) -> float:
    denominator = 1.0 - (4.0 - math.pi) * corner_ratio**2
    return diameter_mm * math.sqrt((math.pi / 4.0) / denominator)


def tonehole_equivalent_correction(
    diameter_mm: float,
    bore_radius_mm: float,
    wall_height_mm: float,
) -> float:
    """Return te/delta^2 using Lefebvre's low-frequency open-hole fit.

    This is the geometric part of the shunt inertance model. A per-hole factor
    fitted from a measured prototype absorbs the instrument-specific residual.
    """
    hole_radius = diameter_mm / 2.0
    delta = hole_radius / bore_radius_mm
    height_ratio = wall_height_mm / hole_radius
    f_delta = (
        0.095
        - 0.422 * delta
        + 1.168 * delta**2
        - 1.808 * delta**3
        + 1.398 * delta**4
        - 0.416 * delta**5
    )
    g = 1.0 - math.tanh(0.778 * height_ratio)
    h = (
        1.435
        + 0.030 * delta
        - 1.566 * delta**2
        + 2.138 * delta**3
        - 1.614 * delta**4
        + 0.502 * delta**5
    )
    equivalent_length = hole_radius * (height_ratio + (1.0 + f_delta * g) * h)
    return equivalent_length / delta**2


def solve_diameter(
    required_correction_mm: float,
    empirical_factor: float,
    bounds_mm: tuple[float, float],
    bore_radius_mm: float,
    wall_height_mm: float,
) -> float:
    low, high = bounds_mm

    def residual(diameter_mm: float) -> float:
        correction = tonehole_equivalent_correction(
            diameter_mm,
            bore_radius_mm,
            wall_height_mm,
        )
        return empirical_factor * correction - required_correction_mm

    low_residual = residual(low)
    high_residual = residual(high)
    if low_residual * high_residual > 0:
        raise DesignError(
            "required tone-hole correction cannot be reached inside diameter "
            f"bounds {low:g}..{high:g} mm"
        )
    for _ in range(80):
        middle = (low + high) / 2.0
        middle_residual = residual(middle)
        if abs(middle_residual) < 1e-10:
            return middle
        # Equivalent correction decreases as diameter increases.
        if middle_residual > 0:
            low = middle
        else:
            high = middle
    return (low + high) / 2.0


def validate_spec(spec: dict[str, Any]) -> None:
    if spec.get("schema_version") != 1:
        raise DesignError("schema_version must be 1")
    if not isinstance(spec.get("design_id"), str) or not spec["design_id"].strip():
        raise DesignError("design_id must be a non-empty string")
    holes = spec.get("holes")
    if not isinstance(holes, list) or not holes:
        raise DesignError("holes must be a non-empty list")
    names = [hole.get("name") for hole in holes if isinstance(hole, dict)]
    if len(names) != len(holes) or len(set(names)) != len(names):
        raise DesignError("every hole must have a unique name")


def generate(spec: dict[str, Any]) -> tuple[dict[str, float], dict[str, Any]]:
    validate_spec(spec)
    geometry = spec["geometry"]
    connectors = spec["connectors"]
    rendering = spec["rendering"]
    profile = spec["tone_hole_profile"]
    layout = spec["lower_hand_layout"]
    compensation = spec["tonehole_compensation"]
    constraints = spec["manufacturing_constraints"]

    bore_id = positive(geometry["bore_id_mm"], "geometry.bore_id_mm")
    shell_width = positive(geometry["shell_width_mm"], "geometry.shell_width_mm")
    taper = number(geometry["taper_mm"], "geometry.taper_mm")
    nominal_acoustic_length = positive(
        geometry["nominal_acoustic_length_mm"],
        "geometry.nominal_acoustic_length_mm",
    )
    pitch_raise_cents = number(
        geometry["pitch_raise_cents"],
        "geometry.pitch_raise_cents",
    )
    mouthpiece_total = positive(
        geometry["mouthpiece_total_length_mm"],
        "geometry.mouthpiece_total_length_mm",
    )
    unacoustic_length = positive(
        geometry["unacoustic_length_mm"],
        "geometry.unacoustic_length_mm",
    )
    z_adjust = number(geometry["z_adjust_mm"], "geometry.z_adjust_mm")
    tube_part_1_length = positive(
        geometry["tube_part_1_length_mm"],
        "geometry.tube_part_1_length_mm",
    )
    if unacoustic_length >= mouthpiece_total:
        raise DesignError("unacoustic mouthpiece length must be shorter than the mouthpiece")

    outer_diameter = bore_id + 2.0 * shell_width
    outlet_id = bore_id - taper
    outlet_od = outer_diameter - taper
    if min(outlet_id, outlet_od) <= 0:
        raise DesignError("taper produces a non-positive outlet diameter")

    length_scale = 2.0 ** (-pitch_raise_cents / 1200.0)
    acoustic_length = nominal_acoustic_length * length_scale
    mouthpiece_active = mouthpiece_total - unacoustic_length
    total_height = acoustic_length + unacoustic_length
    non_mouthpiece_length = acoustic_length - mouthpiece_active
    tube_part_2_length = non_mouthpiece_length - tube_part_1_length
    if tube_part_2_length <= 0:
        raise DesignError("tube_part_1_length leaves no printable second tube")

    mouthpiece_overlap = positive(
        connectors["mouthpiece_overlap_mm"],
        "connectors.mouthpiece_overlap_mm",
    )
    tube_joint_overlap = positive(
        connectors["tube_joint_overlap_mm"],
        "connectors.tube_joint_overlap_mm",
    )
    transition = positive(
        connectors["angled_transition_mm"],
        "connectors.angled_transition_mm",
    )
    accent_ring = number(connectors["accent_ring_mm"], "connectors.accent_ring_mm")
    radial_clearance = number(
        connectors["radial_clearance_mm"],
        "connectors.radial_clearance_mm",
    )
    if radial_clearance < 0:
        raise DesignError("radial_clearance_mm must be non-negative")
    insert_tolerance = number(
        connectors["insert_z_tolerance_mm"],
        "connectors.insert_z_tolerance_mm",
    )
    if not 0 <= insert_tolerance < min(mouthpiece_overlap, tube_joint_overlap):
        raise DesignError(
            "insert_z_tolerance_mm must be smaller than every connector overlap"
        )

    axial_scale = positive(profile["axial_scale"], "tone_hole_profile.axial_scale")
    circumferential_scale = positive(
        profile["circumferential_scale"],
        "tone_hole_profile.circumferential_scale",
    )
    corner_ratio = number(profile["corner_ratio"], "tone_hole_profile.corner_ratio")
    if profile.get("shape") != "equal_area_rounded_square":
        raise DesignError("only equal_area_rounded_square tone holes are supported")
    if not 0 < corner_ratio < 0.5:
        raise DesignError("tone-hole corner_ratio must be between 0 and 0.5")
    if not math.isclose(axial_scale * circumferential_scale, 1.0, abs_tol=1e-9):
        raise DesignError(
            "tone-hole axial and circumferential scales must be reciprocal "
            "to preserve opening area"
        )

    first_offset = positive(
        layout["first_center_offset_mm"],
        "lower_hand_layout.first_center_offset_mm",
    )
    center_spacing = positive(
        layout["center_spacing_mm"],
        "lower_hand_layout.center_spacing_mm",
    )
    angle_spread = number(
        layout["angle_spread_deg"],
        "lower_hand_layout.angle_spread_deg",
    )
    if layout.get("part") != 2:
        raise DesignError("lower_hand_layout.part must currently be 2")

    speed_of_sound = positive(
        compensation["speed_of_sound_mm_s"],
        "tonehole_compensation.speed_of_sound_mm_s",
    )
    diameter_increment = positive(
        compensation["diameter_increment_mm"],
        "tonehole_compensation.diameter_increment_mm",
    )
    diameter_bounds_raw = constraints["diameter_bounds_mm"]
    if not isinstance(diameter_bounds_raw, list) or len(diameter_bounds_raw) != 2:
        raise DesignError("diameter_bounds_mm must contain [minimum, maximum]")
    diameter_bounds = (
        positive(diameter_bounds_raw[0], "diameter_bounds_mm[0]"),
        positive(diameter_bounds_raw[1], "diameter_bounds_mm[1]"),
    )
    if diameter_bounds[0] >= diameter_bounds[1]:
        raise DesignError("diameter bounds must be increasing")

    bore_radius = bore_id / 2.0
    holes: list[dict[str, Any]] = []
    for hole_spec in spec["holes"]:
        name = str(hole_spec["name"])
        position_spec = hole_spec["position"]
        position_mode = position_spec["mode"]
        if position_mode == "lower_hand":
            index = int(position_spec["index"])
            if index < 0:
                raise DesignError(f"hole {name}: lower-hand index cannot be negative")
            axial_adjust = number(
                position_spec.get("axial_adjust_mm", 0.0),
                f"hole {name} axial_adjust_mm",
            )
            local_offset = first_offset + index * center_spacing + axial_adjust
            physical_z = tube_part_1_length + local_offset
            position_detail: dict[str, Any] = {
                "mode": position_mode,
                "part": 2,
                "local_offset_mm": local_offset,
                "axial_adjust_mm": axial_adjust,
            }
        elif position_mode == "tuned_source":
            source_position = positive(
                position_spec["source_position_mm"],
                f"hole {name} source_position_mm",
            )
            physical_z = source_position * length_scale - mouthpiece_active + z_adjust
            position_detail = {
                "mode": position_mode,
                "source_position_mm": source_position,
            }
        else:
            raise DesignError(f"hole {name}: unsupported position mode {position_mode!r}")

        acoustic_position = physical_z + mouthpiece_active - z_adjust
        if "angle_deg" in hole_spec:
            angle = number(hole_spec["angle_deg"], f"hole {name} angle_deg")
        else:
            angle_factor = number(
                hole_spec.get("angle_factor", 0.0),
                f"hole {name} angle_factor",
            )
            angle = angle_factor * angle_spread

        diameter_spec = hole_spec["diameter"]
        diameter_mode = diameter_spec["mode"]
        compensation_detail: dict[str, Any] | None = None
        if diameter_mode == "fixed":
            exact_diameter = positive(
                diameter_spec["value_mm"],
                f"hole {name} diameter.value_mm",
            )
            diameter = exact_diameter
        elif diameter_mode == "measured_compensation":
            calibration = diameter_spec["calibration"]
            calibration_acoustic_position = positive(
                calibration["acoustic_position_mm"],
                f"hole {name} calibration.acoustic_position_mm",
            )
            calibration_diameter = positive(
                calibration["diameter_mm"],
                f"hole {name} calibration.diameter_mm",
            )
            measured_frequency = positive(
                calibration["measured_frequency_hz"],
                f"hole {name} calibration.measured_frequency_hz",
            )
            global_pitch_offset_cents = number(
                calibration.get("global_pitch_offset_cents", 0.0),
                f"hole {name} calibration.global_pitch_offset_cents",
            )
            interval_frequency = measured_frequency / (
                2.0 ** (global_pitch_offset_cents / 1200.0)
            )

            measured_effective_length = speed_of_sound / (2.0 * interval_frequency)
            calibration_geometric_correction = tonehole_equivalent_correction(
                calibration_diameter,
                bore_radius,
                shell_width,
            )
            empirical_factor = (
                measured_effective_length - calibration_acoustic_position
            ) / calibration_geometric_correction
            if empirical_factor <= 0:
                raise DesignError(f"hole {name}: calibration produced a non-positive factor")

            target_frequency = note_frequency_12tet(str(hole_spec["target_note"]))
            target_effective_length = speed_of_sound / (2.0 * target_frequency)
            required_correction = target_effective_length - acoustic_position
            if required_correction <= 0:
                raise DesignError(
                    f"hole {name}: requested position is too distal to compensate"
                )
            exact_diameter = solve_diameter(
                required_correction,
                empirical_factor,
                diameter_bounds,
                bore_radius,
                shell_width,
            )
            acoustic_diameter = exact_diameter
            minimum_diameter = diameter_spec.get("minimum_mm")
            if minimum_diameter is not None:
                minimum_diameter = positive(
                    minimum_diameter,
                    f"hole {name} diameter.minimum_mm",
                )
                if not diameter_bounds[0] <= minimum_diameter <= diameter_bounds[1]:
                    raise DesignError(
                        f"hole {name}: minimum diameter {minimum_diameter:g} mm "
                        "violates configured bounds"
                    )
                exact_diameter = max(exact_diameter, minimum_diameter)
            diameter = round_to_increment(exact_diameter, diameter_increment)
            generated_effective_length = (
                acoustic_position
                + empirical_factor
                * tonehole_equivalent_correction(
                    diameter,
                    bore_radius,
                    shell_width,
                )
            )
            estimated_pitch_delta = 1200.0 * math.log2(
                target_effective_length / generated_effective_length
            )
            compensation_detail = {
                "model": compensation["model"],
                "calibration_source": calibration.get("source"),
                "calibration_measured_frequency_hz": measured_frequency,
                "calibration_global_pitch_offset_cents": global_pitch_offset_cents,
                "calibration_interval_frequency_hz": interval_frequency,
                "empirical_factor": empirical_factor,
                "acoustically_tuned_diameter_mm": acoustic_diameter,
                "minimum_diameter_mm": minimum_diameter,
                "minimum_applied": (
                    minimum_diameter is not None
                    and minimum_diameter > acoustic_diameter
                ),
                "unrounded_diameter_mm": exact_diameter,
                "diameter_increment_mm": diameter_increment,
                "target_effective_length_mm": target_effective_length,
                "generated_effective_length_mm": generated_effective_length,
                "estimated_pitch_delta_cents": estimated_pitch_delta,
            }
        else:
            raise DesignError(f"hole {name}: unsupported diameter mode {diameter_mode!r}")

        if not diameter_bounds[0] <= diameter <= diameter_bounds[1]:
            raise DesignError(
                f"hole {name}: diameter {diameter:g} mm violates configured bounds"
            )
        profile_side = rounded_square_side(diameter, corner_ratio)
        axial_width = profile_side * axial_scale
        circumferential_width = profile_side * circumferential_scale
        holes.append(
            {
                "name": name,
                "target_note": str(hole_spec["target_note"]),
                "physical_z_mm": physical_z,
                "acoustic_position_mm": acoustic_position,
                "angle_deg": angle,
                "diameter_mm": diameter,
                "profile_axial_width_mm": axial_width,
                "profile_circumferential_width_mm": circumferential_width,
                "position": position_detail,
                "diameter_mode": diameter_mode,
                "calibrated_correction_mm": (
                    compensation_detail["generated_effective_length_mm"]
                    - acoustic_position
                    if compensation_detail
                    else None
                ),
                "compensation": compensation_detail,
            }
        )

    # Production constraints are checked on the actual rounded-square cuts.
    maximum_profile_width = positive(
        constraints["maximum_profile_width_mm"],
        "manufacturing_constraints.maximum_profile_width_mm",
    )
    minimum_ligament = positive(
        constraints["minimum_axial_ligament_mm"],
        "manufacturing_constraints.minimum_axial_ligament_mm",
    )
    minimum_end_ligament = positive(
        constraints["minimum_part_end_ligament_mm"],
        "manufacturing_constraints.minimum_part_end_ligament_mm",
    )
    maximum_print_height = positive(
        constraints["maximum_print_height_mm"],
        "manufacturing_constraints.maximum_print_height_mm",
    )
    segment_bounds = ((0.0, tube_part_1_length), (tube_part_1_length, non_mouthpiece_length))
    violations: list[str] = []
    end_ligaments: list[dict[str, Any]] = []
    axial_ligaments: list[dict[str, Any]] = []

    for hole in holes:
        if hole["profile_circumferential_width_mm"] > maximum_profile_width + 1e-9:
            violations.append(
                f"hole {hole['name']} profile width "
                f"{hole['profile_circumferential_width_mm']:.3f} mm exceeds "
                f"{maximum_profile_width:.3f} mm"
            )
        segment_index = 0 if hole["physical_z_mm"] < tube_part_1_length else 1
        segment_start, segment_end = segment_bounds[segment_index]
        half_width = hole["profile_axial_width_mm"] / 2.0
        start_ligament = hole["physical_z_mm"] - half_width - segment_start
        end_ligament = segment_end - hole["physical_z_mm"] - half_width
        end_ligaments.append(
            {
                "hole": hole["name"],
                "part": segment_index + 1,
                "start_mm": start_ligament,
                "end_mm": end_ligament,
            }
        )
        if min(start_ligament, end_ligament) < minimum_end_ligament - 1e-9:
            violations.append(
                f"hole {hole['name']} leaves less than {minimum_end_ligament:g} mm "
                f"at a part end"
            )

    for segment_index, (segment_start, segment_end) in enumerate(segment_bounds):
        segment_holes = sorted(
            (
                hole
                for hole in holes
                if segment_start <= hole["physical_z_mm"] <= segment_end
            ),
            key=lambda hole: hole["physical_z_mm"],
        )
        for first, second in zip(segment_holes, segment_holes[1:]):
            ligament = (
                second["physical_z_mm"]
                - first["physical_z_mm"]
                - first["profile_axial_width_mm"] / 2.0
                - second["profile_axial_width_mm"] / 2.0
            )
            axial_ligaments.append(
                {
                    "part": segment_index + 1,
                    "between": [first["name"], second["name"]],
                    "mm": ligament,
                }
            )
            if ligament < minimum_ligament - 1e-9:
                violations.append(
                    f"holes {first['name']}/{second['name']} leave only "
                    f"{ligament:.3f} mm axial ligament"
                )

    def connector_extra(overlap: float) -> float:
        return overlap - insert_tolerance + transition - 2.0

    print_heights = {
        "mouthpiece": mouthpiece_total + connector_extra(mouthpiece_overlap),
        "tube_1": tube_part_1_length + connector_extra(tube_joint_overlap),
        "tube_2": tube_part_2_length,
    }
    for part_name, height in print_heights.items():
        if height > maximum_print_height + 1e-9:
            violations.append(
                f"{part_name} print height {height:.3f} mm exceeds "
                f"{maximum_print_height:.3f} mm"
            )
    if violations:
        raise DesignError("manufacturing constraints failed:\n- " + "\n- ".join(violations))

    facet_count = positive(rendering["facet_count"], "rendering.facet_count")
    if not facet_count.is_integer() or facet_count < 3:
        raise DesignError("rendering.facet_count must be an integer of at least 3")

    params: dict[str, float] = {
        "quena_facet_count": facet_count,
        "shell_width": shell_width,
        "id": bore_id,
        "od": outer_diameter,
        "hd": (bore_id + outer_diameter) / 2.0,
        "taper": taper,
        "ido": outlet_id,
        "odo": outlet_od,
        "mouthpiece_total_length": mouthpiece_total,
        "unacoustic_length": unacoustic_length,
        "mouthpiece_active_length": mouthpiece_active,
        "pitch_raise_cents": pitch_raise_cents,
        "length_tuning_scale": length_scale,
        "acoustic_length": acoustic_length,
        "zadj": z_adjust,
        "total_height": total_height,
        "angled_transition_z": transition,
        "accent_ring_z": accent_ring,
        "mouthpiece_overlap": mouthpiece_overlap,
        "tube_joint_overlap": tube_joint_overlap,
        "non_mouthpiece_acoustic_length": non_mouthpiece_length,
        "tube_part_1_length": tube_part_1_length,
        "tube_part_2_length": tube_part_2_length,
        "tube_spacing_factor": number(
            rendering["layout_spacing_factor"],
            "rendering.layout_spacing_factor",
        ),
        "e": positive(rendering["epsilon_mm"], "rendering.epsilon_mm"),
        "connector_radial_clearance": radial_clearance,
        "insert_z_tolerance": insert_tolerance,
        "tone_hole_axial_scale": axial_scale,
        "tone_hole_circumferential_scale": circumferential_scale,
        "tone_hole_corner_ratio": corner_ratio,
        "lower_tube_hole_angle_spread": angle_spread,
        "lower_tube_first_hole_offset": first_offset,
        "lower_tube_hole_spacing": center_spacing,
    }
    for hole in holes:
        key = hole["name"].lower().replace("#", "s")
        params[f"tone_hole_{key}_z"] = hole["physical_z_mm"]
        params[f"tone_hole_{key}_angle"] = hole["angle_deg"]
        params[f"tone_hole_{key}_diameter"] = hole["diameter_mm"]

    manifest = {
        "schema_version": 1,
        "design_id": spec["design_id"],
        "spec_sha256": semantic_hash(spec),
        "generator": "tools/generate_quena.py",
        "geometry": {
            "bore_id_mm": bore_id,
            "outer_diameter_mm": outer_diameter,
            "outlet_id_mm": outlet_id,
            "outlet_outer_diameter_mm": outlet_od,
            "shell_width_mm": shell_width,
            "length_tuning_scale": length_scale,
            "acoustic_length_mm": acoustic_length,
            "mouthpiece_active_length_mm": mouthpiece_active,
            "unacoustic_length_mm": unacoustic_length,
            "z_adjust_mm": z_adjust,
            "non_mouthpiece_length_mm": non_mouthpiece_length,
        },
        "connectors": {
            "mouthpiece_overlap_mm": mouthpiece_overlap,
            "tube_joint_overlap_mm": tube_joint_overlap,
            "radial_clearance_mm": radial_clearance,
            "diametral_clearance_mm": radial_clearance * 2.0,
            "outer_diameter_mm": outer_diameter
            + 2.0 * (shell_width + radial_clearance),
            "wall_width_mm": shell_width,
        },
        "parts": [
            {
                "name": "mouthpiece",
                "length_mm": mouthpiece_total,
                "print_height_mm": print_heights["mouthpiece"],
            },
            {
                "name": "tube_1",
                "start_z_mm": 0.0,
                "length_mm": tube_part_1_length,
                "print_height_mm": print_heights["tube_1"],
            },
            {
                "name": "tube_2",
                "start_z_mm": tube_part_1_length,
                "length_mm": tube_part_2_length,
                "print_height_mm": print_heights["tube_2"],
            },
        ],
        "tone_hole_profile": {
            "shape": profile["shape"],
            "corner_ratio": corner_ratio,
            "axial_scale": axial_scale,
            "circumferential_scale": circumferential_scale,
        },
        "holes": holes,
        "manufacturing_validation": {
            "status": "passed",
            "constraints": constraints,
            "end_ligaments": end_ligaments,
            "axial_ligaments": axial_ligaments,
            "minimum_end_ligament_mm": min(
                min(item["start_mm"], item["end_mm"]) for item in end_ligaments
            ),
            "minimum_axial_ligament_mm": min(
                item["mm"] for item in axial_ligaments
            ),
            "maximum_profile_width_mm": max(
                hole["profile_circumferential_width_mm"] for hole in holes
            ),
            "maximum_print_height_mm": max(print_heights.values()),
        },
    }
    return params, manifest


def render_scad(spec: dict[str, Any], params: dict[str, float]) -> str:
    spec_hash = semantic_hash(spec)
    lines = [
        "// GENERATED FILE. DO NOT EDIT.",
        "// Source: designs/quena.json",
        "// Regenerate: python3 tools/generate_quena.py",
        f'generated_design_id = "{spec["design_id"]}";',
        f'generated_spec_sha256 = "{spec_hash}";',
        "",
    ]
    ordered_names = [
        "quena_facet_count",
        "shell_width",
        "id",
        "od",
        "hd",
        "taper",
        "ido",
        "odo",
        "mouthpiece_total_length",
        "unacoustic_length",
        "mouthpiece_active_length",
        "pitch_raise_cents",
        "length_tuning_scale",
        "acoustic_length",
        "zadj",
        "total_height",
        "angled_transition_z",
        "accent_ring_z",
        "mouthpiece_overlap",
        "tube_joint_overlap",
        "non_mouthpiece_acoustic_length",
        "tube_part_1_length",
        "tube_part_2_length",
    ]
    for name in ordered_names:
        lines.append(f"{name} = {scad_number(params[name])};")
    lines.extend(
        [
            "part_lengths = [tube_part_1_length, tube_part_2_length];",
            "part_start = [0, tube_part_1_length];",
        ]
    )
    for name in (
        "tube_spacing_factor",
        "e",
        "connector_radial_clearance",
        "insert_z_tolerance",
        "tone_hole_axial_scale",
        "tone_hole_circumferential_scale",
        "tone_hole_corner_ratio",
        "lower_tube_hole_angle_spread",
        "lower_tube_first_hole_offset",
        "lower_tube_hole_spacing",
    ):
        lines.append(f"{name} = {scad_number(params[name])};")
    lines.append("")
    for hole_spec in spec["holes"]:
        key = str(hole_spec["name"]).lower().replace("#", "s")
        for suffix in ("z", "angle", "diameter"):
            name = f"tone_hole_{key}_{suffix}"
            lines.append(f"{name} = {scad_number(params[name])};")
    return "\n".join(lines) + "\n"


def render_manifest(manifest: dict[str, Any]) -> str:
    return json.dumps(manifest, indent=2, sort_keys=True) + "\n"


def atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w",
        encoding="utf-8",
        dir=path.parent,
        prefix=f".{path.name}.",
        delete=False,
    ) as handle:
        handle.write(content)
        temporary = Path(handle.name)
    os.replace(temporary, path)


def check_or_write(path: Path, content: str, check: bool) -> bool:
    current = path.read_text(encoding="utf-8") if path.exists() else None
    if current == content:
        print(f"current: {path.relative_to(REPO_ROOT)}")
        return True
    if check:
        print(f"stale: {path.relative_to(REPO_ROOT)}")
        return False
    atomic_write(path, content)
    print(f"wrote: {path.relative_to(REPO_ROOT)}")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--spec", type=Path, default=DEFAULT_SPEC)
    parser.add_argument("--scad-output", type=Path, default=DEFAULT_SCAD_OUTPUT)
    parser.add_argument("--manifest-output", type=Path, default=DEFAULT_MANIFEST_OUTPUT)
    parser.add_argument(
        "--check",
        action="store_true",
        help="fail instead of writing when generated files are missing or stale",
    )
    args = parser.parse_args()

    spec = json.loads(args.spec.read_text(encoding="utf-8"))
    params, manifest = generate(spec)
    results = [
        check_or_write(args.scad_output, render_scad(spec, params), args.check),
        check_or_write(args.manifest_output, render_manifest(manifest), args.check),
    ]
    validation = manifest["manufacturing_validation"]
    print(
        "validated: "
        f"min axial ligament={validation['minimum_axial_ligament_mm']:.2f} mm, "
        f"min end ligament={validation['minimum_end_ligament_mm']:.2f} mm, "
        f"max print height={validation['maximum_print_height_mm']:.2f} mm"
    )
    return 0 if all(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
