import pytest

from domain.instrument_definitions import (
    InstrumentConfiguration,
    InstrumentType,
    TuningString,
    STANDARD_TUNINGS,
    create_custom_configuration,
    get_available_instruments,
    get_standard_configuration,
    note_to_frequency,
    note_to_midi_number,
)


# ---------------------------------------------------------------------------
# Standard instrument configurations
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "instrument, expected_count, expected_tuning",
    [
        (InstrumentType.GUITAR, 6, "Standard"),
        (InstrumentType.BASS, 4, "Standard"),
        (InstrumentType.UKULELE, 4, "Standard (High G)"),
        (InstrumentType.BARITONE_UKULELE, 4, "Standard"),
        (InstrumentType.BANJO, 5, "Open G"),
    ],
)
def test_standard_instrument_configurations(
    instrument,
    expected_count,
    expected_tuning,
):
    config = get_standard_configuration(instrument)

    assert config.instrument_type == instrument
    assert config.string_count == expected_count
    assert config.tuning_name == expected_tuning
    assert len(config.strings) == expected_count


def test_all_instruments_have_standard_configurations():
    assert set(STANDARD_TUNINGS) == set(InstrumentType)


def test_available_instruments_returns_all_instrument_names():
    assert set(get_available_instruments()) == {
        "Guitar",
        "Bass",
        "Ukulele",
        "Baritone Ukulele",
        "Banjo",
    }


# ---------------------------------------------------------------------------
# Guitar tuning
# ---------------------------------------------------------------------------

def test_standard_guitar_tuning():
    config = get_standard_configuration(InstrumentType.GUITAR)

    expected = {
        6: ("E", 2),
        5: ("A", 2),
        4: ("D", 3),
        3: ("G", 3),
        2: ("B", 3),
        1: ("E", 4),
    }

    for string_number, (note, octave) in expected.items():
        string = config.get_string(string_number)

        assert string.note == note
        assert string.octave == octave


def test_guitar_string_frequencies():
    config = get_standard_configuration(InstrumentType.GUITAR)

    expected = {
        6: 82.4069,
        5: 110.0,
        4: 146.8324,
        3: 195.9977,
        2: 246.9417,
        1: 329.6276,
    }

    for string_number, expected_frequency in expected.items():
        assert config.get_string(string_number).frequency == pytest.approx(
            expected_frequency,
            abs=0.01,
        )


# ---------------------------------------------------------------------------
# Bass tuning
# ---------------------------------------------------------------------------

def test_standard_four_string_bass_tuning():
    config = get_standard_configuration(InstrumentType.BASS)

    expected = {
        4: ("E", 1),
        3: ("A", 1),
        2: ("D", 2),
        1: ("G", 2),
    }

    for string_number, (note, octave) in expected.items():
        string = config.get_string(string_number)

        assert (string.note, string.octave) == (note, octave)


def test_bass_low_e_frequency():
    config = get_standard_configuration(InstrumentType.BASS)

    assert config.get_string(4).frequency == pytest.approx(
        41.2034,
        abs=0.01,
    )


# ---------------------------------------------------------------------------
# Ukulele tuning
# ---------------------------------------------------------------------------

def test_standard_ukulele_is_reentrant():
    config = get_standard_configuration(InstrumentType.UKULELE)

    expected = {
        4: ("G", 4),
        3: ("C", 4),
        2: ("E", 4),
        1: ("A", 4),
    }

    for string_number, (note, octave) in expected.items():
        string = config.get_string(string_number)

        assert (string.note, string.octave) == (note, octave)

    # High G must be higher than the C string.
    assert config.get_string(4).frequency > config.get_string(3).frequency


def test_standard_baritone_ukulele_tuning():
    config = get_standard_configuration(InstrumentType.BARITONE_UKULELE)

    expected = {
        4: ("D", 3),
        3: ("G", 3),
        2: ("B", 3),
        1: ("E", 4),
    }

    for string_number, (note, octave) in expected.items():
        string = config.get_string(string_number)

        assert (string.note, string.octave) == (note, octave)


# ---------------------------------------------------------------------------
# Banjo tuning
# ---------------------------------------------------------------------------

def test_standard_banjo_open_g_tuning():
    config = get_standard_configuration(InstrumentType.BANJO)

    expected = {
        5: ("G", 4),
        4: ("D", 3),
        3: ("G", 3),
        2: ("B", 3),
        1: ("D", 4),
    }

    for string_number, (note, octave) in expected.items():
        string = config.get_string(string_number)

        assert (string.note, string.octave) == (note, octave)


