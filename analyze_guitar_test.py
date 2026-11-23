import wave
from pathlib import Path

import numpy as np

from dsp.pitch_tracker import PitchTracker

FILE = Path("tests/fixtures/real_guitar/low_e2.wav")

with wave.open(str(FILE), "rb") as wav:
    sample_rate = wav.getframerate()
    channels = wav.getnchannels()
    frames = wav.getnframes()
    audio = wav.readframes(frames)

audio = np.frombuffer(audio, dtype="<i2")
audio = audio.astype(np.float32) / 32768.0
audio = audio.reshape(-1, channels)
audio = np.mean(audio, axis=1)

tracker = PitchTracker(sample_rate=sample_rate)

frame_size = 4096
hop_size = 1024

detections = []

for start in range(0, len(audio) - frame_size, hop_size):
    frame = audio[start:start + frame_size]

    result = tracker.process_frame(frame)

    if not result.is_silent:
        detections.append((
            start / sample_rate,
            result.frequency
        ))

print("REAL GUITAR PITCH ANALYSIS")
print("=" * 45)

if not detections:
    print("No valid detections.")
    raise SystemExit

values = np.array([frequency for _, frequency in detections])

print(f"Total detections: {len(detections)}")
print(f"Overall median: {np.median(values):.2f} Hz")
print()

print("DETECTIONS BY SECOND")
print("-" * 45)

for second in range(5):
    section = [
        frequency
        for timestamp, frequency in detections
        if second <= timestamp < second + 1
    ]

    if section:
        section = np.array(section)

        print(
            f"{second}-{second + 1}s: "
            f"Median={np.median(section):.2f} Hz | "
            f"Min={np.min(section):.2f} Hz | "
            f"Max={np.max(section):.2f} Hz | "
            f"Frames={len(section)}"
        )

print()
print("FREQUENCY DISTRIBUTION")
print("-" * 45)

for low, high in [
    (75, 90),
    (150, 180),
    (230, 270),
    (300, 360),
    (450, 550),
    (550, 600),
]:
    count = np.sum((values >= low) & (values <= high))
    print(f"{low}-{high} Hz: {count} frames")
