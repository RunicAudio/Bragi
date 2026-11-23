import pytest

from domain.music_theory import CHROMATIC_SHARPS
from domain.scale_definitions import (
    SCALE_FORMULAS,
    ScaleType,
    SequenceDirection,
    ScaleDefinition,
    ScaleSequencer,
)


# ============================================================
# SCALE FORMULAS
# ============================================================

class TestScaleFormulas:

    def test_all_four_scale_types_are_defined(self):
        assert len(SCALE_FORMULAS) == 4
        assert set(SCALE_FORMULAS) == set(ScaleType)

    @pytest.mark.parametrize(
        "scale_type, expected",
        [
            (ScaleType.MAJOR, [0, 2, 4, 5, 7, 9, 11]),
            (ScaleType.NATURAL_MINOR, [0, 2, 3, 5, 7, 8, 10]),
            (ScaleType.MAJOR_PENTATONIC, [0, 2, 4, 7, 9]),
            (ScaleType.MINOR_PENTATONIC, [0, 3, 5, 7, 10]),
        ],
    )
    def test_scale_formula_intervals(self, scale_type, expected):
        assert SCALE_FORMULAS[scale_type] == expected

    def test_major_scale_has_seven_notes(self):
        assert len(SCALE_FORMULAS[ScaleType.MAJOR]) == 7

    def test_natural_minor_scale_has_seven_notes(self):
        assert len(SCALE_FORMULAS[ScaleType.NATURAL_MINOR]) == 7

    def test_pentatonic_scales_have_five_notes(self):
        assert len(SCALE_FORMULAS[ScaleType.MAJOR_PENTATONIC]) == 5
        assert len(SCALE_FORMULAS[ScaleType.MINOR_PENTATONIC]) == 5


# ============================================================
# SCALE DEFINITIONS
# ============================================================

class TestScaleDefinition:

    @pytest.mark.parametrize(
        "root, expected_root",
        [(note, index) for index, note in enumerate(CHROMATIC_SHARPS)],
    )
    def test_root_pitch_class_for_all_chromatic_notes(self, root, expected_root):
        scale = ScaleDefinition(root, ScaleType.MAJOR)
        assert scale.root_pitch_class == expected_root

    @pytest.mark.parametrize(
        "scale_type, intervals",
        list(SCALE_FORMULAS.items()),
    )
    @pytest.mark.parametrize(
        "root, root_pc",
        [(note, index) for index, note in enumerate(CHROMATIC_SHARPS)],
    )
    def test_ordered_pitch_classes_for_all_roots_and_scales(
        self, scale_type, intervals, root, root_pc
    ):
        scale = ScaleDefinition(root, scale_type)

        expected = [(root_pc + interval) % 12 for interval in intervals]

        assert scale.ordered_pitch_classes == expected

    @pytest.mark.parametrize(
        "scale_type, intervals",
        list(SCALE_FORMULAS.items()),
    )
    @pytest.mark.parametrize("root_pc", range(12))
    def test_pitch_class_set_matches_ordered_pitch_classes(
        self, scale_type, intervals, root_pc
    ):
        root = CHROMATIC_SHARPS[root_pc]
        scale = ScaleDefinition(root, scale_type)

        assert scale.pitch_classes == set(scale.ordered_pitch_classes)

    def test_c_major_scale(self):
        scale = ScaleDefinition("C", ScaleType.MAJOR)

        assert scale.ordered_pitch_classes == [0, 2, 4, 5, 7, 9, 11]

    def test_a_natural_minor_scale(self):
        scale = ScaleDefinition("A", ScaleType.NATURAL_MINOR)

        assert scale.ordered_pitch_classes == [9, 11, 0, 2, 4, 5, 7]

    def test_e_minor_pentatonic_scale(self):
        scale = ScaleDefinition("E", ScaleType.MINOR_PENTATONIC)

        assert scale.ordered_pitch_classes == [4, 7, 9, 11, 2]

    def test_g_major_pentatonic_scale(self):
        scale = ScaleDefinition("G", ScaleType.MAJOR_PENTATONIC)

        assert scale.ordered_pitch_classes == [7, 9, 11, 2, 4]

    def test_root_note_is_normalized(self):
        scale = ScaleDefinition("  c#  ", ScaleType.MAJOR)

        assert scale.root_note == "C#"
        assert scale.root_pitch_class == 1

    def test_pitch_classes_are_within_valid_range(self):
        for scale_type in ScaleType:
            for root in CHROMATIC_SHARPS:
                scale = ScaleDefinition(root, scale_type)

                assert all(0 <= pc <= 11 for pc in scale.pitch_classes)

    def test_pitch_classes_do_not_contain_duplicates(self):
        for scale_type in ScaleType:
            for root in CHROMATIC_SHARPS:
                scale = ScaleDefinition(root, scale_type)

                assert len(scale.pitch_classes) == len(
                    scale.ordered_pitch_classes
                )


# ============================================================
# SEQUENCE GENERATION
# ============================================================

