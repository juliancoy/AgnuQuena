#!/usr/bin/env python3
import sys
import math
import argparse
import time
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

def guided_test(sample_rate, hold_seconds, timeout):
    sd = require_sounddevice()
    block_seconds = 0.25
    block_frames = int(sample_rate * block_seconds)
    required = max(3, math.ceil(hold_seconds / block_seconds))
    results = []

    print("Guided two-octave tuning test")
    print("Play the requested note and hold it steadily. Press Ctrl+C to stop.\n")

    for index, note in enumerate(GUIDED_NOTES, 1):
        target = midi_to_hz(name_to_midi(note))
        recent = []
        started = time.monotonic()
        print(f"[{index}/{len(GUIDED_NOTES)}] Play {note} ({target:.2f} Hz)")

        while time.monotonic() - started < timeout:
            try:
                audio = sd.rec(block_frames, samplerate=sample_rate, channels=1,
                               dtype="float32", blocking=True)[:, 0]
            except Exception as exc:
                raise SystemExit(f"Could not record audio: {exc}") from exc

            rms = float(np.sqrt(np.mean(audio ** 2)))
            if rms < 0.003:
                recent.clear()
                status = "too quiet"
            else:
                pitches = librosa.yin(
                    audio,
                    fmin=target / (2 ** (1 / 12)),
                    fmax=target * (2 ** (1 / 12)),
                    sr=sample_rate,
                    frame_length=2048,
                    hop_length=256,
                )
                freq = float(np.median(pitches))
                cents = cents_off(freq, name_to_midi(note))
                if abs(cents) > 80:
                    recent.clear()
                    status = f"wrong/unstable pitch ({cents:+.1f} cents)"
                else:
                    recent.append(freq)
                    recent = recent[-required:]
                    spread = (np.std([cents_off(f, name_to_midi(note)) for f in recent])
                              if len(recent) > 1 else 0.0)
                    status = f"{freq:7.2f} Hz  {cents:+6.1f} cents  stability {spread:4.1f}"
                    if len(recent) == required and spread <= 5.0:
                        med_freq = float(np.median(recent))
                        med_cents = cents_off(med_freq, name_to_midi(note))
                        results.append((note, med_freq, target, med_cents, spread))
                        print(f"\r  captured: {med_cents:+.1f} cents{' ' * 45}\n")
                        break
            print(f"\r  {status:<70}", end="", flush=True)
        else:
            results.append((note, None, target, None, None))
            print(f"\r  timed out; no stable sample captured{' ' * 35}\n")

    print("Guided tuning summary:")
    print("note\tmeasured_hz\ttarget_hz\tcents\tstability")
    for note, freq, target, cents, spread in results:
        if freq is None:
            print(f"{note}\t--\t{target:.2f}\t--\tno sample")
        else:
            print(f"{note}\t{freq:.2f}\t{target:.2f}\t{cents:+.1f}\t{spread:.1f}")

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
    parser.add_argument("--hold", type=float, default=1.5,
                        help="stable seconds required per guided note (default: 1.5)")
    parser.add_argument("--timeout", type=float, default=20.0,
                        help="seconds allowed per guided note (default: 20)")
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

    f0, voiced_flag, voiced_prob = librosa.pyin(
        y,
        fmin=args.min,
        fmax=args.max,
        sr=sr,
        hop_length=args.hop,
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
