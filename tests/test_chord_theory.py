import pytest

from domain.chord_definitions import (
    CHORD_DIATONIC_INTERVALS,
    CHORD_INTERVAL_OFFSETS,
    get_chord_pitch_classes,
)
from domain.music_theory import CHROMATIC_SHARPS
from domain.note_spelling import parse_note

from domain.chord_theory import (
    CHORD_FORMULAS,
    REFERENCE_CONTEXTS,
    REFERENCE_SCALE_DEGREES,
    ChordExplanation,
    ChordTone,
    explain_chord,
)


class TestChordFormulas:

    @pytest.mark.parametrize(
        "quality, expected",
        [
            ("Major", ["1", "3", "5"]),
            ("Minor", ["1", "b3", "5"]),
            ("Dominant 7th", ["1", "3", "5", "b7"]),
            ("Major 7th", ["1", "3", "5", "7"]),
            ("Minor 7th", ["1", "b3", "5", "b7"]),
            ("Sus4", ["1", "4", "5"]),
            ("Sus2", ["1", "2", "5"]),
            ("Diminished", ["1", "b3", "b5"]),
        ],
    )
    def test_chord_formulas(self, quality, expected):
        assert CHORD_FORMULAS[quality] == expected

    def test_all_eight_qualities_are_defined(self):
        assert len(CHORD_FORMULAS) == 8


class TestChordConstruction:

    @pytest.mark.parametrize(
        "root,quality,expected_notes",
        [
            ("C", "Major", ["C", "E", "G"]),
            ("A", "Minor", ["A", "C", "E"]),
            ("E", "Dominant 7th", ["E", "G#", "B", "D"]),
            ("F", "Major 7th", ["F", "A", "C", "E"]),
            ("A", "Minor 7th", ["A", "C", "E", "G"]),
            ("C", "Sus4", ["C", "F", "G"]),
            ("C", "Sus2", ["C", "D", "G"]),
            ("B", "Diminished", ["B", "D", "F"]),
        ],
    )
    def test_chord_tone_spelling(
        self, root, quality, expected_notes
    ):
        result = explain_chord(root, quality)

        assert [tone.note_name for tone in result.tones] == expected_notes

    @pytest.mark.parametrize(
        "root,quality,expected",
        [
            ("Db", "Major", ["Db", "F", "Ab"]),
            ("F#", "Major", ["F#", "A#", "C#"]),
            ("Bb", "Minor", ["Bb", "Db", "F"]),
            ("Eb", "Minor", ["Eb", "Gb", "Bb"]),
            ("G#", "Major", ["G#", "B#", "D#"]),
            ("C#", "Major", ["C#", "E#", "G#"]),
        ],
    )
    def test_enharmonic_spelling(
        self, root, quality, expected
    ):
        result = explain_chord(root, quality)

        assert [tone.note_name for tone in result.tones] == expected

    def test_chord_name_is_constructed_correctly(self):
        result = explain_chord("A", "Minor")

        assert result.chord_name == "A Minor"
        assert result.root_note == "A"
        assert result.quality == "Minor"


