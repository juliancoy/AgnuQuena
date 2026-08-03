import math
from pathlib import Path

from acoustics.quena_1d import G_SCALE_NOTES, TARGET_HZ, geometry_from_scad, note_frequency_12tet


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_g_scale_targets_use_exact_twelve_tone_equal_temperament():
    expected_semitones_from_g4 = (0, 2, 4, 5, 7, 9, 11, 12)
    g4 = 440.0 * 2.0 ** (-2.0 / 12.0)

    assert tuple(TARGET_HZ) == G_SCALE_NOTES
    for note, semitones in zip(G_SCALE_NOTES, expected_semitones_from_g4):
        expected = g4 * 2.0 ** (semitones / 12.0)
        assert math.isclose(TARGET_HZ[note], expected, rel_tol=1e-14)


def test_pitch_reference_is_concert_a_440():
    assert note_frequency_12tet("A4") == 440.0
    assert note_frequency_12tet("G5") == 2.0 * note_frequency_12tet("G4")


def test_lower_tube_holes_include_the_measured_axial_retune():
    geometry = geometry_from_scad(REPO_ROOT / "Quena.scad")

    assert [hole.name for hole in geometry.holes] == ["A", "B", "C", "D", "E", "F#"]
    a_hole, b_hole, c_hole = geometry.holes[:3]
    assert math.isclose(b_hole.acoustic_mm, 307.0, abs_tol=1e-9)
    assert math.isclose(a_hole.acoustic_mm - b_hole.acoustic_mm, 34.437)
    assert math.isclose(b_hole.acoustic_mm - c_hole.acoustic_mm, 21.826)
    assert [hole.diameter_mm for hole in (a_hole, b_hole, c_hole)] == [9.5, 10.63, 9.75]
