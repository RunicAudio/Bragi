"""
src/dsp/sample_player.py
========================
Low-latency polyphonic sound generator synthesizing organic piano/e-piano Tones
with smooth ADSR envelopes to prevent audio clipping or harsh harmonic distortion.
"""

import threading
import numpy as np
import sounddevice as sd


class SamplePlayer:
    """Synthesizes high-fidelity piano tones with exponential decay envelopes."""

    def __init__(self, sample_rate: int = 44100) -> None:
        self.sample_rate = sample_rate

    def play_pitch_classes(self, pitch_classes: set[int], base_octave: int = 4, duration_sec: float = 1.2) -> None:
        """Asynchronously plays a chord or interval combination of pitch classes."""
        threading.Thread(
            target=self._render_and_play,
            args=(list(pitch_classes), base_octave, duration_sec),
            daemon=True,
        ).start()

    def play_note(self, note_name: str, octave: int = 4, duration_sec: float = 1.0) -> None:
        """Asynchronously plays a single note."""
        from domain.music_theory import MusicTheory
        pc = MusicTheory.note_to_pitch_class(note_name)
        self.play_pitch_classes({pc}, base_octave=octave, duration_sec=duration_sec)

    def _render_and_play(self, pitch_classes: list[int], octave: int, duration_sec: float) -> None:
        if not pitch_classes:
            return

        num_samples = int(self.sample_rate * duration_sec)
        t = np.linspace(0, duration_sec, num_samples, endpoint=False)
        mixed_signal = np.zeros(num_samples, dtype=np.float32)

        for pc in pitch_classes:
            midi_note = (octave + 1) * 12 + pc
            freq = 440.0 * (2.0 ** ((midi_note - 69) / 12.0))

            # Synthesize fundamental + warm piano overtones
            fundamental = np.sin(2 * np.pi * freq * t)
            second_harmonic = 0.3 * np.sin(2 * np.pi * (2 * freq) * t)
            third_harmonic = 0.1 * np.sin(2 * np.pi * (3 * freq) * t)

            tone = fundamental + second_harmonic + third_harmonic

            # ADSR Envelope: Rapid attack (10ms) + Exponential smooth decay
            attack = np.minimum(1.0, t / 0.01)
            decay = np.exp(-3.5 * t)
            envelope = attack * decay

            mixed_signal += tone * envelope

        # Normalize total power to prevent digital clipping / distortion
        max_val = np.max(np.abs(mixed_signal))
        if max_val > 0.001:
            mixed_signal = (mixed_signal / max_val) * 0.70

        try:
            sd.play(mixed_signal.astype(np.float32), samplerate=self.sample_rate)
            sd.wait()
        except Exception as err:
            print(f"[SamplePlayer] Audio playback error: {err}")
