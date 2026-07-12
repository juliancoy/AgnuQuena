#!/usr/bin/env python3
"""Accuracy report for tunecheck's streaming pitch-detector backends."""

import math
from pathlib import Path
import sys
import tempfile
import unittest

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import tunecheck


SAMPLE_RATE = 44100
BLOCK_SECONDS = 0.25
BLOCK_FRAMES = int(SAMPLE_RATE * BLOCK_SECONDS)
BLOCKS_PER_NOTE = 8
BACKENDS = ("loiacono", "librosa")


def synthetic_flute_note(frequency, frames, start_frame):
    """Return an exactly tuned, continuous-phase flute-like audio block."""
    sample = np.arange(start_frame, start_frame + frames, dtype=float)
    phase = 2 * np.pi * frequency * sample / SAMPLE_RATE
    # The fundamental remains dominant, with realistic weaker harmonics.
    audio = (0.70 * np.sin(phase)
             + 0.20 * np.sin(2 * phase)
             + 0.08 * np.sin(3 * phase))
    return audio.astype(np.float32)


def cents_error(measured, target):
    return 1200 * math.log2(measured / target)


def run_accuracy_report():
    results = {backend: [] for backend in BACKENDS}
    for note in tunecheck.GUIDED_NOTES:
        target = tunecheck.midi_to_hz(tunecheck.name_to_midi(note))
        fmin = target / (2 ** (tunecheck.GUIDED_SEARCH_SEMITONES / 12))
        fmax = target * (2 ** (tunecheck.GUIDED_SEARCH_SEMITONES / 12))
        trackers = {
            "loiacono": tunecheck.make_loiacono_tracker(
                SAMPLE_RATE, fmin, fmax
            ),
            "librosa": None,
        }
        for backend in BACKENDS:
            errors = []
            for block_index in range(BLOCKS_PER_NOTE):
                audio = synthetic_flute_note(
                    target, BLOCK_FRAMES, block_index * BLOCK_FRAMES
                )
                measured = tunecheck.estimate_pitch(
                    audio, SAMPLE_RATE, fmin, fmax, backend,
                    trackers[backend],
                )
                errors.append(cents_error(measured, target))
            results[backend].append((note, float(np.median(errors))))
    return results


def format_report(results):
    lines = [
        "Perfect-tuning streaming accuracy report",
        f"sample rate: {SAMPLE_RATE} Hz; block: {BLOCK_SECONDS:.2f} s; "
        f"blocks/note: {BLOCKS_PER_NOTE}",
        "",
        "note\tloiacono_cents\tlibrosa_cents",
    ]
    by_backend = {backend: dict(values) for backend, values in results.items()}
    for note in tunecheck.GUIDED_NOTES:
        lines.append(
            f"{note}\t{by_backend['loiacono'][note]:+.3f}"
            f"\t{by_backend['librosa'][note]:+.3f}"
        )
    lines.extend(["", "algorithm\tmean_abs_cents\trms_cents\tmax_abs_cents"])
    for backend in BACKENDS:
        errors = np.array([error for _, error in results[backend]])
        lines.append(
            f"{backend}\t{np.mean(np.abs(errors)):.3f}"
            f"\t{np.sqrt(np.mean(errors ** 2)):.3f}"
            f"\t{np.max(np.abs(errors)):.3f}"
        )
    return "\n".join(lines)


class StreamingTunerAccuracyTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.results = run_accuracy_report()
        print("\n" + format_report(cls.results))

    def test_every_algorithm_is_accurate(self):
        # Five cents is the conventional boundary for "in tune" in tunecheck.
        for backend, readings in self.results.items():
            with self.subTest(backend=backend):
                worst = max(abs(error) for _, error in readings)
                self.assertLess(worst, 5.0)

    def test_guided_report_contains_both_algorithms(self):
        target = tunecheck.midi_to_hz(tunecheck.name_to_midi("G4"))
        rows = []
        for algorithm, error in (("loiacono", -1.0), ("librosa", 1.5)):
            rows.append({
                "note": "G4", "algorithm": algorithm,
                "frequency_hz": target * 2 ** (error / 1200),
                "cents": error,
            })
        with tempfile.TemporaryDirectory() as directory:
            report = Path(directory) / "guided.md"
            summary = tunecheck.write_guided_report(
                report, rows, SAMPLE_RATE, 6.0
            )
            text = report.read_text(encoding="utf-8")
        self.assertIn("| G4 | loiacono |", text)
        self.assertIn("| G4 | librosa |", text)
        self.assertEqual(
            sum(item["samples"] for item in summary if item["note"] == "G4"),
            2,
        )

    def test_live_display_shows_tuning_boundaries(self):
        display = tunecheck.render_guided_display(
            "A4", 440.0, "free sweep", {"loiacono": -7.0, "librosa": 4.0},
            {"loiacono": [-12.0, 8.0], "librosa": [-3.0, 6.0]}, 0.1,
        )
        self.assertIn("boundary -12.0 .. +8.0c", display)
        self.assertIn("boundary -3.0 .. +6.0c", display)
        self.assertIn("flat", display)
        self.assertIn("sharp", display)
        self.assertIn("dBFS", display)
        level_line = next(line for line in display.splitlines()
                          if "Level" in line)
        self.assertEqual(level_line.count("█") + level_line.count("░"), 30)

    def test_guided_search_range_is_wider_than_boundary_sweep(self):
        self.assertGreater(tunecheck.GUIDED_SEARCH_SEMITONES, 1)

    def test_guided_octave_note_sequences(self):
        self.assertEqual(
            tunecheck.guided_notes_for_octaves(1),
            ["G4", "A4", "B4", "C5", "D5", "E5", "F#5", "G5"],
        )
        self.assertEqual(tunecheck.guided_notes_for_octaves(2),
                         tunecheck.GUIDED_NOTES)

    def test_guided_sample_requires_level_and_both_pitch_readings(self):
        readings = {"loiacono": 440.0, "librosa": 440.1}
        self.assertTrue(tunecheck.guided_sample_is_ready(0.01, readings, 69))
        self.assertFalse(tunecheck.guided_sample_is_ready(0.001, readings, 69))
        self.assertFalse(tunecheck.guided_sample_is_ready(
            0.01, {"loiacono": np.nan, "librosa": 440.1}, 69
        ))
        self.assertFalse(tunecheck.guided_sample_is_ready(
            0.01, {"loiacono": 523.25, "librosa": 523.25}, 69
        ))


if __name__ == "__main__":
    unittest.main(verbosity=2)
