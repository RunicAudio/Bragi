"""
src/dsp/pitch_tracker.py
========================
Fundamental frequency (F0) tracking using autocorrelation,
peak detection, and quadratic/parabolic sub-sample lag interpolation.
"""

import numpy as np
from core.app_state import LivePitch
from domain.music_theory import CHROMATIC_SHARPS, MusicTheory

A440_HZ = 440.0
NOTE_NAMES_12 = CHROMATIC_SHARPS


class PitchTracker:
    """Monophonic pitch tracker calculating real-time frequency and cents offset."""

    def __init__(
        self,
        sample_rate: int = 44100,
        min_freq: float = 65.0,
        max_freq: float = 1050.0,
    ) -> None:
        self.min_freq = min_freq
        self.max_freq = max_freq
        self.set_sample_rate(sample_rate)

    def set_sample_rate(self, sample_rate: int) -> None:
        """Update sample rate and recalculate frequency-search boundaries."""
        if sample_rate <= 0:
            raise ValueError("Sample rate must be greater than zero.")

        self.sample_rate = int(sample_rate)
        self.min_period = int(self.sample_rate / self.max_freq)
        self.max_period = int(self.sample_rate / self.min_freq)

    def process_frame(self, signal: np.ndarray) -> LivePitch:
        """Processes a PCM audio buffer frame and computes pitch parameters."""
        rms = float(np.sqrt(np.mean(signal ** 2)))

        if rms < 0.0005:
            return LivePitch(is_silent=True, rms_level=rms)

        n = len(signal)

        if n < self.max_period + 10:
            return LivePitch(is_silent=True, rms_level=rms)

        r = np.correlate(signal, signal, mode="full")[n - 1:]
        if r[0] == 0:
            return LivePitch(is_silent=True, rms_level=rms)

        # Compensate for decreasing sample overlap at longer lags.
        lags = np.arange(n)
        r_norm = r / (n - lags)
        r_norm /= r_norm[0]

        search_region = r_norm[self.min_period:self.max_period]

        if len(search_region) < 3:
            return LivePitch(is_silent=True, rms_level=rms)

        # Find local autocorrelation maxima.
        local_peaks = np.where(
            (search_region[1:-1] >= search_region[:-2]) &
            (search_region[1:-1] > search_region[2:])
        )[0] + 1

        # Keep peaks above the confidence threshold.
        valid_peaks = local_peaks[search_region[local_peaks] >= 0.25]

        if len(valid_peaks) == 0:
            return LivePitch(is_silent=True, rms_level=rms)

        # Find the strongest autocorrelation peak.
        peak_values = search_region[valid_peaks]
        strongest_value = np.max(peak_values)

        # Treat peaks within 0.02 of the strongest peak as equivalent.
        # Select the earliest to favor the fundamental frequency.
        near_best_peaks = valid_peaks[
            peak_values >= strongest_value - 0.02
        ]

        peak_idx = int(near_best_peaks[0] + self.min_period)
        peak_val = r_norm[peak_idx]

        # Quadratic / parabolic interpolation
        peak_idx_rel = peak_idx - self.min_period

        if 0 < peak_idx_rel < len(search_region) - 1:
            y1 = search_region[peak_idx_rel - 1]
            y2 = search_region[peak_idx_rel]
            y3 = search_region[peak_idx_rel + 1]

            denominator = y1 - 2 * y2 + y3

            if denominator != 0:
                adjustment = 0.5 * (y1 - y3) / denominator
            else:
                adjustment = 0.0

            refined_lag = peak_idx + adjustment
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
