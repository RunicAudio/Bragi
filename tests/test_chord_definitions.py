import pytest

from domain.chord_definitions import (
    CHORD_INTERVAL_OFFSETS,
    ChordQuality,
    CAGEDPosition,
    FingeringCoordinate,
    ChordVoicing,
    ChordDefinition,
    TargetChord,
    get_chord_pitch_classes,
    get_available_chord_names,
    select_random_chord,
)

from domain.music_theory import CHROMATIC_SHARPS, MusicTheory


class TestChordIntervalOffsets:

    @pytest.mark.parametrize(
        "quality, expected",
        [
            ("Major", [0, 4, 7]),
            ("Minor", [0, 3, 7]),
            ("Dominant 7th", [0, 4, 7, 10]),
            ("Major 7th", [0, 4, 7, 11]),
            ("Minor 7th", [0, 3, 7, 10]),
            ("Sus4", [0, 5, 7]),
            ("Sus2", [0, 2, 7]),
            ("Diminished", [0, 3, 6]),
        ],
    )
    def test_chord_quality_formulas(self, quality, expected):
        assert CHORD_INTERVAL_OFFSETS[quality] == expected

    def test_all_eight_chord_qualities_are_defined(self):
        assert len(CHORD_INTERVAL_OFFSETS) == 8

    def test_chord_quality_enum_matches_supported_qualities(self):
        enum_values = {quality.value for quality in ChordQuality}
        assert enum_values == set(CHORD_INTERVAL_OFFSETS.keys())


class TestChordPitchClasses:

    @pytest.mark.parametrize(
        "root_note, root_pitch_class",
        list(zip(CHROMATIC_SHARPS, range(12))),
    )
    @pytest.mark.parametrize(
        "quality, intervals",
        list(CHORD_INTERVAL_OFFSETS.items()),
    )
    def test_chord_pitch_classes_for_all_roots_and_qualities(
        self,
        root_note,
        root_pitch_class,
        quality,
        intervals,
    ):
        expected = [
            (root_pitch_class + interval) % 12
            for interval in intervals
        ]

        result = get_chord_pitch_classes(root_note, quality)

        assert result == expected
        assert all(0 <= pitch_class <= 11 for pitch_class in result)

    def test_c_major_pitch_classes(self):
        assert get_chord_pitch_classes("C", "Major") == [0, 4, 7]

    def test_a_minor_pitch_classes(self):
        assert get_chord_pitch_classes("A", "Minor") == [9, 0, 4]

    def test_e_dominant_seventh_pitch_classes(self):
        assert get_chord_pitch_classes("E", "Dominant 7th") == [
            4, 8, 11, 2
        ]


class TestAvailableChordNames:

    def test_generates_96_chord_names(self):
        names = get_available_chord_names()
        assert len(names) == 96

    def test_all_chord_names_are_unique(self):
        names = get_available_chord_names()
        assert len(names) == len(set(names))

    def test_every_root_has_all_eight_qualities(self):
        names = get_available_chord_names()

        for root in CHROMATIC_SHARPS:
            root_chords = [
                name for name in names
                if name.startswith(f"{root} ")
            ]

            assert len(root_chords) == 8

    def test_every_generated_name_uses_a_supported_quality(self):
        names = get_available_chord_names()

        for name in names:
            root, quality = name.split(" ", 1)

            assert root in CHROMATIC_SHARPS
            assert quality in CHORD_INTERVAL_OFFSETS


class TestRandomChordSelection:

    def test_selected_chord_is_supported(self):
        selected = select_random_chord()

        assert selected in get_available_chord_names()

    def test_previous_chord_is_excluded(self, monkeypatch):
        previous = "C Major"
        captured_candidates = []

        def mock_choice(candidates):
            captured_candidates.extend(candidates)
            return candidates[0]

        monkeypatch.setattr(
            "domain.chord_definitions.random.choice",
            mock_choice,
        )

        selected = select_random_chord(previous)

        assert previous not in captured_candidates
        assert selected in captured_candidates
        assert len(captured_candidates) == 95

    def test_no_previous_chord_keeps_all_choices(self, monkeypatch):
        captured_candidates = []

        def mock_choice(candidates):
            captured_candidates.extend(candidates)
            return candidates[0]

        monkeypatch.setattr(
            "domain.chord_definitions.random.choice",
            mock_choice,
        )

        select_random_chord()

        assert len(captured_candidates) == 96

    def test_invalid_previous_chord_does_not_remove_choices(
        self,
        monkeypatch,
    ):
        captured_candidates = []

        def mock_choice(candidates):
            captured_candidates.extend(candidates)
            return candidates[0]

        monkeypatch.setattr(
            "domain.chord_definitions.random.choice",
            mock_choice,
        )

        select_random_chord("Not A Chord")

        assert len(captured_candidates) == 96


class TestChordModels:

    def test_fingering_coordinate_defaults(self):
        fingering = FingeringCoordinate(
            string_num=1,
            fret=3,
        )

        assert fingering.finger is None
        assert fingering.is_muted is False
        assert fingering.is_open is False

    def test_chord_definition_creation(self):
        chord = ChordDefinition(
            name="C Major",
            root_note="C",
            quality="Major",
            pitch_classes=[0, 4, 7],
            note_names=["C", "E", "G"],
        )

        assert chord.name == "C Major"
        assert chord.pitch_classes == [0, 4, 7]

    def test_target_chord_display_title(self):
        chord = ChordDefinition(
            name="G Major",
            root_note="G",
            quality="Major",
            pitch_classes=[7, 11, 2],
            note_names=["G", "B", "D"],
        )

        target = TargetChord(chord_definition=chord)

        assert target.display_title == "G Major"

    def test_target_chord_is_frozen(self):
        chord = ChordDefinition(
            name="A Minor",
            root_note="A",
            quality="Minor",
            pitch_classes=[9, 0, 4],
            note_names=["A", "C", "E"],
        )

        target = TargetChord(chord_definition=chord)

        with pytest.raises(Exception):
            target.required_voicing = None