class TestScaleSequencerGeneration:

    @pytest.fixture
    def notes(self):
        return ["C", "D", "E", "F", "G", "A", "B"]

    def test_ascending_sequence(self, notes):
        sequencer = ScaleSequencer(
            notes,
            SequenceDirection.ASCENDING,
        )

        assert sequencer.sequence == notes

    def test_descending_sequence(self, notes):
        sequencer = ScaleSequencer(
            notes,
            SequenceDirection.DESCENDING,
        )

        assert sequencer.sequence == list(reversed(notes))

    def test_ascending_descending_sequence(self, notes):
        sequencer = ScaleSequencer(
            notes,
            SequenceDirection.ASCENDING_DESCENDING,
        )

        assert sequencer.sequence == [
            "C", "D", "E", "F", "G", "A", "B",
            "A", "G", "F", "E", "D", "C",
        ]

    def test_ascending_descending_does_not_repeat_top_note(self, notes):
        sequencer = ScaleSequencer(
            notes,
            SequenceDirection.ASCENDING_DESCENDING,
        )

        assert sequencer.sequence.count("B") == 1

    def test_third_leaps_sequence(self, notes):
        sequencer = ScaleSequencer(
            notes,
            SequenceDirection.THIRD_LEAPS,
        )

        assert sequencer.sequence == [
            "C", "E",
            "D", "F",
            "E", "G",
            "F", "A",
            "G", "B",
            "A", "C",
            "B", "D",
        ]

    def test_third_leaps_wrap_around_at_end(self, notes):
        sequencer = ScaleSequencer(
            notes,
            SequenceDirection.THIRD_LEAPS,
        )

        assert sequencer.sequence[-4:] == [
            "A", "C", "B", "D"
        ]

    def test_random_sequence_contains_all_original_notes(self, notes):
        sequencer = ScaleSequencer(
            notes,
            SequenceDirection.RANDOM,
        )

        assert sorted(sequencer.sequence) == sorted(notes)

    def test_random_sequence_does_not_duplicate_notes(self, notes):
        sequencer = ScaleSequencer(
            notes,
            SequenceDirection.RANDOM,
        )

        assert len(sequencer.sequence) == len(notes)
        assert len(set(sequencer.sequence)) == len(notes)

    def test_empty_input_produces_empty_sequence(self):
        sequencer = ScaleSequencer([])

        assert sequencer.sequence == []
        assert sequencer.current_index == 0

    def test_default_direction_is_ascending(self, notes):
        sequencer = ScaleSequencer(notes)

        assert sequencer.direction == SequenceDirection.ASCENDING
        assert sequencer.sequence == notes

    def test_initial_index_is_zero(self, notes):
        sequencer = ScaleSequencer(notes)

        assert sequencer.current_index == 0

    def test_generate_sequence_updates_direction(self, notes):
        sequencer = ScaleSequencer(notes)

        sequencer.generate_sequence(
            notes,
            SequenceDirection.DESCENDING,
        )

        assert sequencer.direction == SequenceDirection.DESCENDING
        assert sequencer.sequence == list(reversed(notes))

    def test_generate_sequence_resets_current_index(self, notes):
        sequencer = ScaleSequencer(notes)
        sequencer.advance()
        sequencer.advance()

        sequencer.generate_sequence(
            notes,
            SequenceDirection.DESCENDING,
        )

        assert sequencer.current_index == 0


# ============================================================
# SEQUENCE ADVANCEMENT
# ============================================================

class TestScaleSequencerAdvance:

    def test_advance_returns_next_note(self):
        sequencer = ScaleSequencer(
            ["C", "D", "E"],
            SequenceDirection.ASCENDING,
        )

        assert sequencer.advance() == "D"
        assert sequencer.advance() == "E"

    def test_advance_wraps_to_start(self):
        sequencer = ScaleSequencer(
            ["C", "D", "E"],
            SequenceDirection.ASCENDING,
        )

        sequencer.advance()
        sequencer.advance()

        assert sequencer.advance() == "C"
        assert sequencer.current_index == 0

    def test_advance_cycles_repeatedly(self):
        sequencer = ScaleSequencer(
            ["C", "D", "E"],
            SequenceDirection.ASCENDING,
        )

        results = [sequencer.advance() for _ in range(6)]

        assert results == ["D", "E", "C", "D", "E", "C"]

    def test_advance_on_empty_sequence_returns_none(self):
        sequencer = ScaleSequencer([])

        assert sequencer.advance() is None

    def test_single_note_sequence(self):
        sequencer = ScaleSequencer(["C"])

        assert sequencer.sequence == ["C"]
        assert sequencer.advance() == "C"
        assert sequencer.current_index == 0


# ============================================================
# INPUT AND STATE HANDLING
# ============================================================

class TestScaleSequencerState:

    def test_scale_notes_are_stored(self):
        notes = ["C", "D", "E"]
        sequencer = ScaleSequencer(notes)

        assert sequencer.scale_notes == notes

    def test_generate_sequence_replaces_previous_notes(self):
        sequencer = ScaleSequencer(["C", "D", "E"])

        sequencer.generate_sequence(
            ["G", "A", "B"],
            SequenceDirection.ASCENDING,
        )

        assert sequencer.scale_notes == ["G", "A", "B"]
        assert sequencer.sequence == ["G", "A", "B"]

    def test_generate_sequence_with_empty_notes_clears_sequence(self):
        sequencer = ScaleSequencer(["C", "D", "E"])

        sequencer.generate_sequence([])

        assert sequencer.sequence == []
        assert sequencer.current_index == 0

    def test_direction_is_preserved_when_not_specified(self):
        sequencer = ScaleSequencer(
            ["C", "D", "E"],
            SequenceDirection.DESCENDING,
        )

        sequencer.generate_sequence(["G", "A", "B"])

        assert sequencer.direction == SequenceDirection.DESCENDING
        assert sequencer.sequence == ["B", "A", "G"]

    def test_generate_sequence_returns_generated_sequence(self):
        sequencer = ScaleSequencer()

        result = sequencer.generate_sequence(
            ["C", "D", "E"],
            SequenceDirection.ASCENDING,
        )

        assert result == ["C", "D", "E"]
        assert result is sequencer.sequence
