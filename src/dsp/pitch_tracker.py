"""
src/dsp/pitch_tracker.py
========================
High-accuracy real-time fundamental frequency (F0) tracking using autocorrelation,
peak detection, and quadratic/parabolic sub-sample lag interpolation.
"""

import numpy as np
from core.app_state import LivePitch
from domain.music_theory import CHROMATIC_SHARPS, MusicTheory

# Acoustic Reference Constants required by Chromagram analyzer
A440_HZ = 440.0
NOTE_NAMES_12 = CHROMATIC_SHARPS


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
        rms = float(np.sqrt(np.mean(signal**2)))

        # Lowered noise threshold to detect mic input
        if rms < 0.0005:
            return LivePitch(is_silent=True, rms_level=rms)

        n = len(signal)
        if n < self.max_period + 10:
            return LivePitch(is_silent=True, rms_level=rms)

        r = np.correlate(signal, signal, mode="full")[n - 1 :]
        if r[0] == 0:
            return LivePitch(is_silent=True, rms_level=rms)

        r_norm = r / r[0]

        search_region = r_norm[self.min_period : self.max_period]
        if len(search_region) == 0:
            return LivePitch(is_silent=True, rms_level=rms)

        peak_idx_rel = int(np.argmax(search_region))
        peak_idx = peak_idx_rel + self.min_period
        peak_val = search_region[peak_idx_rel]

        if peak_val < 0.25:
            return LivePitch(is_silent=True, rms_level=rms)

        # Quadratic / Parabolic Interpolation around peak
        if 0 < peak_idx_rel < len(search_region) - 1:
            alpha = float(search_region[peak_idx_rel - 1])
            beta = float(search_region[peak_idx_rel])
            gamma = float(search_region[peak_idx_rel + 1])

            denom = 2.0 * (2.0 * beta - alpha - gamma)
            if abs(denom) > 1e-6:
                delta = (gamma - alpha) / denom
            else:
                delta = 0.0
            refined_lag = float(peak_idx) + delta
        else:
            refined_lag = float(peak_idx)

        if refined_lag <= 0:
            return LivePitch(is_silent=True, rms_level=rms)

        freq = float(self.sample_rate) / refined_lag
        note_name, pitch_class, cents = MusicTheory.frequency_to_note_info(freq)
        is_in_tune = abs(cents) <= 10.0

        return LivePitch(
            frequency=float(freq),
            note_name=note_name,
            pitch_class=pitch_class,
            cents_deviation=float(cents),
            is_in_tune=is_in_tune,
            is_silent=False,
            rms_level=rms,
        )
