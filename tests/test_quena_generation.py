import copy
import json
from pathlib import Path

import pytest

from acoustics.quena_1d import geometry_from_manifest
from tools.generate_quena import (
    DesignError,
    generate,
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


def test_lower_hand_layout_spans_the_printable_section():
    _, manifest = generate(load_spec())
    holes = {hole["name"]: hole for hole in manifest["holes"]}

    assert holes["C"]["position"]["local_offset_mm"] == 25.0
    assert holes["B"]["position"]["local_offset_mm"] == 65.0
    assert holes["A"]["position"]["local_offset_mm"] == 105.0
    assert holes["B"]["physical_z_mm"] - holes["C"]["physical_z_mm"] == 40.0
    assert holes["A"]["physical_z_mm"] - holes["B"]["physical_z_mm"] == 40.0


def test_measured_compensation_stays_inside_half_a_cent():
    _, manifest = generate(load_spec())
    compensated = [hole for hole in manifest["holes"] if hole["compensation"]]

    assert compensated
    for hole in compensated:
        assert abs(hole["compensation"]["estimated_pitch_delta_cents"]) < 0.5


def test_fast_acoustic_model_consumes_generated_corrections():
    geometry = geometry_from_manifest(MANIFEST_PATH)
    corrections = {
        hole.name: hole.calibrated_correction_mm for hole in geometry.holes
    }

    assert corrections["A"] is not None
    assert corrections["B"] is not None
    assert corrections["C"] is not None
    assert corrections["D"] is None


def test_manufacturing_constraint_violation_rejects_generation():
    spec = copy.deepcopy(load_spec())
    spec["manufacturing_constraints"]["maximum_print_height_mm"] = 200.0

    with pytest.raises(DesignError, match="print height"):
        generate(spec)
