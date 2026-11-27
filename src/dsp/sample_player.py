"""
src/dsp/sample_player.py
========================
Thread-safe piano synthesizer supporting exact MIDI notes, melodic intervals,
harmonic intervals, chord voicings, and note sequences.

Playback is asynchronous and serialized through a background worker to
prevent overlapping sounddevice playback streams.
"""

import queue
import threading

import numpy as np
import sounddevice as sd

from domain.music_theory import (
    MusicTheory,
    PIANO_MIN_MIDI,
    PIANO_MAX_MIDI,
)


class SamplePlayer:
    """Synthesizes piano tones and manages serialized audio playback."""

    _audio_lock = threading.Lock()

    def __init__(self, sample_rate: int = 44100) -> None:
        if not isinstance(sample_rate, int) or isinstance(sample_rate, bool):
            raise ValueError("Sample rate must be an integer.")

        if sample_rate <= 0:
            raise ValueError("Sample rate must be positive.")

        self.sample_rate = sample_rate
        self._playback_queue: queue.Queue[np.ndarray] = queue.Queue()

        self._worker = threading.Thread(
            target=self._playback_worker,
            daemon=True,
            name="BragiSamplePlayer",
        )
        self._worker.start()

    # ------------------------------------------------------------------
    # Public playback API
    # ------------------------------------------------------------------

    def play_midi_note(
        self,
        midi_number: int,
        duration_sec: float = 1.0,
        level: float = 0.70,
    ) -> None:
        """Asynchronously plays one exact MIDI note."""
        self._validate_midi_notes([midi_number])
        self._validate_playback_settings(duration_sec, level)

        audio = self._render_midi_notes(
            [midi_number],
            duration_sec,
            level,
        )
        self._enqueue(audio)

    def play_midi_notes(
        self,
        midi_numbers: list[int],
        duration_sec: float = 1.2,
        level: float = 0.70,
    ) -> None:
        """Asynchronously plays multiple MIDI notes simultaneously."""
        notes = list(midi_numbers)

        if not notes:
            return

        self._validate_midi_notes(notes)
        self._validate_playback_settings(duration_sec, level)

        audio = self._render_midi_notes(
            notes,
            duration_sec,
            level,
        )
        self._enqueue(audio)

    def play_melodic_interval(
        self,
        first_note: int,
        second_note: int,
        duration_sec: float = 0.65,
        gap_sec: float = 0.20,
        level: float = 0.70,
    ) -> None:
        """Asynchronously plays two MIDI notes sequentially."""
        self.play_midi_sequence(
            [first_note, second_note],
            note_duration_sec=duration_sec,
            gap_sec=gap_sec,
            level=level,
        )

    def play_midi_sequence(
        self,
        midi_numbers: list[int],
        note_duration_sec: float = 0.65,
        gap_sec: float = 0.15,
        level: float = 0.70,
    ) -> None:
        """Asynchronously plays a sequence of individual MIDI notes."""
        notes = list(midi_numbers)

        if not notes:
            return

        self._validate_midi_notes(notes)
        self._validate_playback_settings(note_duration_sec, level)

        if (
            not isinstance(gap_sec, (int, float))
            or isinstance(gap_sec, bool)
            or not np.isfinite(gap_sec)
            or gap_sec < 0
        ):
            raise ValueError("Gap duration must be a finite non-negative number.")

        audio = self._render_midi_sequence(
            notes,
            note_duration_sec,
            gap_sec,
            level,
        )
        self._enqueue(audio)

    # ------------------------------------------------------------------
    # Backward-compatible API
    # ------------------------------------------------------------------

    def play_pitch_classes(
        self,
        pitch_classes: set[int],
        base_octave: int = 4,
        duration_sec: float = 1.2,
    ) -> None:
        """Preserves the original pitch-class chord playback interface."""
        if not pitch_classes:
            return

        if not isinstance(base_octave, int) or isinstance(base_octave, bool):
            raise ValueError("Base octave must be an integer.")

        midi_numbers = [
            (base_octave + 1) * 12 + pc
            for pc in pitch_classes
        ]

        self.play_midi_notes(
            midi_numbers,
            duration_sec=duration_sec,
        )

    def play_note(
        self,
        note_name: str,
        octave: int = 4,
        duration_sec: float = 1.0,
    ) -> None:
        """Preserves the original note-name playback interface."""
        pc = MusicTheory.note_to_pitch_class(note_name)

        if pc >= 0:
            midi_number = (octave + 1) * 12 + pc

            self.play_midi_note(
                midi_number,
                duration_sec=duration_sec,
            )

    # ------------------------------------------------------------------
    # MIDI validation
    # ------------------------------------------------------------------

    @staticmethod
    def _validate_midi_notes(midi_numbers: list[int]) -> None:
        for midi_number in midi_numbers:
            if (
                not isinstance(midi_number, int)
                or isinstance(midi_number, bool)
            ):
                raise ValueError("MIDI notes must be integers.")

            if not PIANO_MIN_MIDI <= midi_number <= PIANO_MAX_MIDI:
                raise ValueError(
                    f"MIDI note must be between "
                    f"{PIANO_MIN_MIDI} and {PIANO_MAX_MIDI}."
                )

    @staticmethod
    def _validate_playback_settings(
        duration_sec: float,
        level: float,
    ) -> None:
        if (
            not isinstance(duration_sec, (int, float))
            or isinstance(duration_sec, bool)
            or not np.isfinite(duration_sec)
            or duration_sec <= 0
        ):
            raise ValueError("Duration must be a finite positive number.")

        if (
            not isinstance(level, (int, float))
            or isinstance(level, bool)
            or not np.isfinite(level)
            or not 0 < level <= 1
        ):
            raise ValueError("Playback level must be greater than 0 and at most 1.")

    # ------------------------------------------------------------------
    # Audio rendering
    # ------------------------------------------------------------------

    def _render_midi_notes(
        self,
        midi_numbers: list[int],
        duration_sec: float,
        level: float,
    ) -> np.ndarray:
        """Renders simultaneous MIDI notes into one audio buffer."""
        num_samples = int(self.sample_rate * duration_sec)

        if num_samples <= 0:
            raise ValueError("Duration is too short for the selected sample rate.")

        t = np.arange(num_samples, dtype=np.float64) / self.sample_rate
        mixed_signal = np.zeros(num_samples, dtype=np.float64)

        for midi_number in midi_numbers:
            frequency = MusicTheory.midi_number_to_frequency(midi_number)

            fundamental = np.sin(2 * np.pi * frequency * t)
            second_harmonic = 0.3 * np.sin(2 * np.pi * 2 * frequency * t)
            third_harmonic = 0.1 * np.sin(2 * np.pi * 3 * frequency * t)

            tone = (
                fundamental
                + second_harmonic
                + third_harmonic
            )

            attack = np.minimum(1.0, t / 0.01)
            decay = np.exp(-3.5 * t)
            envelope = attack * decay

            mixed_signal += tone * envelope

        peak = np.max(np.abs(mixed_signal))

        if peak > 0.001:
            mixed_signal = (mixed_signal / peak) * level

        return mixed_signal.astype(np.float32)

    def _render_midi_sequence(
        self,
        midi_numbers: list[int],
        note_duration_sec: float,
        gap_sec: float,
        level: float,
    ) -> np.ndarray:
        """Renders individual notes separated by configurable silence."""
        note_buffers = []

        gap_samples = int(self.sample_rate * gap_sec)

        for index, midi_number in enumerate(midi_numbers):
            note_buffer = self._render_midi_notes(
                [midi_number],
                note_duration_sec,
                level,
            )
            note_buffers.append(note_buffer)

            if gap_samples > 0 and index < len(midi_numbers) - 1:
                note_buffers.append(
                    np.zeros(gap_samples, dtype=np.float32)
                )

        return np.concatenate(note_buffers)

    # ------------------------------------------------------------------
    # Serialized playback
    # ------------------------------------------------------------------

    def _enqueue(self, audio: np.ndarray) -> None:
        """Adds a rendered buffer to the playback queue."""
        if audio.size:
            self._playback_queue.put(audio)

    def _playback_worker(self) -> None:
        """Processes queued buffers sequentially."""
        while True:
            audio = self._playback_queue.get()

            try:
                with SamplePlayer._audio_lock:
                    sd.play(
                        audio,
                        samplerate=self.sample_rate,
                    )
                    sd.wait()

            except Exception as err:
                print(f"[SamplePlayer] Audio playback error: {err}")

            finally:
                self._playback_queue.task_done()
