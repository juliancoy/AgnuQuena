#!/usr/bin/env python3
import sys
import math
import argparse
import numpy as np
import librosa

NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]

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

def main():
    parser = argparse.ArgumentParser(
        description="Check tuning against 12-tone equal temperament, A4=440 Hz."
    )
    parser.add_argument("audiofile")
    parser.add_argument("--min", type=float, default=80.0, help="minimum frequency to track")
    parser.add_argument("--max", type=float, default=1200.0, help="maximum frequency to track")
    parser.add_argument("--hop", type=int, default=512, help="analysis hop length")
    parser.add_argument("--threshold", type=float, default=0.1, help="minimum voiced probability")
    args = parser.parse_args()

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
