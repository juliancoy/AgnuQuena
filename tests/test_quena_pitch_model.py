import math

from acoustics.quena_1d import G_SCALE_NOTES, TARGET_HZ, note_frequency_12tet


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