class TestIntervalIdentification:

    @pytest.mark.parametrize(
        "root,quality,expected",
        [
            (
                "A",
                "Major",
                [
                    ("1", "Perfect unison", 0),
                    ("3", "Major third", 4),
                    ("5", "Perfect fifth", 7),
                ],
            ),
            (
                "A",
                "Minor",
                [
                    ("1", "Perfect unison", 0),
                    ("b3", "Minor third", 3),
                    ("5", "Perfect fifth", 7),
                ],
            ),
            (
                "A",
                "Dominant 7th",
                [
                    ("1", "Perfect unison", 0),
                    ("3", "Major third", 4),
                    ("5", "Perfect fifth", 7),
                    ("b7", "Minor seventh", 10),
                ],
            ),
            (
                "A",
                "Major 7th",
                [
                    ("1", "Perfect unison", 0),
                    ("3", "Major third", 4),
                    ("5", "Perfect fifth", 7),
                    ("7", "Major seventh", 11),
                ],
            ),
            (
                "A",
                "Minor 7th",
                [
                    ("1", "Perfect unison", 0),
                    ("b3", "Minor third", 3),
                    ("5", "Perfect fifth", 7),
                    ("b7", "Minor seventh", 10),
                ],
            ),
            (
                "A",
                "Sus4",
                [
                    ("1", "Perfect unison", 0),
                    ("4", "Perfect fourth", 5),
                    ("5", "Perfect fifth", 7),
                ],
            ),
            (
                "A",
                "Sus2",
                [
                    ("1", "Perfect unison", 0),
                    ("2", "Major second", 2),
                    ("5", "Perfect fifth", 7),
                ],
            ),
            (
                "A",
                "Diminished",
                [
                    ("1", "Perfect unison", 0),
                    ("b3", "Minor third", 3),
                    ("b5", "Diminished fifth", 6),
                ],
            ),
        ],
    )
    def test_formula_degrees_and_intervals(
        self, root, quality, expected
    ):
        result = explain_chord(root, quality)

        actual = [
            (
                tone.formula_degree,
                tone.interval_name,
                tone.semitones_from_root,
            )
            for tone in result.tones
        ]

        assert actual == expected


class TestReferenceContexts:

    @pytest.mark.parametrize(
        "quality,expected_context",
        [
            ("Major", "A major"),
            ("Major 7th", "A major"),
            ("Minor", "A natural minor"),
            ("Minor 7th", "A natural minor"),
            ("Dominant 7th", "A Mixolydian"),
            ("Sus4", "A-rooted interval structure"),
            ("Sus2", "A-rooted interval structure"),
            ("Diminished", "A-rooted interval structure"),
        ],
    )
    def test_reference_context(
        self, quality, expected_context
    ):
        result = explain_chord("A", quality)

        assert result.reference_context == expected_context

    def test_reference_context_definitions(self):
        assert REFERENCE_CONTEXTS == {
            "Major": "major",
            "Major 7th": "major",
            "Minor": "natural minor",
            "Minor 7th": "natural minor",
            "Dominant 7th": "Mixolydian",
        }


class TestScaleDegreeRelationships:

    def test_a_minor_uses_natural_minor_scale_degrees(self):
        result = explain_chord("A", "Minor")

        assert [
            (tone.formula_degree, tone.scale_degree, tone.scale_degree_name)
            for tone in result.tones
        ] == [
            ("1", "1", "Tonic"),
            ("b3", "3", "Mediant"),
            ("5", "5", "Dominant"),
        ]

    def test_a_major_uses_major_scale_degrees(self):
        result = explain_chord("A", "Major")

        assert [
            (tone.scale_degree, tone.scale_degree_name)
            for tone in result.tones
        ] == [
            ("1", "Tonic"),
            ("3", "Mediant"),
            ("5", "Dominant"),
        ]

    def test_dominant_seventh_uses_mixolydian_degrees(self):
        result = explain_chord("A", "Dominant 7th")

        assert [
            (tone.formula_degree, tone.scale_degree, tone.scale_degree_name)
            for tone in result.tones
        ] == [
            ("1", "1", "Tonic"),
            ("3", "3", "Mediant"),
            ("5", "5", "Dominant"),
            ("b7", "b7", "Subtonic"),
        ]

    def test_minor_seventh_uses_natural_minor_degrees(self):
        result = explain_chord("A", "Minor 7th")

        assert [
            (tone.formula_degree, tone.scale_degree, tone.scale_degree_name)
            for tone in result.tones
        ] == [
            ("1", "1", "Tonic"),
            ("b3", "3", "Mediant"),
            ("5", "5", "Dominant"),
            ("b7", "b7", "Subtonic"),
        ]

    def test_major_seventh_uses_leading_tone(self):
        result = explain_chord("A", "Major 7th")

        seventh = result.tones[-1]

        assert seventh.note_name == "G#"
        assert seventh.formula_degree == "7"
        assert seventh.scale_degree == "7"
        assert seventh.scale_degree_name == "Leading tone"

    @pytest.mark.parametrize(
        "quality",
        ["Sus2", "Sus4", "Diminished"],
    )
    def test_unsupported_reference_scales_are_not_assigned(
        self, quality
    ):
        result = explain_chord("A", quality)

        for tone in result.tones:
            assert tone.scale_degree is None
            assert tone.scale_degree_name is None

    def test_reference_scale_degree_definitions(self):
        assert REFERENCE_SCALE_DEGREES == {
            "Major": ["1", "3", "5"],
            "Minor": ["1", "3", "5"],
            "Dominant 7th": ["1", "3", "5", "b7"],
            "Major 7th": ["1", "3", "5", "7"],
            "Minor 7th": ["1", "3", "5", "b7"],
        }


