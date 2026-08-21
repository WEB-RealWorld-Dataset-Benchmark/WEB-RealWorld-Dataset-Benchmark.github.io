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


def add_sax(track, start, seconds, freq, gain, rng, pan=0.08):
    """A restrained breathy sax-like lead with slow vibrato."""
    start_i = int(start * SAMPLE_RATE)
    length = min(int(seconds * SAMPLE_RATE), len(track) - start_i)
    if length <= 0:
        return
    t = np.arange(length) / SAMPLE_RATE
    vibrato = 0.006 * np.sin(2 * np.pi * 5.1 * t) * (1 - np.exp(-t * 3.0))
    phase = 2 * np.pi * freq * np.cumsum(1 + vibrato) / SAMPLE_RATE
    x = np.sin(phase) + 0.34 * np.sin(2 * phase + 0.2) + 0.12 * np.sin(3 * phase + 0.7)
    breath = rng.normal(0, 1, length)
    breath = np.convolve(breath, np.ones(18) / 18, mode="same")
    x = 0.62 * x + 0.055 * breath
    env = np.ones(length)
    attack = min(int(0.11 * SAMPLE_RATE), length)
    release = min(int(0.38 * SAMPLE_RATE), length)
    env[:attack] = np.linspace(0, 1, attack)
    env[-release:] *= np.linspace(1, 0, release)
    left = np.sqrt((1 - pan) / 2)
    right = np.sqrt((1 + pan) / 2)
    track[start_i:start_i + length, 0] += gain * left * x * env
    track[start_i:start_i + length, 1] += gain * right * x * env


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
        progress = start / args.duration
        chord = chords[i % len(chords)]
        piano_gain = 0.050 if progress < 0.14 else (0.068 if progress < 0.82 else 0.045)
        for n, freq in enumerate(chord):
            add_epiano(mix, start, chord_len + 0.35, freq, piano_gain, pan=(-0.46 + n * 0.23))
        root = roots[i % len(roots)]
        if 0.04 < progress < 0.93:
            bass_gain = 0.105 if progress < 0.34 else 0.135
            add_note(mix, start, BEAT * 1.35, root, bass_gain, attack=0.07, release=0.45)
            add_note(mix, start + 1.5 * BEAT, BEAT * 0.8, root * 1.5, bass_gain * 0.62, attack=0.04, release=0.32)
            if 0.30 < progress < 0.84:
                add_note(mix, start + 3 * BEAT, BEAT * 0.72, root * 2, bass_gain * 0.48, attack=0.04, release=0.28)

    # Short sax responses enter only after the arrangement has opened up.
    sax_scale = [293.66, 329.63, 349.23, 392.00, 440.00, 493.88, 523.25]
    sax_phrases = [
        [(0.0, 2, 1.25), (1.5, 4, 0.7), (2.5, 3, 1.1)],
        [(0.0, 1, 0.7), (1.0, 3, 0.8), (2.0, 5, 1.5)],
        [(0.0, 4, 1.0), (1.25, 6, 0.65), (2.25, 4, 1.35)],
    ]
    for block in range(3, chord_count, 4):
        start = block * chord_len
        progress = start / args.duration
        if not 0.34 < progress < 0.84:
            continue
        phrase = sax_phrases[(block // 4) % len(sax_phrases)]
        sax_gain = 0.050 if progress < 0.58 else 0.066
        for beat_offset, note_idx, beats_long in phrase:
            add_sax(mix, start + beat_offset * BEAT, beats_long * BEAT, sax_scale[note_idx], sax_gain, rng)

    # Evolving soft-house groove: four-on-the-floor, brushed hats, then a gentle exit.
    total_beats = int(args.duration / BEAT)
    for beat_i in range(total_beats):
        progress = (beat_i * BEAT) / args.duration
        if not 0.12 < progress < 0.89:
            continue
        groove = min(1.0, (progress - 0.12) / 0.22) * min(1.0, (0.89 - progress) / 0.10)
        start_i = int(beat_i * BEAT * SAMPLE_RATE)
        kick_len = min(int(0.23 * SAMPLE_RATE), frames - start_i)
        if kick_len > 0:
            t = np.arange(kick_len) / SAMPLE_RATE
            phase = 2 * np.pi * (72 * t - 35 * t * t)
            kick = np.sin(phase) * np.exp(-t * 18) * (0.095 * groove)
            mix[start_i:start_i + kick_len] += kick[:, None]
        hat_start = int((beat_i + 0.5) * BEAT * SAMPLE_RATE)
        hat_len = min(int(0.11 * SAMPLE_RATE), frames - hat_start)
        if hat_len > 0:
            t = np.arange(hat_len) / SAMPLE_RATE
            noise = rng.normal(0, 1, hat_len)
            noise = np.concatenate(([0], np.diff(noise)))
            hat_gain = 0.008 + (0.006 if progress > 0.46 else 0.0)
            hat = noise * np.exp(-t * 30) * hat_gain * groove
            mix[hat_start:hat_start + hat_len, 0] += hat * 0.8
            mix[hat_start:hat_start + hat_len, 1] += hat
        if beat_i % 4 in (1, 3) and progress > 0.28:
            clap_len = min(int(0.10 * SAMPLE_RATE), frames - start_i)
            t = np.arange(clap_len) / SAMPLE_RATE
            clap = rng.normal(0, 1, clap_len) * np.exp(-t * 34) * 0.012 * groove
            mix[start_i:start_i + clap_len] += clap[:, None]

    # Subtle room-like delays create width without external samples.
    for delay_s, gain, swap in [(0.19, 0.15, True), (0.37, 0.09, False)]:
        delay = int(delay_s * SAMPLE_RATE)
        source = mix[:-delay, ::-1] if swap else mix[:-delay]
        mix[delay:] += source * gain

    fade = min(int(8.0 * SAMPLE_RATE), frames // 2)
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
