"""
src/dsp/pitch_tracker.py
========================
High-accuracy real-time fundamental frequency (F0) tracking using autocorrelation and peak detection.
"""

import numpy as np
from core.app_state import LivePitch
from domain.music_theory import MusicTheory


class PitchTracker:
    """Monophonic pitch tracker calculating real-time frequency and cents offset."""

    def __init__(
        self,
        sample_rate: int = 44100,
        min_freq: float = 65.0,   # C2 (~65.4 Hz)
        max_freq: float = 1050.0, # C6 (~1046.5 Hz)
    ) -> None:
        self.sample_rate = sample_rate
        self.min_period = int(sample_rate / max_freq)
        self.max_period = int(sample_rate / min_freq)

    def process_frame(self, signal: np.ndarray) -> LivePitch:
        """Processes a PCM audio buffer frame and computes pitch parameters."""
        rms = np.sqrt(np.mean(signal**2))
        if rms < 0.01:
            return LivePitch(is_silent=True)

        n = len(signal)
        if n < self.max_period * 2:
            return LivePitch(is_silent=True)

        r = np.correlate(signal, signal, mode="full")[n - 1 :]
        if r[0] == 0:
            return LivePitch(is_silent=True)

        r_norm = r / r[0]

        search_region = r_norm[self.min_period : self.max_period]
        if len(search_region) == 0:
            return LivePitch(is_silent=True)

        peak_idx = np.argmax(search_region) + self.min_period
        peak_val = r_norm[peak_idx]

        if peak_val < 0.4:
            return LivePitch(is_silent=True)

        freq = self.sample_rate / peak_idx
        note_name, pitch_class, cents = MusicTheory.frequency_to_note_info(freq)
        is_in_tune = abs(cents) <= 10.0

        return LivePitch(
            frequency=float(freq),
            note_name=note_name,
            pitch_class=pitch_class,
            cents_deviation=float(cents),
            is_in_tune=is_in_tune,
            is_silent=False,
        )
