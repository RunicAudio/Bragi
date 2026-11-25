"""
src/domain/music_theory.py
==========================
Fundamental music theory domain rules, chromatic mappings,
frequency math, and note spelling.
"""

import math
from typing import Tuple


CHROMATIC_SHARPS = [
    "C", "C#", "D", "D#", "E", "F",
    "F#", "G", "G#", "A", "A#", "B"
]

CHROMATIC_FLATS = [
    "C", "Db", "D", "Eb", "E", "F",
    "Gb", "G", "Ab", "A", "Bb", "B"
]

NATURAL_NOTE_PITCH_CLASSES = {
    "C": 0,
    "D": 2,
    "E": 4,
    "F": 5,
    "G": 7,
    "A": 9,
    "B": 11,
}


class MusicTheory:
    """Static utility methods for pitch classes and frequency conversion."""

    A4_FREQ = 440.0
    A4_MIDI = 69

    @staticmethod
    def note_to_pitch_class(note_name: str) -> int:
        """
        Convert a note name into a pitch class (0-11).

        Supports natural notes, sharps, flats, and enharmonic spellings.
        Returns -1 for invalid input.
        """

        if not isinstance(note_name, str):
            return -1

        clean_note = note_name.strip()

        if not clean_note:
            return -1

        # Normalize Unicode accidental symbols.
        clean_note = clean_note.replace("♯", "#").replace("♭", "b")

        letter = clean_note[0].upper()
        accidental = clean_note[1:]

        if letter not in NATURAL_NOTE_PITCH_CLASSES:
            return -1

        natural_pc = NATURAL_NOTE_PITCH_CLASSES[letter]

        if accidental == "":
            offset = 0
        elif accidental == "#":
            offset = 1
        elif accidental == "b":
            offset = -1
        else:
            return -1

        return (natural_pc + offset) % 12

    @staticmethod
    def pitch_class_to_note(
        pitch_class: int,
        prefer_flats: bool = False
    ) -> str:
        """
        Convert a pitch class into a note name.

        Sharp notation is the default for backward compatibility.
        Set prefer_flats=True to use flat spellings.
        """

        note_names = CHROMATIC_FLATS if prefer_flats else CHROMATIC_SHARPS

        return note_names[pitch_class % 12]

    @staticmethod
    def frequency_to_note_info(
        freq: float,
        prefer_flats: bool = False
    ) -> Tuple[str, int, float]:
        """
        Convert frequency into note name, pitch class, and cents deviation.

        Sharp notation remains the default.
        """

        if freq <= 0:
            return ("--", -1, 0.0)

        midi_num = (
            12 * math.log2(freq / MusicTheory.A4_FREQ)
            + MusicTheory.A4_MIDI
        )

        nearest_midi = round(midi_num)
        pitch_class = nearest_midi % 12

        note_name = MusicTheory.pitch_class_to_note(
            pitch_class,
            prefer_flats=prefer_flats
        )

        nearest_freq = MusicTheory.A4_FREQ * (
            2 ** ((nearest_midi - MusicTheory.A4_MIDI) / 12)
        )

        cents = 1200 * math.log2(freq / nearest_freq)

        return (note_name, pitch_class, cents)
