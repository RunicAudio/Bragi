"""
src/domain/ear_training_engine.py
=================================
Core data structures and curriculum definitions for Ear Training.

This module is independent of the UI and audio playback systems.
"""
import random

from dataclasses import dataclass
from enum import Enum, IntEnum
from typing import Optional, Tuple


# ---------------------------------------------------------------------------
# Curriculum
# ---------------------------------------------------------------------------

class EarTrainingLevel(IntEnum):
    FOUNDATIONS = 1
    INTERMEDIATE = 2
    ADVANCED = 3
    ACTIVE_RECALL = 4


class ExerciseType(str, Enum):
    SINGLE_NOTE = "single_note"
    MELODIC_INTERVAL = "melodic_interval"
    HARMONIC_INTERVAL = "harmonic_interval"
    CHORD_QUALITY = "chord_quality"
    NOTE_IDENTIFICATION = "note_identification"
    INTERVAL_IDENTIFICATION = "interval_identification"
    CHORD_IDENTIFICATION = "chord_identification"
    CHORD_INVERSION = "chord_inversion"
    COMPOUND_INTERVAL = "compound_interval"


# ---------------------------------------------------------------------------
# Interval definitions
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class IntervalDefinition:
    """
    Defines an interval independently of its starting pitch.

    semitones:
        Distance between the two notes.

    diatonic_number:
        Diatonic interval number where applicable.
        Tritones are ambiguous enharmonically, so this is None.

    aliases:
        Alternative names accepted during answer validation.
    """

    interval_id: str
    name: str
    semitones: int
    diatonic_number: Optional[int]
    aliases: Tuple[str, ...] = ()


# Complete interval catalogue within one octave.
INTERVAL_CATALOGUE = {
    "unison": IntervalDefinition(
        interval_id="unison",
        name="Perfect Unison",
        semitones=0,
        diatonic_number=1,
        aliases=("unison", "perfect unison"),
    ),
    "minor_second": IntervalDefinition(
        interval_id="minor_second",
        name="Minor Second",
        semitones=1,
        diatonic_number=2,
        aliases=("minor second", "flat second", "semitone"),
    ),
    "major_second": IntervalDefinition(
        interval_id="major_second",
        name="Major Second",
        semitones=2,
        diatonic_number=2,
        aliases=("major second", "whole tone", "whole step"),
    ),
    "minor_third": IntervalDefinition(
        interval_id="minor_third",
        name="Minor Third",
        semitones=3,
        diatonic_number=3,
        aliases=("minor third",),
    ),
    "major_third": IntervalDefinition(
        interval_id="major_third",
        name="Major Third",
        semitones=4,
        diatonic_number=3,
        aliases=("major third",),
    ),
    "perfect_fourth": IntervalDefinition(
        interval_id="perfect_fourth",
        name="Perfect Fourth",
        semitones=5,
        diatonic_number=4,
        aliases=("perfect fourth",),
    ),
    "tritone": IntervalDefinition(
        interval_id="tritone",
        name="Tritone",
        semitones=6,
        diatonic_number=None,
        aliases=("tritone", "augmented fourth", "diminished fifth"),
    ),
    "perfect_fifth": IntervalDefinition(
        interval_id="perfect_fifth",
        name="Perfect Fifth",
        semitones=7,
        diatonic_number=5,
        aliases=("perfect fifth",),
    ),
    "minor_sixth": IntervalDefinition(
        interval_id="minor_sixth",
        name="Minor Sixth",
        semitones=8,
        diatonic_number=6,
        aliases=("minor sixth",),
    ),
    "major_sixth": IntervalDefinition(
        interval_id="major_sixth",
        name="Major Sixth",
        semitones=9,
        diatonic_number=6,
        aliases=("major sixth",),
    ),
    "minor_seventh": IntervalDefinition(
        interval_id="minor_seventh",
        name="Minor Seventh",
        semitones=10,
        diatonic_number=7,
        aliases=("minor seventh",),
    ),
    "major_seventh": IntervalDefinition(
        interval_id="major_seventh",
        name="Major Seventh",
        semitones=11,
        diatonic_number=7,
        aliases=("major seventh",),
    ),
    "octave": IntervalDefinition(
        interval_id="octave",
        name="Perfect Octave",
        semitones=12,
        diatonic_number=8,
        aliases=("octave", "perfect octave"),
    ),
}


# Level 1 deliberately limits the interval vocabulary.
LEVEL_1_INTERVALS = (
    "unison",
    "minor_second",
    "major_second",
    "minor_third",
    "major_third",
    "perfect_fourth",
    "perfect_fifth",
    "octave",
)


# Level 2 introduces every remaining interval within the octave.
LEVEL_2_INTERVALS = tuple(INTERVAL_CATALOGUE.keys())


