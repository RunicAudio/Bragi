import random

import pytest

from domain.ear_training_engine import (
    CHORD_INTERVALS,
    CHORD_QUALITIES_BY_LEVEL,
    INTERVAL_CATALOGUE,
    LEVEL_EXERCISES,
    EarTrainingLevel,
    EarTrainingQuestion,
    EarTrainingQuestionGenerator,
    ExerciseType,
    get_intervals_for_level,
)


@pytest.fixture
def generator():
    return EarTrainingQuestionGenerator(rng=random.Random(42))


class TestIntervalCatalogue:

    def test_catalogue_contains_thirteen_intervals(self):
        assert len(INTERVAL_CATALOGUE) == 13

    def test_level_one_contains_eight_intervals(self):
        intervals = get_intervals_for_level(
            EarTrainingLevel.FOUNDATIONS
        )
        assert len(intervals) == 8

    def test_level_two_contains_all_thirteen_intervals(self):
        intervals = get_intervals_for_level(
            EarTrainingLevel.INTERMEDIATE
        )
        assert len(intervals) == 13

    def test_level_one_excludes_tritone(self):
        intervals = get_intervals_for_level(
            EarTrainingLevel.FOUNDATIONS
        )
        assert "tritone" not in {
            interval.interval_id for interval in intervals
        }

    def test_level_two_includes_tritone(self):
        intervals = get_intervals_for_level(
            EarTrainingLevel.INTERMEDIATE
        )
        assert "tritone" in {
            interval.interval_id for interval in intervals
        }

    def test_interval_semitone_values(self):
        expected = {
            "unison": 0,
            "minor_second": 1,
            "major_second": 2,
            "minor_third": 3,
            "major_third": 4,
            "perfect_fourth": 5,
            "tritone": 6,
            "perfect_fifth": 7,
            "minor_sixth": 8,
            "major_sixth": 9,
            "minor_seventh": 10,
            "major_seventh": 11,
            "octave": 12,
        }

        actual = {
            key: interval.semitones
            for key, interval in INTERVAL_CATALOGUE.items()
        }

        assert actual == expected


class TestChordDefinitions:

    def test_all_eight_chord_qualities_are_defined(self):
        assert len(CHORD_INTERVALS) == 8

    @pytest.mark.parametrize(
        "quality, expected",
        [
            ("Major", (0, 4, 7)),
            ("Minor", (0, 3, 7)),
            ("Diminished", (0, 3, 6)),
            ("Sus4", (0, 5, 7)),
            ("Sus2", (0, 2, 7)),
            ("Dominant 7th", (0, 4, 7, 10)),
            ("Major 7th", (0, 4, 7, 11)),
            ("Minor 7th", (0, 3, 7, 10)),
        ],
    )
    def test_chord_formulas(self, quality, expected):
        assert CHORD_INTERVALS[quality] == expected

    def test_level_one_has_four_chord_qualities(self):
        assert len(
            CHORD_QUALITIES_BY_LEVEL[
                EarTrainingLevel.FOUNDATIONS
            ]
        ) == 4

    def test_level_two_has_eight_chord_qualities(self):
        assert len(
            CHORD_QUALITIES_BY_LEVEL[
                EarTrainingLevel.INTERMEDIATE
            ]
        ) == 8

    def test_level_one_excludes_extended_chords(self):
        qualities = CHORD_QUALITIES_BY_LEVEL[
            EarTrainingLevel.FOUNDATIONS
        ]

        assert "Sus2" not in qualities
        assert "Dominant 7th" not in qualities
        assert "Major 7th" not in qualities
        assert "Minor 7th" not in qualities


