#!/usr/bin/env python3
import sys
import math
import argparse
import csv
from datetime import datetime
import time
from pathlib import Path
import numpy as np
import librosa

NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
GUIDED_NOTES = ["G4", "A4", "B4", "C5", "D5", "E5", "F#5",
                "G5", "A5", "B5", "C6", "D6", "E6", "F#6", "G6"]

def hz_to_midi(f):
    return 69 + 12 * math.log2(f / 440.0)

def midi_to_hz(m):
    return 440.0 * (2 ** ((m - 69) / 12))

def midi_to_name(m):
    n = int(round(m))
    name = NOTE_NAMES[n % 12]
    octave = (n // 12) - 1
    return f"{name}{octave}"

def cents_off(freq, midi_nearest):
    target = midi_to_hz(midi_nearest)
    return 1200 * math.log2(freq / target)

def name_to_midi(note):
    split = 2 if len(note) > 2 and note[1] == "#" else 1
    return (int(note[split:]) + 1) * 12 + NOTE_NAMES.index(note[:split])

def require_sounddevice():
    try:
        import sounddevice as sd
    except ImportError:
        raise SystemExit(
            "Recording requires the optional 'sounddevice' package. "
            "Install it with: python3 -m pip install sounddevice"
        )
    return sd

def record_audio(duration, sample_rate):
    sd = require_sounddevice()

    print(
        "Play every note across all two octaves of the flute, holding each note "
        "steady for a moment."
    )
    print(f"Recording for {duration:g} seconds...", flush=True)
    try:
        audio = sd.rec(
            int(duration * sample_rate),
            samplerate=sample_rate,
            channels=1,
            dtype="float32",
        )
        sd.wait()
    except Exception as exc:
        raise SystemExit(f"Could not record audio: {exc}") from exc

    print("Recording complete; processing immediately.")
    return audio[:, 0], sample_rate

def make_loiacono_tracker(sample_rate, fmin, fmax):
    loiacono_parent = Path(__file__).resolve().parent.parent
    if str(loiacono_parent) not in sys.path:
        sys.path.insert(0, str(loiacono_parent))
    try:
        from loiacono import LoiaconoPitchTracker
    except ImportError as exc:
        raise SystemExit(
            f"Could not load the Loiacono Python interface from "
            f"{loiacono_parent / 'loiacono'}: {exc}"
        ) from exc
    return LoiaconoPitchTracker(sample_rate, fmin=fmin, fmax=fmax)


def estimate_pitch(audio, sample_rate, fmin, fmax, tuner, tracker=None):
    if tuner == "loiacono":
        tracker = tracker or make_loiacono_tracker(sample_rate, fmin, fmax)
        return tracker.estimate(audio)[0]
    pitches = librosa.yin(
        audio, fmin=fmin, fmax=fmax, sr=sample_rate,
        frame_length=2048, hop_length=256,
    )
    return float(np.median(pitches))


def summarize_guided_rows(rows):
    summary = []
    for note in GUIDED_NOTES:
        target = midi_to_hz(name_to_midi(note))
        for algorithm in ("loiacono", "librosa"):
            values = [row for row in rows
                      if row["note"] == note
                      and row["algorithm"] == algorithm
                      and row["frequency_hz"] is not None]
            if values:
                frequencies = np.array([row["frequency_hz"] for row in values])
                cents = np.array([row["cents"] for row in values])
                summary.append({
                    "note": note,
                    "algorithm": algorithm,
                    "samples": len(values),
                    "frequency_hz": float(np.median(frequencies)),
                    "target_hz": target,
                    "cents": float(np.median(cents)),
                    "stability": float(np.std(cents)),
                    "min_cents": float(np.min(cents)),
                    "max_cents": float(np.max(cents)),
                })
            else:
                summary.append({
                    "note": note, "algorithm": algorithm, "samples": 0,
                    "frequency_hz": None, "target_hz": target,
                    "cents": None, "stability": None,
                    "min_cents": None, "max_cents": None,
                })
    return summary


def write_guided_report(path, rows, sample_rate, seconds_per_note):
    summary = summarize_guided_rows(rows)
    lines = [
        "# Guided tuning measurement",
        "",
        f"Sample rate: {sample_rate} Hz  ",
        f"Requested duration per note: {seconds_per_note:g} seconds  ",
        "Gesture: grade loud to soft and tilt the flute back to forth.",
        "",
        "| Note | Algorithm | Blocks | Median Hz | Target Hz | Median cents | "
        "Stability | Range cents |",
        "|---|---|---:|---:|---:|---:|---:|---:|",
    ]
    for item in summary:
        if item["frequency_hz"] is None:
            lines.append(
                f"| {item['note']} | {item['algorithm']} | 0 | -- | "
                f"{item['target_hz']:.2f} | -- | -- | -- |"
            )
        else:
            lines.append(
                f"| {item['note']} | {item['algorithm']} | {item['samples']} | "
                f"{item['frequency_hz']:.2f} | {item['target_hz']:.2f} | "
                f"{item['cents']:+.1f} | {item['stability']:.1f} | "
                f"{item['min_cents']:+.1f} to {item['max_cents']:+.1f} |"
            )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return summary


def tuning_bar(cents, width=31):
    """Render a fixed -50..+50 cent scale with a centered in-tune zone."""
    cells = ["─"] * width
    center = width // 2
    for index in range(max(0, center - 1), min(width, center + 2)):
        cells[index] = "·"
    cells[center] = "│"
    if cents is not None:
        position = int(round((np.clip(cents, -50, 50) + 50) * (width - 1) / 100))
        cells[position] = "●"
    return "".join(cells)


def render_guided_display(note, target, gesture, readings, boundaries, rms):
    def reading_line(label, algorithm):
        cents = readings.get(algorithm)
        low, high = boundaries.get(algorithm, (None, None))
        current = " quiet " if cents is None else f"{cents:+6.1f}c"
        extent = ("no boundary yet" if low is None else
                  f"boundary {low:+.1f} .. {high:+.1f}c")
        return (f"│ {label:<8} {tuning_bar(cents)} {current}  "
                f"{extent:<24} │")

    loudness = min(20, int(round(rms * 80)))
    meter = "█" * loudness + "░" * (20 - loudness)
    return "\n".join([
        f"╭─ {note}  target {target:.2f} Hz " + "─" * 49 + "╮",
        f"│ Motion   {gesture:<65} │",
        f"│ Level    {meter}  RMS {rms:0.4f}"
        + " " * 37 + "│",
        reading_line("Loiacono", "loiacono"),
        reading_line("librosa", "librosa"),
        "╰──────── flat ←─────── [ ±5 cents ] ───────→ sharp ─────────╯",
    ])


def guided_test(sample_rate, hold_seconds, timeout):
    sd = require_sounddevice()
    block_seconds = 0.25
    block_frames = int(sample_rate * block_seconds)
    seconds_per_note = min(hold_seconds, timeout)
    blocks_per_note = max(1, math.ceil(seconds_per_note / block_seconds))
    rows = []
    measurements = Path(__file__).resolve().parent / "measurements"
    measurements.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().astimezone().strftime("%Y-%m-%d-%H%M%S%z")
    csv_path = measurements / f"{stamp}-guided-tuning.csv"
    report_path = measurements / f"{stamp}-guided-tuning.md"
    fields = ["note", "target_hz", "block", "elapsed_s", "gesture",
              "rms", "algorithm", "frequency_hz", "cents"]

    print("Guided two-octave tuning test")
    print("For every note, grade loud to soft and tilt back to forth.")
    print("Repeat or reverse that motion as many times as you want during the recording.")
    print("The test records the flattest and sharpest tuning boundaries; it does not count cycles.")
    print("Keep the fingering fixed throughout the gesture. Press Ctrl+C to stop.")
    print(f"Every block from both algorithms will be saved to {csv_path}\n")

    try:
        with csv_path.open("w", newline="", encoding="utf-8") as output:
            writer = csv.DictWriter(output, fieldnames=fields)
            writer.writeheader()
            for index, note in enumerate(GUIDED_NOTES, 1):
                target = midi_to_hz(name_to_midi(note))
                fmin = target / (2 ** (1 / 12))
                fmax = target * (2 ** (1 / 12))
                tracker = make_loiacono_tracker(sample_rate, fmin, fmax)
                print(
                    f"[{index}/{len(GUIDED_NOTES)}] {note} ({target:.2f} Hz): "
                    "explore loud/soft and back/forth boundaries"
                )
                boundaries = {"loiacono": [None, None], "librosa": [None, None]}
                dashboard_drawn = False
                for block in range(blocks_per_note):
                    progress = (block + 0.5) / blocks_per_note
                    gesture = f"free sweep ({progress:3.0%} of recording)"
                    started = time.monotonic()
                    try:
                        audio = sd.rec(
                            block_frames, samplerate=sample_rate, channels=1,
                            dtype="float32", blocking=True,
                        )[:, 0]
                    except Exception as exc:
                        raise SystemExit(f"Could not record audio: {exc}") from exc
                    rms = float(np.sqrt(np.mean(audio ** 2)))
                    readings = {}
                    for algorithm in ("loiacono", "librosa"):
                        frequency = estimate_pitch(
                            audio, sample_rate, fmin, fmax, algorithm,
                            tracker if algorithm == "loiacono" else None,
                        )
                        valid = (rms >= 0.003 and np.isfinite(frequency))
                        cents = (cents_off(frequency, name_to_midi(note))
                                 if valid else None)
                        row = {
                            "note": note, "target_hz": target,
                            "block": block + 1,
                            "elapsed_s": (block * block_seconds
                                          + time.monotonic() - started),
                            "gesture": gesture, "rms": rms,
                            "algorithm": algorithm,
                            "frequency_hz": frequency if valid else None,
                            "cents": cents,
                        }
                        rows.append(row)
                        writer.writerow(row)
                        readings[algorithm] = cents
                        if cents is not None:
                            low, high = boundaries[algorithm]
                            boundaries[algorithm] = [
                                cents if low is None else min(low, cents),
                                cents if high is None else max(high, cents),
                            ]
                    output.flush()
                    dashboard = render_guided_display(
                        note, target, gesture, readings, boundaries, rms
                    )
                    if sys.stdout.isatty():
                        if dashboard_drawn:
                            print("\x1b[6A", end="")
                        print(dashboard, flush=True)
                        dashboard_drawn = True
                    else:
                        values = "; ".join(
                            f"{name} {value:+.1f}c" if value is not None
                            else f"{name} quiet"
                            for name, value in readings.items()
                        )
                        print(f"  {gesture}: {values}")
                if sys.stdout.isatty():
                    print()
    except KeyboardInterrupt:
        print("\nStopped early; preserving all measurements collected so far.")
    finally:
        summary = write_guided_report(
            report_path, rows, sample_rate, seconds_per_note
        )

    print("\nGuided tuning summary:")
    print("note\talgorithm\tmeasured_hz\ttarget_hz\tcents\tstability\trange")
    for item in summary:
        if item["frequency_hz"] is None:
            print(f"{item['note']}\t{item['algorithm']}\t--\t"
                  f"{item['target_hz']:.2f}\t--\t--\t--")
        else:
            print(
                f"{item['note']}\t{item['algorithm']}\t"
                f"{item['frequency_hz']:.2f}\t{item['target_hz']:.2f}\t"
                f"{item['cents']:+.1f}\t{item['stability']:.1f}\t"
                f"{item['min_cents']:+.1f}..{item['max_cents']:+.1f}"
            )
    print(f"\nRaw measurements: {csv_path}")
    print(f"Summary report:   {report_path}")

def main():
    parser = argparse.ArgumentParser(
        description="Check tuning against 12-tone equal temperament, A4=440 Hz."
    )
    inputs = parser.add_mutually_exclusive_group(required=True)
    inputs.add_argument("audiofile", nargs="?", help="audio file to analyze")
    inputs.add_argument(
        "--record",
        nargs="?",
        type=float,
        const=30.0,
        metavar="SECONDS",
        help="record from the default microphone (default: 30 seconds)",
    )
    inputs.add_argument(
        "--guided",
        action="store_true",
        help="run a live, note-by-note two-octave tuning test",
    )
    parser.add_argument(
        "--sample-rate",
        type=int,
        default=44100,
        help="sample rate used for recording (default: 44100)",
    )
    parser.add_argument("--min", type=float, default=80.0, help="minimum frequency to track")
    parser.add_argument("--max", type=float, default=1200.0, help="maximum frequency to track")
    parser.add_argument("--hop", type=int, default=512, help="analysis hop length")
    parser.add_argument("--threshold", type=float, default=0.1, help="minimum voiced probability")
    parser.add_argument(
        "--tuner", choices=("loiacono", "librosa"), default="loiacono",
        help="file/recording pitch detector; guided mode always runs both "
             "(default: loiacono)",
    )
    parser.add_argument("--hold", type=float, default=6.0,
                        help="gesture recording time per guided note (default: 6)")
    parser.add_argument("--timeout", type=float, default=20.0,
                        help="maximum recording time per guided note (default: 20)")
    args = parser.parse_args()

    if args.guided:
        if args.sample_rate <= 0 or args.hold <= 0 or args.timeout <= 0:
            parser.error("--sample-rate, --hold, and --timeout must be greater than zero")
        guided_test(args.sample_rate, args.hold, args.timeout)
        return
    elif args.record is not None:
        if args.record <= 0:
            parser.error("--record duration must be greater than zero")
        if args.sample_rate <= 0:
            parser.error("--sample-rate must be greater than zero")
        y, sr = record_audio(args.record, args.sample_rate)
    else:
        y, sr = librosa.load(args.audiofile, sr=None, mono=True)

    if args.tuner == "loiacono":
        track = make_loiacono_tracker(sr, args.min, args.max).track(
            y, hop_length=args.hop, confidence_threshold=args.threshold
        )
        f0, voiced_flag, voiced_prob = (
            track.frequencies, track.voiced, track.confidence
        )
    else:
        f0, voiced_flag, voiced_prob = librosa.pyin(
            y, fmin=args.min, fmax=args.max, sr=sr, hop_length=args.hop,
        )

    times = librosa.frames_to_time(np.arange(len(f0)), sr=sr, hop_length=args.hop)

    rows = []
    for t, freq, voiced, prob in zip(times, f0, voiced_flag, voiced_prob):
        if freq is None or np.isnan(freq) or not voiced or prob < args.threshold:
            continue

        midi = hz_to_midi(freq)
        nearest = int(round(midi))
        note = midi_to_name(nearest)
        target = midi_to_hz(nearest)
        cents = cents_off(freq, nearest)

        rows.append((t, freq, note, target, cents))

    if not rows:
        print("No stable pitched notes detected.")
        return

    print()
    print("Per-frame tuning estimate:")
    print("time_s\tfreq_hz\tnote\ttarget_hz\tcents")
    for t, freq, note, target, cents in rows:
        print(f"{t:.3f}\t{freq:.2f}\t{note}\t{target:.2f}\t{cents:+.1f}")

    print()
    print("Summary by detected note:")
    print("note\tframes\tmedian_hz\ttarget_hz\tmedian_cents\tmeaning")

    by_note = {}
    for _, freq, note, target, cents in rows:
        by_note.setdefault(note, []).append((freq, target, cents))

    for note in sorted(by_note.keys(), key=lambda n: NOTE_NAMES.index(n[:-1].replace("#", "#")) if n[:-1] in NOTE_NAMES else 999):
        vals = by_note[note]
        freqs = np.array([v[0] for v in vals])
        target = vals[0][1]
        cents_vals = np.array([v[2] for v in vals])
        med_freq = np.median(freqs)
        med_cents = np.median(cents_vals)

        if abs(med_cents) < 5:
            meaning = "in tune"
        elif med_cents > 0:
            meaning = "sharp"
        else:
            meaning = "flat"

        print(
            f"{note}\t{len(vals)}\t{med_freq:.2f}\t{target:.2f}\t{med_cents:+.1f}\t{meaning}"
        )

if __name__ == "__main__":
    main()
