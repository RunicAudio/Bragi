import numpy as np
import pytest

from dsp.pitch_tracker import PitchTracker


@pytest.mark.parametrize("frequency", [
    82.41,   # E2 - low E string
    110.00,  # A2
    146.83,  # D3
    196.00,  # G3
    246.94,  # B3
    329.63,  # E4 - high E string
    440.00,  # A4
    659.25,  # E5
])
def test_pitch_detection_accuracy(frequency):
    sample_rate = 48000
    duration = 4096 / sample_rate

    time = np.arange(4096) / sample_rate
    signal = 0.5 * np.sin(2 * np.pi * frequency * time)

    tracker = PitchTracker(sample_rate=sample_rate)
    result = tracker.process_frame(signal.astype(np.float32))

    assert not result.is_silent
    assert result.frequency == pytest.approx(frequency, rel=0.03)


def test_silence_is_detected():
    tracker = PitchTracker(sample_rate=48000)
    signal = np.zeros(4096, dtype=np.float32)

    result = tracker.process_frame(signal)

    assert result.is_silent


def test_low_volume_signal_is_detected_as_silent():
    tracker = PitchTracker(sample_rate=48000)
    time = np.arange(4096) / 48000
    signal = 0.0001 * np.sin(2 * np.pi * 440 * time)

    result = tracker.process_frame(signal.astype(np.float32))

    assert result.is_silent


def test_sample_rate_can_be_changed():
    tracker = PitchTracker(sample_rate=44100)

    tracker.set_sample_rate(48000)

    assert tracker.sample_rate == 48000

def test_harmonic_rich_signal_detects_fundamental():
    sample_rate = 48000
    frequency = 110.0
    n = 4096

    time = np.arange(n) / sample_rate

    signal = (
        0.5 * np.sin(2 * np.pi * frequency * time)
        + 0.25 * np.sin(2 * np.pi * frequency * 2 * time)
        + 0.12 * np.sin(2 * np.pi * frequency * 3 * time)
        + 0.06 * np.sin(2 * np.pi * frequency * 4 * time)
    )

    tracker = PitchTracker(sample_rate=sample_rate)
    result = tracker.process_frame(signal.astype(np.float32))

    assert not result.is_silent
    assert result.frequency == pytest.approx(frequency, rel=0.03)

def test_noisy_harmonic_signal_detects_fundamental():
    sample_rate = 48000
    frequency = 110.0
    n = 4096

    time = np.arange(n) / sample_rate

    signal = (
        0.5 * np.sin(2 * np.pi * frequency * time)
        + 0.25 * np.sin(2 * np.pi * frequency * 2 * time)
        + 0.12 * np.sin(2 * np.pi * frequency * 3 * time)
        + 0.06 * np.sin(2 * np.pi * frequency * 4 * time)
    )

    rng = np.random.default_rng(42)
    noise = rng.normal(0, 0.03, n)

    noisy_signal = signal + noise

    tracker = PitchTracker(sample_rate=sample_rate)
    result = tracker.process_frame(noisy_signal.astype(np.float32))

    assert not result.is_silent
    assert result.frequency == pytest.approx(frequency, rel=0.03)

@pytest.mark.parametrize("amplitude", [
    0.05,
    0.10,
    0.25,
    0.50,
    0.90,
])
def test_pitch_detection_across_amplitudes(amplitude):
    sample_rate = 48000
    frequency = 220.0
    n = 4096

    time = np.arange(n) / sample_rate
    signal = amplitude * np.sin(2 * np.pi * frequency * time)

    tracker = PitchTracker(sample_rate=sample_rate)
    result = tracker.process_frame(signal.astype(np.float32))

    assert not result.is_silent
    assert result.frequency == pytest.approx(frequency, rel=0.03)

def test_tracks_consecutive_frequency_changes():
    sample_rate = 48000
    n = 4096

    frequencies = [
        110.0,
        220.0,
        329.63,
        146.83,
        110.0,
    ]

    tracker = PitchTracker(sample_rate=sample_rate)

    for frequency in frequencies:
        time = np.arange(n) / sample_rate
        signal = 0.5 * np.sin(2 * np.pi * frequency * time)

        result = tracker.process_frame(signal.astype(np.float32))

        assert not result.is_silent
        assert result.frequency == pytest.approx(frequency, rel=0.03)

@pytest.mark.parametrize("frequency", [
    66.0,
    70.0,
    80.0,
    1000.0,
    1050.0,
])
def test_pitch_detection_near_frequency_boundaries(frequency):
    sample_rate = 48000
    n = 4096

    time = np.arange(n) / sample_rate
    signal = 0.5 * np.sin(2 * np.pi * frequency * time)

    tracker = PitchTracker(sample_rate=sample_rate)
    result = tracker.process_frame(signal.astype(np.float32))

    assert not result.is_silent
    assert result.frequency == pytest.approx(frequency, rel=0.03)

@pytest.mark.parametrize("frequency", [
    82.41,   # Low E2
    110.00,  # A2
    146.83,  # D3
    196.00,  # G3
    246.94,  # B3
    329.63,  # High E4
])
def test_standard_guitar_open_strings(frequency):
    sample_rate = 48000
    n = 4096

    time = np.arange(n) / sample_rate
    signal = 0.5 * np.sin(2 * np.pi * frequency * time)

    tracker = PitchTracker(sample_rate=sample_rate)
    result = tracker.process_frame(signal.astype(np.float32))

    assert not result.is_silent
    assert result.frequency == pytest.approx(frequency, rel=0.03)