def test_banjo_fifth_string_is_marked_short():
    config = get_standard_configuration(InstrumentType.BANJO)

    assert config.get_string(5).is_short is True

    for string in config.strings:
        if string.string_number != 5:
            assert string.is_short is False


# ---------------------------------------------------------------------------
# Note and frequency calculations
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "note, octave, expected_midi",
    [
        ("C", 4, 60),
        ("A", 4, 69),
        ("E", 2, 40),
        ("B", 0, 23),
        ("F#", 2, 42),
        ("Bb", 3, 58),
    ],
)
def test_note_to_midi_number(note, octave, expected_midi):
    assert note_to_midi_number(note, octave) == expected_midi


def test_a4_frequency_is_440_hz():
    assert note_to_frequency("A", 4) == pytest.approx(440.0)


def test_octave_doubles_frequency():
    lower = note_to_frequency("A", 3)
    higher = note_to_frequency("A", 4)

    assert higher == pytest.approx(lower * 2)


def test_enharmonic_notes_have_same_frequency():
    assert note_to_frequency("C#", 4) == pytest.approx(
        note_to_frequency("Db", 4)
    )


def test_double_accidentals_are_supported():
    assert note_to_midi_number("C##", 4) == 62
    assert note_to_midi_number("Ebb", 4) == 62


# ---------------------------------------------------------------------------
# Custom configurations
# ---------------------------------------------------------------------------

def test_create_custom_guitar_tuning():
    config = create_custom_configuration(
        InstrumentType.GUITAR,
        [
            TuningString(6, "D", 2),
            TuningString(5, "A", 2),
            TuningString(4, "D", 3),
            TuningString(3, "G", 3),
            TuningString(2, "A", 3),
            TuningString(1, "D", 4),
        ],
    )

    assert config.instrument_type == InstrumentType.GUITAR
    assert config.string_count == 6
    assert config.tuning_name == "Custom"
    assert config.is_custom is True

    assert config.get_string(6).note_name == "D2"
    assert config.get_string(1).note_name == "D4"


def test_custom_configuration_infers_string_count():
    config = create_custom_configuration(
        InstrumentType.BASS,
        [
            TuningString(5, "B", 0),
            TuningString(4, "E", 1),
            TuningString(3, "A", 1),
            TuningString(2, "D", 2),
            TuningString(1, "G", 2),
        ],
    )

    assert config.string_count == 5
    assert config.get_string(5).note_name == "B0"


def test_custom_tuning_strings_are_sorted_by_physical_number():
    config = create_custom_configuration(
        InstrumentType.GUITAR,
        [
            TuningString(1, "E", 4),
            TuningString(3, "G", 3),
            TuningString(2, "B", 3),
        ],
    )

    assert [
        string.string_number for string in config.strings
    ] == [3, 2, 1]


def test_custom_configuration_can_use_flat_spellings():
    config = create_custom_configuration(
        InstrumentType.GUITAR,
        [
            TuningString(1, "Eb", 4),
        ],
    )

    assert config.get_string(1).note_name == "Eb4"


# ---------------------------------------------------------------------------
# Configuration validation
# ---------------------------------------------------------------------------

def test_invalid_note_is_rejected():
    with pytest.raises(ValueError):
        TuningString(1, "H", 4)


def test_invalid_string_number_is_rejected():
    with pytest.raises(ValueError):
        TuningString(0, "E", 4)


def test_invalid_octave_type_is_rejected():
    with pytest.raises(TypeError):
        TuningString(1, "E", 4.5)


def test_boolean_string_number_is_rejected():
    with pytest.raises(ValueError):
        TuningString(True, "E", 4)


def test_configuration_rejects_wrong_string_count():
    with pytest.raises(ValueError):
        InstrumentConfiguration(
            instrument_type=InstrumentType.GUITAR,
            string_count=2,
            tuning_name="Custom",
            strings=(
                TuningString(1, "E", 4),
            ),
        )


def test_configuration_rejects_duplicate_string_numbers():
    with pytest.raises(ValueError):
        InstrumentConfiguration(
            instrument_type=InstrumentType.GUITAR,
            string_count=2,
            tuning_name="Custom",
            strings=(
                TuningString(1, "E", 4),
                TuningString(1, "B", 3),
            ),
        )