def get_intervals_for_level(
    level: EarTrainingLevel,
) -> Tuple[IntervalDefinition, ...]:
    """
    Return the interval definitions available at a curriculum level.

    Levels 3 and 4 use the complete interval vocabulary.
    Compound intervals are handled separately by the advanced engine.
    """

    if level == EarTrainingLevel.FOUNDATIONS:
        interval_ids = LEVEL_1_INTERVALS
    elif level in (
        EarTrainingLevel.INTERMEDIATE,
        EarTrainingLevel.ADVANCED,
        EarTrainingLevel.ACTIVE_RECALL,
    ):
        interval_ids = LEVEL_2_INTERVALS
    else:
        raise ValueError(f"Unsupported Ear Training level: {level}")

    return tuple(
        INTERVAL_CATALOGUE[interval_id]
        for interval_id in interval_ids
    )


# ---------------------------------------------------------------------------
# Question model
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class EarTrainingQuestion:
    """
    Represents one generated Ear Training question.

    midi_notes:
        Actual MIDI notes used for audio playback.
        One note for pitch identification, two for intervals,
        and three or more for chords.

    target_answer:
        Canonical answer used internally for validation and analytics.

    answer_options:
        Available choices for multiple-choice exercises.
        Empty for active-recall exercises.
    """

    level: EarTrainingLevel
    exercise_type: ExerciseType
    prompt: str
    target_answer: str
    midi_notes: Tuple[int, ...]
    answer_options: Tuple[str, ...] = ()
    starting_note: Optional[int] = None
    interval_id: Optional[str] = None
    chord_quality: Optional[str] = None
    chord_root: Optional[str] = None
    inversion: Optional[int] = None

    def __post_init__(self) -> None:
        if not isinstance(self.level, EarTrainingLevel):
            raise TypeError("level must be an EarTrainingLevel")

        if not isinstance(self.exercise_type, ExerciseType):
            raise TypeError("exercise_type must be an ExerciseType")

        if not self.prompt.strip():
            raise ValueError("Question prompt cannot be empty")

        if not self.target_answer.strip():
            raise ValueError("Target answer cannot be empty")

        if not self.midi_notes:
            raise ValueError("A question must contain at least one MIDI note")

        for midi_number in self.midi_notes:
            if (
                isinstance(midi_number, bool)
                or not isinstance(midi_number, int)
                or not 21 <= midi_number <= 108
            ):
                raise ValueError(
                    "MIDI notes must be integers within the piano range "
                    "(21–108)"
                )

        if self.answer_options and self.target_answer not in self.answer_options:
            raise ValueError(
                "The target answer must appear in the answer options"
            )

        if self.inversion is not None and (
            isinstance(self.inversion, bool)
            or not isinstance(self.inversion, int)
            or self.inversion < 0
        ):
            raise ValueError("Inversion must be a non-negative integer")

# ---------------------------------------------------------------------------
# Question generation
# ---------------------------------------------------------------------------

CHROMATIC_NOTE_NAMES = (
    "C", "C#", "D", "D#", "E", "F",
    "F#", "G", "G#", "A", "A#", "B",
)

CHORD_QUALITIES_BY_LEVEL = {
    EarTrainingLevel.FOUNDATIONS: (
        "Major",
        "Minor",
        "Diminished",
        "Sus4",
    ),
    EarTrainingLevel.INTERMEDIATE: (
        "Major",
        "Minor",
        "Diminished",
        "Sus4",
        "Sus2",
        "Dominant 7th",
        "Major 7th",
        "Minor 7th",
    ),
}

CHORD_INTERVALS = {
    "Major": (0, 4, 7),
    "Minor": (0, 3, 7),
    "Diminished": (0, 3, 6),
    "Sus4": (0, 5, 7),
    "Sus2": (0, 2, 7),
    "Dominant 7th": (0, 4, 7, 10),
    "Major 7th": (0, 4, 7, 11),
    "Minor 7th": (0, 3, 7, 10),
}

LEVEL_EXERCISES = {
    EarTrainingLevel.FOUNDATIONS: (
        ExerciseType.SINGLE_NOTE,
        ExerciseType.MELODIC_INTERVAL,
        ExerciseType.CHORD_QUALITY,
    ),
    EarTrainingLevel.INTERMEDIATE: (
        ExerciseType.SINGLE_NOTE,
        ExerciseType.MELODIC_INTERVAL,
        ExerciseType.HARMONIC_INTERVAL,
        ExerciseType.CHORD_QUALITY,
    ),
}