class TestQuestionGeneration:

    @pytest.mark.parametrize(
        "level, exercise_type",
        [
            (
                EarTrainingLevel.FOUNDATIONS,
                ExerciseType.SINGLE_NOTE,
            ),
            (
                EarTrainingLevel.FOUNDATIONS,
                ExerciseType.MELODIC_INTERVAL,
            ),
            (
                EarTrainingLevel.FOUNDATIONS,
                ExerciseType.CHORD_QUALITY,
            ),
            (
                EarTrainingLevel.INTERMEDIATE,
                ExerciseType.SINGLE_NOTE,
            ),
            (
                EarTrainingLevel.INTERMEDIATE,
                ExerciseType.MELODIC_INTERVAL,
            ),
            (
                EarTrainingLevel.INTERMEDIATE,
                ExerciseType.HARMONIC_INTERVAL,
            ),
            (
                EarTrainingLevel.INTERMEDIATE,
                ExerciseType.CHORD_QUALITY,
            ),
        ],
    )
    def test_supported_exercises_generate_questions(
        self,
        generator,
        level,
        exercise_type,
    ):
        question = generator.generate(level, exercise_type)

        assert isinstance(question, EarTrainingQuestion)
        assert question.level == level
        assert question.exercise_type == exercise_type

    def test_level_one_never_generates_harmonic_intervals(
        self,
        generator,
    ):
        with pytest.raises(ValueError):
            generator.generate(
                EarTrainingLevel.FOUNDATIONS,
                ExerciseType.HARMONIC_INTERVAL,
            )

    def test_level_three_is_not_yet_implemented(self, generator):
        with pytest.raises(ValueError):
            generator.generate(EarTrainingLevel.ADVANCED)

    def test_level_four_is_not_yet_implemented(self, generator):
        with pytest.raises(ValueError):
            generator.generate(EarTrainingLevel.ACTIVE_RECALL)

    def test_invalid_level_type_is_rejected(self, generator):
        with pytest.raises(TypeError):
            generator.generate(5)

    def test_all_generated_notes_stay_within_piano_range(
        self,
        generator,
    ):
        for level in (
            EarTrainingLevel.FOUNDATIONS,
            EarTrainingLevel.INTERMEDIATE,
        ):
            for _ in range(200):
                question = generator.generate(level)

                assert all(
                    21 <= note <= 108
                    for note in question.midi_notes
                )


class TestSingleNoteGeneration:

    def test_level_one_identifies_pitch_class(self, generator):
        question = generator.generate(
            EarTrainingLevel.FOUNDATIONS,
            ExerciseType.SINGLE_NOTE,
        )

        assert len(question.midi_notes) == 1
        assert len(question.target_answer) <= 2
        assert question.target_answer in question.answer_options

    def test_level_two_identifies_exact_octave(self, generator):
        question = generator.generate(
            EarTrainingLevel.INTERMEDIATE,
            ExerciseType.SINGLE_NOTE,
        )

        assert len(question.midi_notes) == 1
        assert question.target_answer[-1].isdigit()
        assert question.target_answer in question.answer_options

    def test_level_two_options_share_target_octave(self, generator):
        question = generator.generate(
            EarTrainingLevel.INTERMEDIATE,
            ExerciseType.SINGLE_NOTE,
        )

        target_octave = question.target_answer[-1]

        assert all(
            option[-1] == target_octave
            for option in question.answer_options
        )


class TestIntervalGeneration:

    @pytest.mark.parametrize(
        "level, exercise_type",
        [
            (
                EarTrainingLevel.FOUNDATIONS,
                ExerciseType.MELODIC_INTERVAL,
            ),
            (
                EarTrainingLevel.INTERMEDIATE,
                ExerciseType.MELODIC_INTERVAL,
            ),
            (
                EarTrainingLevel.INTERMEDIATE,
                ExerciseType.HARMONIC_INTERVAL,
            ),
        ],
    )
    def test_generated_interval_has_correct_distance(
        self,
        generator,
        level,
        exercise_type,
    ):
        for _ in range(100):
            question = generator.generate(level, exercise_type)

            interval = INTERVAL_CATALOGUE[question.interval_id]
            first, second = question.midi_notes

            assert abs(second - first) == interval.semitones

    def test_melodic_intervals_have_two_notes(self, generator):
        question = generator.generate(
            EarTrainingLevel.FOUNDATIONS,
            ExerciseType.MELODIC_INTERVAL,
        )

        assert len(question.midi_notes) == 2

    def test_melodic_interval_direction_matches_prompt(self, generator):
        for _ in range(100):
            question = generator.generate(
                EarTrainingLevel.FOUNDATIONS,
                ExerciseType.MELODIC_INTERVAL,
            )

            first, second = question.midi_notes

            if "ascending" in question.prompt:
                assert second >= first
            else:
                assert second <= first

    def test_harmonic_intervals_are_ordered_low_to_high(self, generator):
        question = generator.generate(
            EarTrainingLevel.INTERMEDIATE,
            ExerciseType.HARMONIC_INTERVAL,
        )

        first, second = question.midi_notes
        assert first <= second


