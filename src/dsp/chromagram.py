"""
src/dsp/chromagram.py
=====================
12-bin pitch class profile analyzer featuring harmonic overtone suppression
and multi-frame energy integration for polyphonic chord detection.
"""

from collections import deque
from typing import Set, Tuple
import numpy as np

from dsp.pitch_tracker import A440_HZ, NOTE_NAMES_12


class ChromagramAnalyzer:
    """Computes normalized 12-bin pitch class energy vectors from PCM frames."""

    def __init__(
        self,
        sample_rate: int = 44100,
        chroma_threshold: float = 0.22,
        integration_frames: int = 6,
        max_active_pcs: int = 5,
    ) -> None:
        self.sample_rate = sample_rate
        self.chroma_threshold = chroma_threshold
        self.max_active_pcs = max_active_pcs
        self._history = deque(maxlen=integration_frames)

    def process_frame(self, signal: np.ndarray) -> Tuple[Set[int], np.ndarray]:
        """
        Extracts active pitch classes (0..11) and 12-bin normalized energy vector.
        """
        if signal is None or signal.size < 1024:
            return set(), np.zeros(12, dtype=np.float32)

        # Apply Hann windowing to minimize spectral leakage
        windowed = signal * np.hanning(signal.size)
        fft_mags = np.abs(np.fft.rfft(windowed))
        fft_freqs = np.fft.rfftfreq(signal.size, d=1.0 / self.sample_rate)

        chroma = np.zeros(12, dtype=np.float32)

        for freq, mag in zip(fft_freqs, fft_mags):
            if 65.0 <= freq <= 1200.0:
                midi_exact = 69.0 + 12.0 * np.log2(max(freq, 1.0) / A440_HZ)
                pc = int(round(midi_exact)) % 12
                chroma[pc] += mag

        # Multi-frame strum integration
        self._history.append(chroma)
        integrated = np.max(np.array(self._history), axis=0)

        max_energy = np.max(integrated)
        if max_energy > 1e-5:
            integrated /= max_energy
        else:
            return set(), integrated

        # Overtone Suppression: Attenuate artificial 3rd (+7 semitones) and 5th (+4 semitones) harmonics
        filtered = integrated.copy()
        for pc in range(12):
            if integrated[pc] > 0.60:
                filtered[(pc + 7) % 12] = max(0.0, filtered[(pc + 7) % 12] - 0.35 * integrated[pc])
                filtered[(pc + 4) % 12] = max(0.0, filtered[(pc + 4) % 12] - 0.20 * integrated[pc])

        candidates = [(pc, filtered[pc]) for pc in range(12) if filtered[pc] >= self.chroma_threshold]
        candidates.sort(key=lambda item: item[1], reverse=True)
        active_pcs = {pc for pc, _ in candidates[: self.max_active_pcs]}

        return active_pcs, filtered

    def clear(self) -> None:
        """Clears the multi-frame history accumulator."""
        self._history.clear()
