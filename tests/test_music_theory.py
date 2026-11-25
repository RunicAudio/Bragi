import math

import pytest

from domain.music_theory import CHROMATIC_SHARPS, MusicTheory


class TestNoteToPitchClass:

    @pytest.mark.parametrize(
        "note, expected",
        [
            ("C", 0),
            ("C#", 1),
            ("D", 2),
            ("D#", 3),
            ("E", 4),
            ("F", 5),
            ("F#", 6),
            ("G", 7),
            ("G#", 8),
            ("A", 9),
            ("A#", 10),
            ("B", 11),
        ],
    )
    def test_all_chromatic_notes(self, note, expected):
        assert MusicTheory.note_to_pitch_class(note) == expected

    def test_note_names_are_case_insensitive(self):
        assert MusicTheory.note_to_pitch_class("c") == 0
        assert MusicTheory.note_to_pitch_class("f#") == 6

    def test_whitespace_is_ignored(self):
        assert MusicTheory.note_to_pitch_class(" C ") == 0

    @pytest.mark.parametrize("note", ["H", "X", "", "Invalid", "C##", "Dbb"])
    def test_invalid_notes_return_negative_one(self, note):
        assert MusicTheory.note_to_pitch_class(note) == -1


class TestPitchClassToNote:

    @pytest.mark.parametrize(
        "pitch_class, expected",
        [
            (0, "C"),
            (1, "C#"),
            (2, "D"),
            (3, "D#"),
            (4, "E"),
            (5, "F"),
            (6, "F#"),
            (7, "G"),
            (8, "G#"),
            (9, "A"),
            (10, "A#"),
            (11, "B"),
        ],
    )
    def test_all_pitch_classes(self, pitch_class, expected):
        assert MusicTheory.pitch_class_to_note(pitch_class) == expected

    def test_pitch_classes_wrap_above_twelve(self):
        assert MusicTheory.pitch_class_to_note(12) == "C"
        assert MusicTheory.pitch_class_to_note(13) == "C#"

    def test_negative_pitch_classes_wrap_below_zero(self):
        assert MusicTheory.pitch_class_to_note(-1) == "B"
        assert MusicTheory.pitch_class_to_note(-12) == "C"

class TestEnharmonicNoteSupport:

    @pytest.mark.parametrize(
        "note, expected",
        [
            ("Db", 1),
            ("Eb", 3),
            ("Gb", 6),
            ("Ab", 8),
            ("Bb", 10),
            ("C#", 1),
            ("D#", 3),
            ("F#", 6),
            ("G#", 8),
            ("A#", 10),
            ("E#", 5),
            ("Fb", 4),
            ("B#", 0),
            ("Cb", 11),
        ],
    )
    def test_enharmonic_notes(self, note, expected):
        assert MusicTheory.note_to_pitch_class(note) == expected

    def test_unicode_accidentals(self):
        assert MusicTheory.note_to_pitch_class("C♯") == 1
        assert MusicTheory.note_to_pitch_class("D♭") == 1

    def test_lowercase_flat_input(self):
        assert MusicTheory.note_to_pitch_class("db") == 1
        assert MusicTheory.note_to_pitch_class("bb") == 10

class TestFlatNotation:

    @pytest.mark.parametrize(
        "pitch_class, expected",
        [
            (0, "C"),
            (1, "Db"),
            (2, "D"),
            (3, "Eb"),
            (4, "E"),
            (5, "F"),
            (6, "Gb"),
            (7, "G"),
            (8, "Ab"),
            (9, "A"),
            (10, "Bb"),
            (11, "B"),
        ],
    )
    def test_flat_pitch_class_names(self, pitch_class, expected):
        assert MusicTheory.pitch_class_to_note(
            pitch_class,
            prefer_flats=True
        ) == expected

    def test_default_output_remains_sharp_based(self):
        assert MusicTheory.pitch_class_to_note(1) == "C#"
        assert MusicTheory.pitch_class_to_note(10) == "A#"
class TestFrequencyToNoteInfo:

    @pytest.mark.parametrize(
        "frequency, expected_note, expected_pitch_class",
        [
            (440.00, "A", 9),
            (261.63, "C", 0),
            (329.63, "E", 4),
            (82.41, "E", 4),
            (110.00, "A", 9),
            (146.83, "D", 2),
            (196.00, "G", 7),
            (246.94, "B", 11),
        ],
    )
    def test_standard_frequencies(
        self,
        frequency,
        expected_note,
        expected_pitch_class,
    ):
        note, pitch_class, cents = MusicTheory.frequency_to_note_info(
            frequency
        )

        assert note == expected_note
        assert pitch_class == expected_pitch_class
        assert abs(cents) < 2.0

    def test_a4_is_exactly_zero_cents(self):
        note, pitch_class, cents = MusicTheory.frequency_to_note_info(440.0)

        assert note == "A"
        assert pitch_class == 9
        assert cents == pytest.approx(0.0, abs=0.001)

    @pytest.mark.parametrize("cents_offset", [-49, -25, -10, 10, 25, 49])
    def test_cents_deviation(self, cents_offset):
        frequency = 440.0 * (2 ** (cents_offset / 1200))

        note, pitch_class, cents = MusicTheory.frequency_to_note_info(
            frequency
        )

        assert note == "A"
        assert pitch_class == 9
        assert cents == pytest.approx(cents_offset, abs=0.001)

    def test_invalid_nonpositive_frequencies(self):
        assert MusicTheory.frequency_to_note_info(0) == ("--", -1, 0.0)
        assert MusicTheory.frequency_to_note_info(-100) == ("--", -1, 0.0)

def test_frequency_conversion_supports_flat_notation():
    note, pitch_class, cents = MusicTheory.frequency_to_note_info(
        277.18,
        prefer_flats=True
    )

    assert note == "Db"
    assert pitch_class == 1
    assert abs(cents) < 2.0