class TestChordGeneration:

    @pytest.mark.parametrize(
        "level",
        [
            EarTrainingLevel.FOUNDATIONS,
            EarTrainingLevel.INTERMEDIATE,
        ],
    )
    def test_generated_chord_matches_its_formula(
        self,
        generator,
        level,
    ):
        for _ in range(100):
            question = generator.generate(
                level,
                ExerciseType.CHORD_QUALITY,
            )

            expected_offsets = CHORD_INTERVALS[
                question.chord_quality
            ]

            root = question.midi_notes[0]

            expected_notes = tuple(
                root + offset
                for offset in expected_offsets
            )

            assert question.midi_notes == expected_notes
            assert question.target_answer == question.chord_quality

    def test_level_one_only_generates_basic_qualities(self, generator):
        allowed = set(
            CHORD_QUALITIES_BY_LEVEL[
                EarTrainingLevel.FOUNDATIONS
            ]
        )

        for _ in range(100):
            question = generator.generate(
                EarTrainingLevel.FOUNDATIONS,
                ExerciseType.CHORD_QUALITY,
            )

            assert question.chord_quality in allowed

    def test_level_two_can_generate_all_eight_qualities(self):
        generator = EarTrainingQuestionGenerator(
            rng=random.Random(12345)
        )

        generated = {
            generator.generate(
                EarTrainingLevel.INTERMEDIATE,
                ExerciseType.CHORD_QUALITY,
            ).chord_quality
            for _ in range(1000)
        }

        assert generated == set(CHORD_INTERVALS.keys())


class TestQuestionValidation:

    def test_empty_prompt_is_rejected(self):
        with pytest.raises(ValueError):
            EarTrainingQuestion(
                level=EarTrainingLevel.FOUNDATIONS,
                exercise_type=ExerciseType.SINGLE_NOTE,
                prompt=" ",
                target_answer="C",
                midi_notes=(60,),
            )

    def test_empty_target_answer_is_rejected(self):
        with pytest.raises(ValueError):
            EarTrainingQuestion(
                level=EarTrainingLevel.FOUNDATIONS,
                exercise_type=ExerciseType.SINGLE_NOTE,
                prompt="Identify the pitch.",
                target_answer=" ",
                midi_notes=(60,),
            )

    def test_empty_midi_notes_are_rejected(self):
        with pytest.raises(ValueError):
            EarTrainingQuestion(
                level=EarTrainingLevel.FOUNDATIONS,
                exercise_type=ExerciseType.SINGLE_NOTE,
                prompt="Identify the pitch.",
                target_answer="C",
                midi_notes=(),
            )

    @pytest.mark.parametrize(
        "midi_number",
        [20, 109, -1, 200, True, 60.5],
    )
    def test_invalid_midi_notes_are_rejected(self, midi_number):
        with pytest.raises(ValueError):
            EarTrainingQuestion(
                level=EarTrainingLevel.FOUNDATIONS,
                exercise_type=ExerciseType.SINGLE_NOTE,
                prompt="Identify the pitch.",
                target_answer="C",
                midi_notes=(midi_number,),
            )

    def test_target_must_be_an_available_option(self):
        with pytest.raises(ValueError):
            EarTrainingQuestion(
                level=EarTrainingLevel.FOUNDATIONS,
                exercise_type=ExerciseType.SINGLE_NOTE,
                prompt="Identify the pitch.",
                target_answer="C",
                midi_notes=(60,),
                answer_options=("D", "E", "F"),
            )


class TestDeterministicGeneration:

    def test_same_seed_generates_same_questions(self):
        first = EarTrainingQuestionGenerator(
            rng=random.Random(1234)
        )
        second = EarTrainingQuestionGenerator(
            rng=random.Random(1234)
        )

        first_questions = [
            first.generate(EarTrainingLevel.INTERMEDIATE)
            for _ in range(20)
        ]

        second_questions = [
            second.generate(EarTrainingLevel.INTERMEDIATE)
            for _ in range(20)
        ]

        assert first_questions == second_questions
