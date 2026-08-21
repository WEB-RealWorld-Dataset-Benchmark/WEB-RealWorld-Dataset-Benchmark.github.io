#!/usr/bin/env python3
"""Generate an original, royalty-free ambient electronic teaser soundtrack."""

import argparse
import wave

import numpy as np


SAMPLE_RATE = 44_100
BPM = 82
BEAT = 60.0 / BPM


def tone(freq, seconds, phase=0.0):
    t = np.arange(int(seconds * SAMPLE_RATE), dtype=np.float64) / SAMPLE_RATE
    return np.sin(2 * np.pi * freq * t + phase)


def add_note(track, start, seconds, freq, gain, pan=0.0, attack=0.02, release=0.25):
    start_i = int(start * SAMPLE_RATE)
    length = min(int(seconds * SAMPLE_RATE), len(track) - start_i)
    if length <= 0:
        return
    x = tone(freq, length / SAMPLE_RATE)[:length]
    x += 0.26 * tone(freq * 2, length / SAMPLE_RATE, 0.4)[:length]
    x += 0.08 * tone(freq * 3, length / SAMPLE_RATE, 0.9)[:length]
    env = np.ones(length)
    a = min(int(attack * SAMPLE_RATE), length)
    r = min(int(release * SAMPLE_RATE), length)
    if a:
        env[:a] = np.linspace(0, 1, a)
    if r:
        env[-r:] *= np.linspace(1, 0, r)
    left = np.sqrt((1 - pan) / 2)
    right = np.sqrt((1 + pan) / 2)
    track[start_i:start_i + length, 0] += gain * left * x * env
    track[start_i:start_i + length, 1] += gain * right * x * env


def add_epiano(track, start, seconds, freq, gain, pan=0.0):
    """A mellow electric-piano voice with a soft tine and long decay."""
    start_i = int(start * SAMPLE_RATE)
    length = min(int(seconds * SAMPLE_RATE), len(track) - start_i)
    if length <= 0:
        return
    t = np.arange(length) / SAMPLE_RATE
    body = np.sin(2 * np.pi * freq * t)
    tine = np.sin(2 * np.pi * freq * 2.01 * t + 0.35) * np.exp(-t * 2.4)
    warmth = np.sin(2 * np.pi * freq * 0.5 * t + 0.7)
    x = (0.78 * body + 0.20 * tine + 0.10 * warmth) * np.exp(-t * 0.52)
    attack = min(int(0.018 * SAMPLE_RATE), length)
    x[:attack] *= np.linspace(0, 1, attack)
    release = min(int(0.7 * SAMPLE_RATE), length)
    x[-release:] *= np.linspace(1, 0, release)
    left = np.sqrt((1 - pan) / 2)
    right = np.sqrt((1 + pan) / 2)
    track[start_i:start_i + length, 0] += gain * left * x
    track[start_i:start_i + length, 1] += gain * right * x


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("output")
    parser.add_argument("--duration", type=float, required=True)
    args = parser.parse_args()

    rng = np.random.default_rng(20260821)
    frames = int(args.duration * SAMPLE_RATE)
    mix = np.zeros((frames, 2), dtype=np.float64)

    # Jazz-lounge turnaround: Dm9 - G13 - Cmaj9 - A7(b9).
    chords = [
        [146.83, 174.61, 220.00, 261.63, 329.63],
        [123.47, 164.81, 220.00, 246.94, 329.63],
        [130.81, 164.81, 196.00, 246.94, 293.66],
        [138.59, 164.81, 207.65, 233.08, 311.13],
    ]
    roots = [73.42, 49.00, 65.41, 55.00]
    chord_len = 4 * BEAT
    chord_count = int(np.ceil(args.duration / chord_len))
    for i in range(chord_count):
        start = i * chord_len
        chord = chords[i % len(chords)]
        for n, freq in enumerate(chord):
            add_epiano(mix, start, chord_len + 0.35, freq, 0.068, pan=(-0.46 + n * 0.23))
        root = roots[i % len(roots)]
        add_note(mix, start, BEAT * 1.8, root, 0.095, attack=0.08, release=0.55)
        add_note(mix, start + 2 * BEAT, BEAT * 1.55, root * 1.5, 0.065, attack=0.06, release=0.5)

    # Sparse upper-register piano phrases, leaving plenty of room for the visuals.
    scale = [261.63, 293.66, 329.63, 349.23, 392.00, 440.00, 493.88]
    motif = [2, 4, 6, 4, 3, 1, 2, 5]
    total_beats = int(args.duration / BEAT)
    for beat_i in range(total_beats):
        if beat_i % 4 in (1, 3) and (beat_i // 4) % 2 == 0:
            idx = motif[(beat_i // 2) % len(motif)]
            pan = -0.22 if beat_i % 4 == 1 else 0.22
            add_epiano(mix, beat_i * BEAT, BEAT * 1.2, scale[idx], 0.040, pan=pan)

    # Hotel-lounge rhythm: a soft downbeat and quiet brushed offbeats.
    for beat_i in range(total_beats):
        start_i = int(beat_i * BEAT * SAMPLE_RATE)
        kick_len = min(int(0.23 * SAMPLE_RATE), frames - start_i)
        if kick_len > 0 and beat_i % 4 == 0:
            t = np.arange(kick_len) / SAMPLE_RATE
            phase = 2 * np.pi * (72 * t - 35 * t * t)
            kick = np.sin(phase) * np.exp(-t * 18) * 0.10
            mix[start_i:start_i + kick_len] += kick[:, None]
        hat_start = int((beat_i + 0.5) * BEAT * SAMPLE_RATE)
        hat_len = min(int(0.11 * SAMPLE_RATE), frames - hat_start)
        if hat_len > 0:
            t = np.arange(hat_len) / SAMPLE_RATE
            noise = rng.normal(0, 1, hat_len)
            noise = np.concatenate(([0], np.diff(noise)))
            hat = noise * np.exp(-t * 30) * 0.010
            mix[hat_start:hat_start + hat_len, 0] += hat * 0.8
            mix[hat_start:hat_start + hat_len, 1] += hat

    # Subtle room-like delays create width without external samples.
    for delay_s, gain, swap in [(0.19, 0.15, True), (0.37, 0.09, False)]:
        delay = int(delay_s * SAMPLE_RATE)
        source = mix[:-delay, ::-1] if swap else mix[:-delay]
        mix[delay:] += source * gain

    fade = min(int(4.0 * SAMPLE_RATE), frames // 2)
    mix[:fade] *= np.linspace(0, 1, fade)[:, None]
    mix[-fade:] *= np.linspace(1, 0, fade)[:, None]
    peak = np.max(np.abs(mix)) or 1.0
    mix *= 0.82 / peak
    pcm = np.int16(np.clip(mix, -1, 1) * 32767)

    with wave.open(args.output, "wb") as wav:
        wav.setnchannels(2)
        wav.setsampwidth(2)
        wav.setframerate(SAMPLE_RATE)
        wav.writeframes(pcm.tobytes())


if __name__ == "__main__":
    main()
