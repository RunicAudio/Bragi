"""
src/domain/chord_definitions.py
===============================
Pydantic chord data models, quality definitions, and pitch class mapping.
"""
import random

from enum import Enum
from typing import List, Optional, Tuple
from pydantic import BaseModel, ConfigDict
from domain.note_spelling import spell_interval


class ChordQuality(str, Enum):
    MAJOR = "Major"
    MINOR = "Minor"
    DOM7 = "Dominant 7th"
    MAJ7 = "Major 7th"
    MIN7 = "Minor 7th"
    SUS4 = "Sus4"
    SUS2 = "Sus2"
    DIMINISHED = "Diminished"


class CAGEDPosition(str, Enum):
    C_SHAPE = "C"
    A_SHAPE = "A"
    G_SHAPE = "G"
    E_SHAPE = "E"
    D_SHAPE = "D"
    OPEN = "Open"


class FingeringCoordinate(BaseModel):
    string_num: int
    fret: int
    finger: Optional[int] = None
    is_muted: bool = False
    is_open: bool = False


class ChordVoicing(BaseModel):
    voicing_id: str
    caged_position: CAGEDPosition
    fret_range: Tuple[int, int]
    fingerings: List[FingeringCoordinate]
    bass_string: int


class ChordDefinition(BaseModel):
    name: str
    root_note: str
    quality: str
    pitch_classes: List[int]
    note_names: List[str]
    formula_intervals: Optional[List[str]] = None


class TargetChord(BaseModel):
    model_config = ConfigDict(frozen=True)

    chord_definition: ChordDefinition
    required_voicing: Optional[ChordVoicing] = None

    @property
    def display_title(self) -> str:
        return self.chord_definition.name


CHORD_INTERVAL_OFFSETS = {
    "Major": [0, 4, 7],
    "Minor": [0, 3, 7],
    "Dominant 7th": [0, 4, 7, 10],
    "Major 7th": [0, 4, 7, 11],
    "Minor 7th": [0, 3, 7, 10],
    "Sus4": [0, 5, 7],
    "Sus2": [0, 2, 7],
    "Diminished": [0, 3, 6],
}

CHORD_DIATONIC_INTERVALS = {
    "Major": [1, 3, 5],
    "Minor": [1, 3, 5],
    "Dominant 7th": [1, 3, 5, 7],
    "Major 7th": [1, 3, 5, 7],
    "Minor 7th": [1, 3, 5, 7],
    "Sus4": [1, 4, 5],
    "Sus2": [1, 2, 5],
    "Diminished": [1, 3, 5],
}

def get_chord_pitch_classes(root_note: str, quality_str: str) -> List[int]:
    """Calculates pitch class integers (0..11) for a root and chord quality."""
    from domain.music_theory import MusicTheory
    root_pc = MusicTheory.note_to_pitch_class(root_note)
    offsets = CHORD_INTERVAL_OFFSETS.get(quality_str, [0, 4, 7])
    return [(root_pc + offset) % 12 for offset in offsets]

def get_chord_note_names(
    root_note: str,
    quality_str: str,
    unicode_accidentals: bool = False,
) -> List[str]:
    """
    Return correctly spelled chord tones.

    Uses diatonic interval numbers to preserve correct note-letter
    relationships and chromatic offsets to determine accidentals.

    Examples:
        get_chord_note_names("C", "Major")
            -> ["C", "E", "G"]

        get_chord_note_names("Db", "Major")
            -> ["Db", "F", "Ab"]

        get_chord_note_names("Bb", "Minor")
            -> ["Bb", "Db", "F"]

    Raises:
        ValueError: If the root note or chord quality is unsupported.
    """
    if quality_str not in CHORD_INTERVAL_OFFSETS:
        raise ValueError(f"Unsupported chord quality: {quality_str}")

    offsets = CHORD_INTERVAL_OFFSETS[quality_str]
    interval_numbers = CHORD_DIATONIC_INTERVALS[quality_str]

    if len(offsets) != len(interval_numbers):
        raise ValueError(
            f"Inconsistent interval definitions for {quality_str}"
        )

    return [
        spell_interval(
            root_note=root_note,
            interval_number=interval_number,
            semitones=semitones,
            unicode_accidentals=unicode_accidentals,
        )
        for interval_number, semitones in zip(
            interval_numbers,
            offsets,
        )
    ]

def get_available_chord_names() -> List[str]:
    """Return every supported root and chord-quality combination."""
    from domain.music_theory import CHROMATIC_SHARPS

    return [
        f"{root} {quality}"
        for root in CHROMATIC_SHARPS
        for quality in CHORD_INTERVAL_OFFSETS
    ]


def select_random_chord(previous_chord: Optional[str] = None) -> str:
    """Select a random supported chord without immediately repeating."""
    available = get_available_chord_names()

    if previous_chord in available and len(available) > 1:
        available.remove(previous_chord)

    return random.choice(available)
