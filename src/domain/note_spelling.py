"""
src/domain/note_spelling.py
===========================
Context-aware musical note spelling.

Separates written note names from numeric pitch classes. This module
spells intervals using both their diatonic interval number and their
chromatic semitone distance.

Examples:
    C + major third (3, 4) -> E
    D♭ + major third (3, 4) -> F
    F♯ + major third (3, 4) -> A♯
    G♯ + major seventh (7, 11) -> F𝄪
"""

from dataclasses import dataclass


LETTER_ORDER = ("C", "D", "E", "F", "G", "A", "B")

NATURAL_PITCH_CLASSES = {
    "C": 0,
    "D": 2,
    "E": 4,
    "F": 5,
    "G": 7,
    "A": 9,
    "B": 11,
}

ACCIDENTAL_OFFSETS = {
    "": 0,
    "#": 1,
    "##": 2,
    "b": -1,
    "bb": -2,
    "x": 2,
    "♯": 1,
    "♯♯": 2,
    "♭": -1,
    "♭♭": -2,
    "𝄪": 2,
    "𝄫": -2,
}

ASCII_ACCIDENTALS = {
    -2: "bb",
    -1: "b",
    0: "",
    1: "#",
    2: "##",
}

UNICODE_ACCIDENTALS = {
    -2: "𝄫",
    -1: "♭",
    0: "",
    1: "♯",
    2: "𝄪",
}


@dataclass(frozen=True)
class SpelledNote:
    """A written note represented by its letter and accidental."""

    letter: str
    accidental: int = 0

    def __post_init__(self):
        if self.letter not in LETTER_ORDER:
            raise ValueError(f"Invalid note letter: {self.letter}")

        if not isinstance(self.accidental, int):
            raise TypeError("Accidental must be an integer.")

    @property
    def pitch_class(self) -> int:
        """Return the note's numeric pitch class (0-11)."""
        return (
            NATURAL_PITCH_CLASSES[self.letter] + self.accidental
        ) % 12

    def format(self, unicode_accidentals: bool = False) -> str:
        """Return the written note name."""
        accidental_map = (
            UNICODE_ACCIDENTALS
            if unicode_accidentals
            else ASCII_ACCIDENTALS
        )

        if self.accidental not in accidental_map:
            raise ValueError(
                f"Cannot format accidental of {self.accidental} semitones."
            )

        return self.letter + accidental_map[self.accidental]


def parse_note(note_name: str) -> SpelledNote:
    """
    Parse a note name into its letter and accidental.

    Supported examples:
        C, F#, Bb, C##, Ebb, Fx, Db, F♯, B♭, G𝄪

    Accidentals beyond double sharps or flats are rejected.
    """
    if not isinstance(note_name, str):
        raise TypeError("Note name must be a string.")

    clean_note = note_name.strip()

    if not clean_note:
        raise ValueError("Note name cannot be empty.")

    letter = clean_note[0].upper()

    if letter not in LETTER_ORDER:
        raise ValueError(f"Invalid note letter: {letter}")

    accidental_text = clean_note[1:]

    if accidental_text not in ACCIDENTAL_OFFSETS:
        raise ValueError(
            f"Unsupported accidental or note spelling: {note_name}"
        )

    return SpelledNote(
        letter=letter,
        accidental=ACCIDENTAL_OFFSETS[accidental_text],
    )


def spell_interval(
    root_note: str,
    interval_number: int,
    semitones: int,
    unicode_accidentals: bool = False,
) -> str:
    """
    Spell an interval above a root note.

    Args:
        root_note: Written root note, such as C, Db, or F#.
        interval_number: Diatonic interval number (1 = unison,
                         2 = second, 3 = third, etc.).
        semitones: Chromatic distance above the root.
        unicode_accidentals: Use ♯, ♭, 𝄪, and 𝄫 when True.

    Returns:
        Correctly spelled written note name.

    Examples:
        spell_interval("C", 3, 4) -> "E"
        spell_interval("Db", 3, 4) -> "F"
        spell_interval("F#", 3, 4) -> "A#"
        spell_interval("G#", 7, 11) -> "F##"
    """
    if not isinstance(interval_number, int) or isinstance(interval_number, bool):
        raise TypeError("Interval number must be an integer.")

    if interval_number < 1:
        raise ValueError("Interval number must be at least 1.")

    if not isinstance(semitones, int) or isinstance(semitones, bool):
        raise TypeError("Semitone distance must be an integer.")

    root = parse_note(root_note)

    root_letter_index = LETTER_ORDER.index(root.letter)

    diatonic_steps = interval_number - 1
    target_letter_index = (
        root_letter_index + diatonic_steps
    ) % len(LETTER_ORDER)

    octave_displacement = (
        root_letter_index + diatonic_steps
    ) // len(LETTER_ORDER)

    target_letter = LETTER_ORDER[target_letter_index]

    natural_interval_semitones = (
        octave_displacement * 12
        + NATURAL_PITCH_CLASSES[target_letter]
        - NATURAL_PITCH_CLASSES[root.letter]
    )

    target_accidental = (
        root.accidental
        + semitones
        - natural_interval_semitones
    )

    target = SpelledNote(
        letter=target_letter,
        accidental=target_accidental,
    )

    return target.format(
        unicode_accidentals=unicode_accidentals
    )


def spell_note_from_pitch_class(
    root_note: str,
    interval_number: int,
    target_pitch_class: int,
    unicode_accidentals: bool = False,
) -> str:
    """
    Spell a target pitch class as a diatonic interval above a root.

    The interval number determines the letter name. The pitch class
    determines the accidental needed to reach the correct sound.
    """
    if not isinstance(target_pitch_class, int) or isinstance(target_pitch_class, bool):
        raise TypeError("Pitch class must be an integer.")

    if not 0 <= target_pitch_class <= 11:
        raise ValueError("Pitch class must be between 0 and 11.")

    root = parse_note(root_note)

    semitones = (
        target_pitch_class - root.pitch_class
    ) % 12

    return spell_interval(
        root_note=root_note,
        interval_number=interval_number,
        semitones=semitones,
        unicode_accidentals=unicode_accidentals,
    )
