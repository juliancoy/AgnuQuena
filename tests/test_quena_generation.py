import copy
import json
from pathlib import Path

import pytest

from acoustics.quena_1d import geometry_from_manifest
from tools.generate_quena import (
    DesignError,
    generate,
    note_frequency_12tet,
    render_manifest,
    render_scad,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
SPEC_PATH = REPO_ROOT / "designs" / "quena.json"
SCAD_PATH = REPO_ROOT / "generated" / "quena_parameters.scad"
MANIFEST_PATH = REPO_ROOT / "generated" / "quena_manifest.json"


def load_spec():
    return json.loads(SPEC_PATH.read_text(encoding="utf-8"))


def test_generated_artifacts_match_the_canonical_spec():
    spec = load_spec()
    parameters, manifest = generate(spec)

    assert SCAD_PATH.read_text(encoding="utf-8") == render_scad(spec, parameters)
    assert MANIFEST_PATH.read_text(encoding="utf-8") == render_manifest(manifest)


def test_two_wall_shell_and_tight_connector_fit_are_explicit():
    parameters, manifest = generate(load_spec())

    assert parameters["shell_width"] == pytest.approx(0.8)
    assert parameters["od"] == pytest.approx(19.1)
    assert parameters["connector_radial_clearance"] == pytest.approx(0.0)
    assert manifest["connectors"]["radial_clearance_mm"] == pytest.approx(0.0)
    assert manifest["connectors"]["diametral_clearance_mm"] == pytest.approx(0.0)
    assert manifest["connectors"]["outer_diameter_mm"] == pytest.approx(20.7)
    assert manifest["connectors"]["wall_width_mm"] == pytest.approx(0.8)
    assert manifest["connectors"]["mouthpiece_overlap_mm"] == pytest.approx(22.0)
    assert manifest["connectors"]["tube_joint_overlap_mm"] == pytest.approx(7.0)
    mouthpiece = next(
        part for part in manifest["parts"] if part["name"] == "mouthpiece"
    )
    assert mouthpiece["print_height_mm"] == pytest.approx(52.6)


def test_negative_connector_clearance_is_rejected():
    spec = copy.deepcopy(load_spec())
    spec["connectors"]["radial_clearance_mm"] = -0.01

    with pytest.raises(DesignError, match="non-negative"):
        generate(spec)


def test_lower_hand_layout_spans_the_printable_section():
    _, manifest = generate(load_spec())
    holes = {hole["name"]: hole for hole in manifest["holes"]}

    assert holes["C"]["physical_z_mm"] == 242.0
    assert holes["C"]["position"]["local_offset_mm"] == 19.5
    assert holes["B"]["physical_z_mm"] == pytest.approx(273.154575)
    assert holes["B"]["position"]["local_offset_mm"] == pytest.approx(50.654575)
    assert holes["B"]["position"]["axial_adjust_mm"] == pytest.approx(1.154575)
    assert holes["A"]["position"]["local_offset_mm"] == 79.5
    assert holes["B"]["physical_z_mm"] - holes["C"]["physical_z_mm"] == pytest.approx(
        31.154575
    )
    assert holes["A"]["physical_z_mm"] - holes["B"]["physical_z_mm"] == pytest.approx(
        28.845425
    )
    tube_1 = next(part for part in manifest["parts"] if part["name"] == "tube_1")
    assert tube_1["length_mm"] == 222.5


def test_holes_honor_playable_minimums_as_equal_area_rounded_squares():
    _, manifest = generate(load_spec())

    assert manifest["tone_hole_profile"]["corner_ratio"] == pytest.approx(0.4)

    expected_diameters = {
        "A": 10.1,
        "B": 10.5,
        "C": 9.75,
        "D": 10.5,
        "E": 11.1,
        "F#": 11.13,
    }
    for hole in manifest["holes"]:
        assert hole["diameter_mm"] == pytest.approx(
            expected_diameters[hole["name"]]
        )
        assert hole["profile_circumferential_width_mm"] == pytest.approx(
            hole["profile_axial_width_mm"]
        )


def test_measured_compensation_reports_ergonomic_pitch_tradeoff():
    _, manifest = generate(load_spec())
    compensated = [hole for hole in manifest["holes"] if hole["compensation"]]

    assert compensated
    for hole in compensated:
        detail = hole["compensation"]
        assert detail["minimum_applied"] is True
        assert detail["minimum_diameter_mm"] == pytest.approx(hole["diameter_mm"])
        assert detail["acoustically_tuned_diameter_mm"] < hole["diameter_mm"]
        assert detail["estimated_pitch_delta_cents"] > 0.0


def test_measured_compensation_targets_each_explicit_12tet_note():
    spec = load_spec()
    _, manifest = generate(spec)
    speed_of_sound = spec["tonehole_compensation"]["speed_of_sound_mm_s"]

    for hole in manifest["holes"]:
        target_hz = note_frequency_12tet(hole["target_note"])
        assert hole["compensation"]["target_effective_length_mm"] == pytest.approx(
            speed_of_sound / (2.0 * target_hz)
        )


def test_prototype_calibration_does_not_rescale_with_new_body_length():
    spec = load_spec()
    _, baseline = generate(spec)
    changed_spec = copy.deepcopy(spec)
    changed_spec["geometry"]["pitch_raise_cents"] += 10.0
    _, changed = generate(changed_spec)

    baseline_factors = {
        hole["name"]: hole["compensation"]["empirical_factor"]
        for hole in baseline["holes"]
    }
    changed_factors = {
        hole["name"]: hole["compensation"]["empirical_factor"]
        for hole in changed["holes"]
    }
    assert changed_factors == pytest.approx(baseline_factors)


def test_fast_acoustic_model_consumes_generated_corrections():
    geometry = geometry_from_manifest(MANIFEST_PATH)
    corrections = {
        hole.name: hole.calibrated_correction_mm for hole in geometry.holes
    }

    assert corrections["A"] is not None
    assert corrections["B"] is not None
    assert corrections["C"] is not None
    assert corrections["D"] is not None


def test_manufacturing_constraint_violation_rejects_generation():
    spec = copy.deepcopy(load_spec())
    spec["manufacturing_constraints"]["maximum_print_height_mm"] = 200.0

    with pytest.raises(DesignError, match="print height"):
        generate(spec)


def test_overdistributed_lower_hand_layout_rejects_oversized_holes():
    spec = copy.deepcopy(load_spec())
    spec["lower_hand_layout"]["first_center_offset_mm"] = 25.0
    spec["lower_hand_layout"]["center_spacing_mm"] = 40.0

    with pytest.raises(DesignError, match="diameter bounds"):
        generate(spec)
