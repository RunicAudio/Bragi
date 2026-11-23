"""
src/domain/music_theory.py
==========================
Fundamental music theory domain rules, chromatic mappings, frequency math, and scale/chord formulas.
"""

import math
from typing import Tuple

CHROMATIC_SHARPS = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]


class MusicTheory:
    """Static utility methods for pitch class calculation and frequency conversions."""

    A4_FREQ = 440.0
    A4_MIDI = 69

    @staticmethod
    def note_to_pitch_class(note_name: str) -> int:
        clean_note = note_name.strip().upper()
        if clean_note in CHROMATIC_SHARPS:
            return CHROMATIC_SHARPS.index(clean_note)
        return -1

    @staticmethod
    def pitch_class_to_note(pitch_class: int) -> str:
        return CHROMATIC_SHARPS[pitch_class % 12]

    @staticmethod
    def frequency_to_note_info(freq: float) -> Tuple[str, int, float]:
        if freq <= 0:
            return ("--", -1, 0.0)

        # MIDI Note Number calculation
        midi_num = 12 * math.log2(freq / MusicTheory.A4_FREQ) + MusicTheory.A4_MIDI
        nearest_midi = round(midi_num)
        pitch_class = nearest_midi % 12
        note_name = CHROMATIC_SHARPS[pitch_class]

        # Cents deviation calculation
        nearest_freq = MusicTheory.A4_FREQ * (2 ** ((nearest_midi - MusicTheory.A4_MIDI) / 12))
        cents = 1200 * math.log2(freq / nearest_freq)

        return (note_name, pitch_class, cents)
