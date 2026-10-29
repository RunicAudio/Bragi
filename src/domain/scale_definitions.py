"""
src/domain/scale_definitions.py
===============================
Scale degree formulas, direction patterns, and step-by-step practice sequencers.
"""

from enum import Enum
import random
from typing import Dict, List, Optional, Set


class ScaleType(str, Enum):
    MAJOR = "Major"
    NATURAL_MINOR = "Natural Minor"
    MAJOR_PENTATONIC = "Major Pentatonic"
    MINOR_PENTATONIC = "Minor Pentatonic"


class SequenceDirection(str, Enum):
    ASCENDING = "ASCENDING"
    DESCENDING = "DESCENDING"
    ASCENDING_DESCENDING = "ASCENDING_DESCENDING"
    THIRD_LEAPS = "THIRD_LEAPS"
    RANDOM = "RANDOM"


SCALE_FORMULAS: Dict[ScaleType, List[int]] = {
    ScaleType.MAJOR: [0, 2, 4, 5, 7, 9, 11],
    ScaleType.NATURAL_MINOR: [0, 2, 3, 5, 7, 8, 10],
    ScaleType.MAJOR_PENTATONIC: [0, 2, 4, 7, 9],
    ScaleType.MINOR_PENTATONIC: [0, 3, 5, 7, 10],
}


class ScaleDefinition:
    """Represents a specific key and scale combination."""

    def __init__(self, root_note: str, scale_type: ScaleType):
        from domain.music_theory import MusicTheory
        self.root_note = root_note.strip().upper()
        self.scale_type = scale_type
        self.root_pitch_class = MusicTheory.note_to_pitch_class(self.root_note)

        offsets = SCALE_FORMULAS.get(scale_type, [0, 2, 4, 5, 7, 9, 11])
        self.pitch_classes: Set[int] = {(self.root_pitch_class + offset) % 12 for offset in offsets}
        self.ordered_pitch_classes: List[int] = [(self.root_pitch_class + offset) % 12 for offset in offsets]


class ScaleSequencer:
    """Generates practice patterns and advances step-by-step during scale drills."""

    def __init__(
        self,
        scale_notes: Optional[List[str]] = None,
        direction: SequenceDirection = SequenceDirection.ASCENDING,
    ):
        self.scale_notes: List[str] = scale_notes or []
        self.direction: SequenceDirection = direction
        self.sequence: List[str] = []
        self.current_index: int = 0

        if self.scale_notes:
            self.generate_sequence(self.scale_notes, self.direction)

    def generate_sequence(self, scale_notes: List[str], direction: Optional[SequenceDirection] = None) -> List[str]:
        """Generates an ordered list of target note strings matching direction."""
        self.scale_notes = scale_notes
        if direction is not None:
            self.direction = direction

        if not self.scale_notes:
            self.sequence = []
            self.current_index = 0
            return self.sequence

        notes = list(self.scale_notes)

        if self.direction == SequenceDirection.ASCENDING:
            self.sequence = notes
        elif self.direction == SequenceDirection.DESCENDING:
            self.sequence = list(reversed(notes))
        elif self.direction == SequenceDirection.ASCENDING_DESCENDING:
            self.sequence = notes + list(reversed(notes[:-1]))
        elif self.direction == SequenceDirection.THIRD_LEAPS:
            seq = []
            n = len(notes)
            for i in range(n):
                seq.append(notes[i])
                seq.append(notes[(i + 2) % n])
            self.sequence = seq
        elif self.direction == SequenceDirection.RANDOM:
            shuffled = list(notes)
            random.shuffle(shuffled)
            self.sequence = shuffled
        else:
            self.sequence = notes

        self.current_index = 0
        return self.sequence

    def advance(self) -> Optional[str]:
        """Advances to the next target step in sequence."""
        if not self.sequence:
            return None
        self.current_index = (self.current_index + 1) % len(self.sequence)
        return self.sequence[self.current_index]
