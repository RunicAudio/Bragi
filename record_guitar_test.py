import wave
from pathlib import Path

import numpy as np
import sounddevice as sd

DEVICE = 81
SAMPLE_RATE = 48000
CHANNELS = 2
DURATION = 5

OUTPUT = Path("tests/fixtures/real_guitar/low_e2.wav")

OUTPUT.parent.mkdir(parents=True, exist_ok=True)

print("Bragi Guitar Recording Test")
print("---------------------------")
print("Input: HeadRush Core Line 1/2")
print("Sample rate: 48000 Hz")
print("Duration: 5 seconds")
print()
print("Prepare your guitar:")
print("1. Select your Strat's bridge or neck pickup.")
print("2. Tune the low E string accurately.")
print("3. Let the string ring naturally.")
print()
input("Press ENTER, then play one open low E note...")

print("Recording...")

audio = sd.rec(
    int(DURATION * SAMPLE_RATE),
    samplerate=SAMPLE_RATE,
    channels=CHANNELS,
    dtype="float32",
    device=DEVICE,
)

sd.wait()

peak = float(np.max(np.abs(audio)))
rms = float(np.sqrt(np.mean(audio ** 2)))

print()
print(f"Peak level: {peak:.4f}")
print(f"RMS level:  {rms:.4f}")

if peak >= 0.99:
    print("WARNING: Recording may be clipping.")

if peak < 0.005:
    print("WARNING: Signal is extremely quiet.")

# Convert float audio to 16-bit PCM.
pcm = (np.clip(audio, -1.0, 1.0) * 32767).astype("<i2")

with wave.open(str(OUTPUT), "wb") as wav:
    wav.setnchannels(CHANNELS)
    wav.setsampwidth(2)
    wav.setframerate(SAMPLE_RATE)
    wav.writeframes(pcm.tobytes())

print()
print(f"Recording saved: {OUTPUT}")