class TestChordExplanation:

    def test_returns_chord_explanation_model(self):
        result = explain_chord("C", "Major")

        assert isinstance(result, ChordExplanation)
        assert all(
            isinstance(tone, ChordTone)
            for tone in result.tones
        )

    def test_construction_explanation_contains_formula(self):
        result = explain_chord("A", "Minor")

        assert "A Minor" in result.construction_explanation
        assert "1 - b3 - 5" in result.construction_explanation

    def test_three_progressive_hints_are_provided(self):
        result = explain_chord("A", "Minor")

        assert len(result.hints) == 3
        assert "A" in result.hints[0]
        assert "Minor" in result.hints[1]
        assert "1 - b3 - 5" in result.hints[2]

    def test_hints_are_ordered_from_general_to_specific(self):
        result = explain_chord("A", "Minor")

        assert "formula" not in result.hints[0].lower()
        assert "formula" not in result.hints[1].lower()
        assert "formula" in result.hints[2].lower()


class TestInvalidChordInputs:

    def test_rejects_unsupported_quality(self):
        with pytest.raises(ValueError):
            explain_chord("C", "Augmented")

    def test_rejects_invalid_root(self):
        with pytest.raises(ValueError):
            explain_chord("H", "Major")

    def test_rejects_empty_root(self):
        with pytest.raises(ValueError):
            explain_chord("", "Major")

    def test_rejects_non_string_root(self):
        with pytest.raises(TypeError):
            explain_chord(4, "Major")

class TestChordTheoryCrossValidation:

    FORMULA_INTERVALS = {
        "1": (1, 0),
        "2": (2, 2),
        "b3": (3, 3),
        "3": (3, 4),
        "4": (4, 5),
        "b5": (5, 6),
        "5": (5, 7),
        "b7": (7, 10),
        "7": (7, 11),
    }

    def test_all_chord_formulas_match_authoritative_definitions(self):
        for quality, formula in CHORD_FORMULAS.items():
            interval_numbers = CHORD_DIATONIC_INTERVALS[quality]
            semitone_offsets = CHORD_INTERVAL_OFFSETS[quality]

            assert len(formula) == len(interval_numbers)
            assert len(formula) == len(semitone_offsets)

            for index, formula_degree in enumerate(formula):
                expected = self.FORMULA_INTERVALS[formula_degree]

                actual = (
                    interval_numbers[index],
                    semitone_offsets[index],
                )

                assert actual == expected, (
                    f"{quality}: formula degree {formula_degree} "
                    f"does not match its authoritative interval "
                    f"definition. Expected {expected}, got {actual}."
                )

    def test_all_96_generated_chords_have_consistent_pitch_classes(self):
        for root in CHROMATIC_SHARPS:
            for quality in CHORD_FORMULAS:
                explanation = explain_chord(root, quality)

                expected_pitch_classes = get_chord_pitch_classes(
                    root,
                    quality,
                )

                actual_pitch_classes = [
                    parse_note(tone.note_name).pitch_class
                    for tone in explanation.tones
                ]

                assert actual_pitch_classes == expected_pitch_classes, (
                    f"{root} {quality}: spelled notes do not match "
                    f"the authoritative pitch classes. "
                    f"Expected {expected_pitch_classes}, "
                    f"got {actual_pitch_classes}."
                )
