import pytest

from domain.note_spelling import (
    SpelledNote,
    parse_note,
    spell_interval,
    spell_note_from_pitch_class,
)


class TestParseNote:
    @pytest.mark.parametrize(
        "name,letter,accidental,pitch_class",
        [
            ("C", "C", 0, 0),
            ("D", "D", 0, 2),
            ("F#", "F", 1, 6),
            ("Bb", "B", -1, 10),
            ("C##", "C", 2, 2),
            ("Ebb", "E", -2, 2),
            ("Fx", "F", 2, 7),
            ("Db", "D", -1, 1),
            ("F♯", "F", 1, 6),
            ("B♭", "B", -1, 10),
            ("G𝄪", "G", 2, 9),
            ("Abb", "A", -2, 7),
            ("  c#  ", "C", 1, 1),
        ],
    )
    def test_parses_supported_notes(
        self, name, letter, accidental, pitch_class
    ):
        note = parse_note(name)

        assert note.letter == letter
        assert note.accidental == accidental
        assert note.pitch_class == pitch_class

    @pytest.mark.parametrize(
        "name",
        [
            "",
            " ",
            "H",
            "C###",
            "Dbbb",
            "C#b",
            "C natural",
            "4",
        ],
    )
    def test_rejects_invalid_note_names(self, name):
        with pytest.raises(ValueError):
            parse_note(name)

    def test_rejects_non_string_input(self):
        with pytest.raises(TypeError):
            parse_note(4)


class TestSpelledNote:
    def test_formats_ascii_accidentals(self):
        assert SpelledNote("C", 1).format() == "C#"
        assert SpelledNote("B", -1).format() == "Bb"
        assert SpelledNote("F", 2).format() == "F##"
        assert SpelledNote("E", -2).format() == "Ebb"

    def test_formats_unicode_accidentals(self):
        assert SpelledNote("C", 1).format(True) == "C♯"
        assert SpelledNote("B", -1).format(True) == "B♭"
        assert SpelledNote("F", 2).format(True) == "F𝄪"
        assert SpelledNote("E", -2).format(True) == "E𝄫"

    def test_rejects_invalid_letter(self):
        with pytest.raises(ValueError):
            SpelledNote("H")

    def test_rejects_unformattable_accidental(self):
        with pytest.raises(ValueError):
            SpelledNote("C", 3).format()


class TestSpellInterval:
    @pytest.mark.parametrize(
        "root,interval,semitones,expected",
        [
            ("C", 1, 0, "C"),
            ("C", 2, 2, "D"),
            ("C", 3, 4, "E"),
            ("C", 3, 3, "Eb"),
            ("C", 4, 5, "F"),
            ("C", 4, 6, "F#"),
            ("C", 5, 6, "Gb"),
            ("C", 5, 7, "G"),
            ("C", 5, 8, "G#"),
            ("C", 6, 9, "A"),
            ("C", 7, 10, "Bb"),
            ("C", 7, 11, "B"),
            ("C", 8, 12, "C"),
            ("Db", 3, 4, "F"),
            ("Db", 3, 3, "Fb"),
            ("Db", 5, 7, "Ab"),
            ("F#", 3, 4, "A#"),
            ("F#", 5, 7, "C#"),
            ("Bb", 3, 3, "Db"),
            ("Bb", 5, 7, "F"),
            ("Eb", 3, 3, "Gb"),
            ("Eb", 5, 7, "Bb"),
            ("G#", 3, 4, "B#"),
            ("G#", 7, 11, "F##"),
            ("C#", 5, 7, "G#"),
            ("F", 4, 6, "B"),
        ],
    )
    def test_spells_intervals(
        self, root, interval, semitones, expected
    ):
        assert spell_interval(root, interval, semitones) == expected

    def test_spells_unicode_accidentals(self):
        assert spell_interval(
            "F#", 3, 4, unicode_accidentals=True
        ) == "A♯"

        assert spell_interval(
            "G#", 7, 11, unicode_accidentals=True
        ) == "F𝄪"

    def test_supports_intervals_across_octaves(self):
        assert spell_interval("C", 9, 14) == "D"
        assert spell_interval("C", 10, 16) == "E"
        assert spell_interval("G", 8, 12) == "G"

    @pytest.mark.parametrize(
        "interval,semitones",
        [
            (0, 0),
            (-1, 0),
            (3.5, 4),
            (3, 4.5),
            (True, 4),
        ],
    )
    def test_rejects_invalid_interval_arguments(
        self, interval, semitones
    ):
        with pytest.raises((TypeError, ValueError)):
            spell_interval("C", interval, semitones)


class TestSpellNoteFromPitchClass:
    @pytest.mark.parametrize(
        "root,interval,pitch_class,expected",
        [
            ("C", 3, 4, "E"),
            ("C", 3, 3, "Eb"),
            ("Db", 3, 5, "F"),
            ("F#", 3, 10, "A#"),
            ("G#", 7, 7, "F##"),
            ("Bb", 5, 5, "F"),
            ("Eb", 3, 6, "Gb"),
        ],
    )
    def test_spells_pitch_classes_in_context(
        self, root, interval, pitch_class, expected
    ):
        assert spell_note_from_pitch_class(
            root, interval, pitch_class
        ) == expected

    def test_rejects_pitch_class_outside_range(self):
        with pytest.raises(ValueError):
            spell_note_from_pitch_class("C", 3, 12)

        with pytest.raises(ValueError):
            spell_note_from_pitch_class("C", 3, -1)

    def test_rejects_non_integer_pitch_class(self):
        with pytest.raises(TypeError):
            spell_note_from_pitch_class("C", 3, 4.5)

    def test_rejects_boolean_pitch_class(self):
        with pytest.raises(TypeError):
            spell_note_from_pitch_class("C", 3, True)