def test_configuration_rejects_missing_string_numbers():
    with pytest.raises(ValueError):
        InstrumentConfiguration(
            instrument_type=InstrumentType.GUITAR,
            string_count=2,
            tuning_name="Custom",
            strings=(
                TuningString(1, "E", 4),
                TuningString(3, "G", 3),
            ),
        )


def test_configuration_rejects_empty_tuning_name():
    with pytest.raises(ValueError):
        InstrumentConfiguration(
            instrument_type=InstrumentType.GUITAR,
            string_count=1,
            tuning_name=" ",
            strings=(
                TuningString(1, "E", 4),
            ),
        )


def test_configuration_rejects_invalid_string_count():
    with pytest.raises(ValueError):
        InstrumentConfiguration(
            instrument_type=InstrumentType.GUITAR,
            string_count=13,
            tuning_name="Custom",
            strings=(),
        )


def test_get_string_rejects_nonexistent_string():
    config = get_standard_configuration(InstrumentType.GUITAR)

    with pytest.raises(ValueError):
        config.get_string(7)


def test_invalid_instrument_is_rejected():
    with pytest.raises(ValueError):
        get_standard_configuration("Mandolin")


# ---------------------------------------------------------------------------
# Serialization
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "instrument",
    list(InstrumentType),
)
def test_standard_configuration_serialization_roundtrip(instrument):
    original = get_standard_configuration(instrument)

    serialized = original.to_dict()
    restored = InstrumentConfiguration.from_dict(serialized)

    assert restored == original


def test_custom_configuration_serialization_roundtrip():
    original = create_custom_configuration(
        InstrumentType.GUITAR,
        [
            TuningString(6, "D", 2),
            TuningString(5, "A", 2),
            TuningString(4, "D", 3),
            TuningString(3, "G", 3),
            TuningString(2, "A", 3),
            TuningString(1, "D", 4),
        ],
    )

    restored = InstrumentConfiguration.from_dict(original.to_dict())

    assert restored == original


def test_serialization_preserves_short_string():
    original = get_standard_configuration(InstrumentType.BANJO)

    restored = InstrumentConfiguration.from_dict(original.to_dict())

    assert restored.get_string(5).is_short is True


def test_from_dict_rejects_missing_fields():
    with pytest.raises(ValueError):
        InstrumentConfiguration.from_dict({
            "instrument_type": "Guitar",
            "string_count": 6,
        })

# ---------------------------------------------------------------------------
# Fret count
# ---------------------------------------------------------------------------

def test_standard_instruments_default_to_22_frets():
    for instrument in InstrumentType:
        config = get_standard_configuration(instrument)
        assert config.fret_count == 22


@pytest.mark.parametrize("fret_count", [19, 22, 24, 27])
def test_custom_configuration_supports_different_fret_counts(fret_count):
    config = create_custom_configuration(
        InstrumentType.GUITAR,
        [
            TuningString(1, "E", 4),
        ],
        fret_count=fret_count,
    )

    assert config.fret_count == fret_count


def test_configuration_rejects_invalid_fret_count():
    with pytest.raises(ValueError):
        InstrumentConfiguration(
            instrument_type=InstrumentType.GUITAR,
            string_count=1,
            tuning_name="Custom",
            strings=(TuningString(1, "E", 4),),
            fret_count=0,
        )


def test_configuration_rejects_boolean_fret_count():
    with pytest.raises(ValueError):
        InstrumentConfiguration(
            instrument_type=InstrumentType.GUITAR,
            string_count=1,
            tuning_name="Custom",
            strings=(TuningString(1, "E", 4),),
            fret_count=True,
        )


def test_old_configuration_data_defaults_to_22_frets():
    old_data = {
        "instrument_type": "Guitar",
        "string_count": 1,
        "tuning_name": "Custom",
        "strings": [
            {
                "string_number": 1,
                "note": "E",
                "octave": 4,
            }
        ],
    }

    config = InstrumentConfiguration.from_dict(old_data)

    assert config.fret_count == 22


def test_serialization_preserves_custom_fret_count():
    original = create_custom_configuration(
        InstrumentType.GUITAR,
        [TuningString(1, "E", 4)],
        fret_count=24,
    )

    restored = InstrumentConfiguration.from_dict(original.to_dict())

    assert restored.fret_count == 24