class EarTrainingQuestionGenerator:
    """
    Generates curriculum-controlled Ear Training questions.

    Randomness can be injected for deterministic testing.
    All generated pitches remain within MIDI 21–108.
    """

    def __init__(self, rng: Optional[random.Random] = None) -> None:
        self.rng = rng or random.Random()

    @staticmethod
    def _note_name(midi_number: int) -> str:
        """Convert a MIDI number into a note name including its octave."""

        from domain.music_theory import MusicTheory

        return MusicTheory.midi_number_to_note_name(midi_number)

    @staticmethod
    def _pitch_class_name(midi_number: int) -> str:
        """Return the chromatic note name without its octave."""

        return CHROMATIC_NOTE_NAMES[midi_number % 12]

    def generate(
        self,
        level: EarTrainingLevel,
        exercise_type: Optional[ExerciseType] = None,
    ) -> EarTrainingQuestion:
        """Generate a random question appropriate for the selected level."""

        if not isinstance(level, EarTrainingLevel):
            raise TypeError("level must be an EarTrainingLevel")

        available_exercises = LEVEL_EXERCISES.get(level)

        if available_exercises is None:
            raise ValueError(
                f"Question generation is not implemented for level {level.value}"
            )

        if exercise_type is None:
            exercise_type = self.rng.choice(available_exercises)
        elif exercise_type not in available_exercises:
            raise ValueError(
                f"{exercise_type.value} is not available at level {level.value}"
            )

        generators = {
            ExerciseType.SINGLE_NOTE: self._generate_single_note,
            ExerciseType.MELODIC_INTERVAL: self._generate_melodic_interval,
            ExerciseType.HARMONIC_INTERVAL: self._generate_harmonic_interval,
            ExerciseType.CHORD_QUALITY: self._generate_chord_quality,
        }

        return generators[exercise_type](level)

    def _generate_single_note(
        self,
        level: EarTrainingLevel,
    ) -> EarTrainingQuestion:
        """Generate a single-note identification question."""

        midi_number = self.rng.randint(48, 83)

        if level == EarTrainingLevel.FOUNDATIONS:
            target = self._pitch_class_name(midi_number)
            options = CHROMATIC_NOTE_NAMES
            prompt = "Identify the pitch."
        else:
            target = self._note_name(midi_number)

            octave_start = (midi_number // 12) * 12
            octave_notes = tuple(
                octave_start + offset
                for offset in range(12)
                if 21 <= octave_start + offset <= 108
            )

            options = tuple(
                self._note_name(note)
                for note in octave_notes
            )
            prompt = "Identify the exact note, including its octave."

        return EarTrainingQuestion(
            level=level,
            exercise_type=ExerciseType.SINGLE_NOTE,
            prompt=prompt,
            target_answer=target,
            midi_notes=(midi_number,),
            answer_options=options,
            starting_note=midi_number,
        )

    def _generate_melodic_interval(
        self,
        level: EarTrainingLevel,
    ) -> EarTrainingQuestion:
        """Generate an ascending or descending melodic interval."""

        interval = self.rng.choice(get_intervals_for_level(level))
        ascending = self.rng.choice((True, False))

        if ascending:
            starting_note = self.rng.randint(
                48,
                96 - interval.semitones,
            )
            second_note = starting_note + interval.semitones
        else:
            starting_note = self.rng.randint(
                48 + interval.semitones,
                96,
            )
            second_note = starting_note - interval.semitones

        return EarTrainingQuestion(
            level=level,
            exercise_type=ExerciseType.MELODIC_INTERVAL,
            prompt=(
                "Identify the ascending interval."
                if ascending
                else "Identify the descending interval."
            ),
            target_answer=interval.name,
            midi_notes=(starting_note, second_note),
            answer_options=tuple(
                item.name for item in get_intervals_for_level(level)
            ),
            starting_note=starting_note,
            interval_id=interval.interval_id,
        )

    def _generate_harmonic_interval(
        self,
        level: EarTrainingLevel,
    ) -> EarTrainingQuestion:
        """Generate two simultaneously played notes."""

        interval = self.rng.choice(get_intervals_for_level(level))

        starting_note = self.rng.randint(
            48,
            96 - interval.semitones,
        )
        second_note = starting_note + interval.semitones

        return EarTrainingQuestion(
            level=level,
            exercise_type=ExerciseType.HARMONIC_INTERVAL,
            prompt="Identify the harmonic interval.",
            target_answer=interval.name,
            midi_notes=(starting_note, second_note),
            answer_options=tuple(
                item.name for item in get_intervals_for_level(level)
            ),
            starting_note=starting_note,
            interval_id=interval.interval_id,
        )

    def _generate_chord_quality(
        self,
        level: EarTrainingLevel,
    ) -> EarTrainingQuestion:
        """Generate a root-position chord-quality identification question."""

        qualities = CHORD_QUALITIES_BY_LEVEL[level]
        quality = self.rng.choice(qualities)

        root_midi = self.rng.randint(48, 59)
        root_name = self._pitch_class_name(root_midi)

        midi_notes = tuple(
            root_midi + offset
            for offset in CHORD_INTERVALS[quality]
        )

        return EarTrainingQuestion(
            level=level,
            exercise_type=ExerciseType.CHORD_QUALITY,
            prompt="Identify the chord quality.",
            target_answer=quality,
            midi_notes=midi_notes,
            answer_options=qualities,
            starting_note=root_midi,
            chord_quality=quality,
            chord_root=root_name,
        )
