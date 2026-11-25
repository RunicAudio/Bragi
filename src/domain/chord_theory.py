"""
src/domain/chord_theory.py
==========================
Root-relative chord construction and theory explanations.

This module is independent of the UI and audio-processing systems.
It separates chord formula degrees, intervals, and reference-scale
degrees so that each concept is represented accurately.
"""

from dataclasses import dataclass
from typing import List, Optional

from domain.chord_definitions import (
    CHORD_DIATONIC_INTERVALS,
    CHORD_INTERVAL_OFFSETS,
    get_chord_note_names,
)
from domain.note_spelling import parse_note


INTERVAL_NAMES = {
    (1, 0): "Perfect unison",
    (2, 2): "Major second",
    (3, 3): "Minor third",
    (3, 4): "Major third",
    (4, 5): "Perfect fourth",
    (5, 6): "Diminished fifth",
    (5, 7): "Perfect fifth",
    (7, 9): "Major sixth",
    (7, 10): "Minor seventh",
    (7, 11): "Major seventh",
}

SCALE_DEGREE_NAMES = {
    "1": "Tonic",
    "2": "Supertonic",
    "3": "Mediant",
    "4": "Subdominant",
    "5": "Dominant",
    "6": "Submediant",
    "b7": "Subtonic",
    "7": "Leading tone",
}

CHORD_FORMULAS = {
    "Major": ["1", "3", "5"],
    "Minor": ["1", "b3", "5"],
    "Dominant 7th": ["1", "3", "5", "b7"],
    "Major 7th": ["1", "3", "5", "7"],
    "Minor 7th": ["1", "b3", "5", "b7"],
    "Sus4": ["1", "4", "5"],
    "Sus2": ["1", "2", "5"],
    "Diminished": ["1", "b3", "b5"],
}

# Reference-scale degrees are deliberately independent of chord formulas.
# For example, b3 in a minor chord is degree 3 in its natural minor scale.
REFERENCE_SCALE_DEGREES = {
    "Major": ["1", "3", "5"],
    "Minor": ["1", "3", "5"],
    "Dominant 7th": ["1", "3", "5", "b7"],
    "Major 7th": ["1", "3", "5", "7"],
    "Minor 7th": ["1", "3", "5", "b7"],
}

REFERENCE_CONTEXTS = {
    "Major": "major",
    "Major 7th": "major",
    "Minor": "natural minor",
    "Minor 7th": "natural minor",
    "Dominant 7th": "Mixolydian",
}


@dataclass(frozen=True)
class ChordTone:
    """The theoretical properties of one chord tone."""

    note_name: str
    formula_degree: str
    interval_name: str
    semitones_from_root: int
    scale_degree: Optional[str]
    scale_degree_name: Optional[str]


@dataclass(frozen=True)
class ChordExplanation:
    """Complete root-relative explanation of a chord."""

    chord_name: str
    root_note: str
    quality: str
    reference_context: str
    formula: List[str]
    tones: List[ChordTone]
    construction_explanation: str
    hints: List[str]


def _get_interval_name(
    interval_number: int,
    semitones: int,
) -> str:
    """Return the correct interval name for a chord tone."""

    interval_name = INTERVAL_NAMES.get(
        (interval_number, semitones)
    )

    if interval_name is None:
        raise ValueError(
            f"Unsupported interval: {interval_number}, {semitones}"
        )

    return interval_name


def _get_reference_context(root: str, quality: str) -> str:
    """Return the root-relative reference context."""

    context = REFERENCE_CONTEXTS.get(quality)

    if context is None:
        return f"{root}-rooted interval structure"

    return f"{root} {context}"


def explain_chord(
    root_note: str,
    quality: str,
) -> ChordExplanation:
    """
    Construct a complete root-relative chord explanation.

    Args:
        root_note: Written chord root, such as A, Bb, or F#.
        quality: One of the supported chord qualities.

    Returns:
        A complete ChordExplanation.

    Raises:
        ValueError: If the chord quality or root is unsupported.
    """

    if quality not in CHORD_INTERVAL_OFFSETS:
        raise ValueError(f"Unsupported chord quality: {quality}")

    # Validate the root spelling.
    parse_note(root_note)

    offsets = CHORD_INTERVAL_OFFSETS[quality]
    interval_numbers = CHORD_DIATONIC_INTERVALS[quality]
    formula = CHORD_FORMULAS[quality]
    scale_degrees = REFERENCE_SCALE_DEGREES.get(quality)

    if not (
        len(offsets)
        == len(interval_numbers)
        == len(formula)
    ):
        raise ValueError(
            f"Inconsistent theory definitions for {quality}"
        )

    if scale_degrees is not None and len(scale_degrees) != len(formula):
        raise ValueError(
            f"Inconsistent reference-scale definitions for {quality}"
        )

    note_names = get_chord_note_names(root_note, quality)

    tones = []

    for index, (note_name, interval_number, semitones, degree) in enumerate(
        zip(note_names, interval_numbers, offsets, formula)
    ):
        scale_degree = (
            scale_degrees[index]
            if scale_degrees is not None
            else None
        )

        scale_degree_name = (
            SCALE_DEGREE_NAMES[scale_degree]
            if scale_degree is not None
            else None
        )

        tones.append(
            ChordTone(
                note_name=note_name,
                formula_degree=degree,
                interval_name=_get_interval_name(
                    interval_number,
                    semitones,
                ),
                semitones_from_root=semitones,
                scale_degree=scale_degree,
                scale_degree_name=scale_degree_name,
            )
        )

    chord_name = f"{root_note} {quality}"

    construction_explanation = (
        f"{chord_name} is constructed from {len(tones)} chord tones "
        f"relative to {root_note}. "
        f"Its formula is {' - '.join(formula)}."
    )

    hints = [
        f"Start with the root note: {root_note}.",
        (
            f"This is a {quality} chord. Consider which intervals "
            "distinguish this chord quality."
        ),
        (
            f"The chord formula is {' - '.join(formula)}. "
            "Use those intervals to derive the remaining notes."
        ),
    ]

    return ChordExplanation(
        chord_name=chord_name,
        root_note=root_note,
        quality=quality,
        reference_context=_get_reference_context(
            root_note,
            quality,
        ),
        formula=formula,
        tones=tones,
        construction_explanation=construction_explanation,
        hints=hints,
    )
