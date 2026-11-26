"""
src/domain/instrument_definitions.py
====================================
Instrument definitions, standard tunings, and custom tuning configuration.

String numbers follow physical instrument numbering:
- Guitar: 6 is the lowest string; 1 is the highest.
- Bass: 4 is the lowest string; 1 is the highest.
- Ukulele: 4 is the top string; 1 is the bottom string.
- Banjo: 5 is the short drone string.

Tunings are not sorted by pitch. This preserves re-entrant tunings.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any

from domain.note_spelling import parse_note


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

A4_FREQUENCY = 440.0
A4_MIDI_NUMBER = 69

MIN_STRING_COUNT = 1
MAX_STRING_COUNT = 12


# ---------------------------------------------------------------------------
# Instrument types
# ---------------------------------------------------------------------------

class InstrumentType(str, Enum):
    GUITAR = "Guitar"
    BASS = "Bass"
    UKULELE = "Ukulele"
    BARITONE_UKULELE = "Baritone Ukulele"
    BANJO = "Banjo"


# ---------------------------------------------------------------------------
# Note and frequency utilities
# ---------------------------------------------------------------------------

def note_to_midi_number(note: str, octave: int) -> int:
    """
    Convert a written note and octave into its MIDI note number.

    MIDI note 69 is A4 (440 Hz).
    Supports the note spellings accepted by note_spelling.parse_note().
    """

    if not isinstance(octave, int) or isinstance(octave, bool):
        raise TypeError("Octave must be an integer.")

    spelled_note = parse_note(note)

    return (
        (octave + 1) * 12
        + spelled_note.pitch_class
    )


def note_to_frequency(note: str, octave: int) -> float:
    """Convert a written note and octave into frequency in Hz."""

    midi_number = note_to_midi_number(note, octave)

    return A4_FREQUENCY * (
        2 ** ((midi_number - A4_MIDI_NUMBER) / 12)
    )


# ---------------------------------------------------------------------------
# Individual string configuration
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class TuningString:
    """
    Configuration for one physical instrument string.

    Example:
        TuningString(
            string_number=6,
            note="E",
            octave=2,
        )
    """

    string_number: int
    note: str
    octave: int
    is_short: bool = False

    def __post_init__(self) -> None:
        if (
            not isinstance(self.string_number, int)
            or isinstance(self.string_number, bool)
            or self.string_number < 1
        ):
            raise ValueError("String number must be a positive integer.")

        if not isinstance(self.octave, int) or isinstance(self.octave, bool):
            raise TypeError("String octave must be an integer.")

        if not isinstance(self.is_short, bool):
            raise TypeError("is_short must be a boolean.")

        # Validate the note spelling immediately.
        parse_note(self.note)

    @property
    def note_name(self) -> str:
        """Return the complete note name, including octave."""

        return f"{self.note}{self.octave}"

    @property
    def midi_number(self) -> int:
        """Return the MIDI note number for this string."""

        return note_to_midi_number(self.note, self.octave)

    @property
    def frequency(self) -> float:
        """Return the open-string frequency in Hz."""

        return note_to_frequency(self.note, self.octave)


# ---------------------------------------------------------------------------
# Complete instrument configuration
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class InstrumentConfiguration:
    """
    Complete tuning configuration for an instrument.

    Strings must contain exactly one entry for every physical string
    number from 1 through string_count.

    The stored order is descending physical string number.
    """

    instrument_type: InstrumentType
    string_count: int
    tuning_name: str
    strings: tuple[TuningString, ...]

    def __post_init__(self) -> None:
        # Allow construction using either an enum or its string value.
        try:
            instrument_type = InstrumentType(self.instrument_type)
        except ValueError as exc:
            raise ValueError(
                f"Unsupported instrument type: {self.instrument_type}"
            ) from exc

        object.__setattr__(self, "instrument_type", instrument_type)

        if (
            not isinstance(self.string_count, int)
            or isinstance(self.string_count, bool)
        ):
            raise TypeError("String count must be an integer.")

        if not MIN_STRING_COUNT <= self.string_count <= MAX_STRING_COUNT:
            raise ValueError(
                f"String count must be between "
                f"{MIN_STRING_COUNT} and {MAX_STRING_COUNT}."
            )

        if not isinstance(self.tuning_name, str) or not self.tuning_name.strip():
            raise ValueError("Tuning name cannot be empty.")

        # Normalize strings to an immutable tuple.
        normalized_strings = tuple(self.strings)

        if not all(isinstance(s, TuningString) for s in normalized_strings):
            raise TypeError("Every string must be a TuningString instance.")

        if len(normalized_strings) != self.string_count:
            raise ValueError(
                f"Expected {self.string_count} strings, "
                f"received {len(normalized_strings)}."
            )

        string_numbers = [s.string_number for s in normalized_strings]

        expected_numbers = set(range(1, self.string_count + 1))

        if set(string_numbers) != expected_numbers:
            raise ValueError(
                "String numbers must contain every physical string number "
                f"from 1 through {self.string_count}, without duplicates."
            )

        # Always store strings in physical order: highest number first.
        normalized_strings = tuple(
            sorted(
                normalized_strings,
                key=lambda string: string.string_number,
                reverse=True,
            )
        )

        object.__setattr__(self, "strings", normalized_strings)

    @property
    def is_custom(self) -> bool:
        """Whether this configuration represents a custom tuning."""

        return self.tuning_name.strip().lower() == "custom"

    def get_string(self, string_number: int) -> TuningString:
        """Retrieve a string by its physical string number."""

        for string in self.strings:
            if string.string_number == string_number:
                return string

        raise ValueError(
            f"String {string_number} does not exist on this instrument."
        )

    def get_frequencies(self) -> dict[int, float]:
        """Return open-string frequencies indexed by physical string number."""

        return {
            string.string_number: string.frequency
            for string in self.strings
        }

    def to_dict(self) -> dict[str, Any]:
        """Convert the configuration into a JSON-serializable dictionary."""

        return {
            "instrument_type": self.instrument_type.value,
            "string_count": self.string_count,
            "tuning_name": self.tuning_name,
            "strings": [
                {
                    "string_number": string.string_number,
                    "note": string.note,
                    "octave": string.octave,
                    "is_short": string.is_short,
                }
                for string in self.strings
            ],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "InstrumentConfiguration":
        """Reconstruct a configuration from a serialized dictionary."""

        if not isinstance(data, dict):
            raise TypeError("Configuration data must be a dictionary.")

        required_fields = {
            "instrument_type",
            "string_count",
            "tuning_name",
            "strings",
        }

        missing_fields = required_fields - data.keys()

        if missing_fields:
            raise ValueError(
                f"Missing configuration fields: {sorted(missing_fields)}"
            )

        strings = tuple(
            TuningString(
                string_number=item["string_number"],
                note=item["note"],
                octave=item["octave"],
                is_short=item.get("is_short", False),
            )
            for item in data["strings"]
        )

        return cls(
            instrument_type=InstrumentType(data["instrument_type"]),
            string_count=data["string_count"],
            tuning_name=data["tuning_name"],
            strings=strings,
        )


# ---------------------------------------------------------------------------
# Standard instrument tunings
# ---------------------------------------------------------------------------

STANDARD_TUNINGS: dict[InstrumentType, InstrumentConfiguration] = {

    InstrumentType.GUITAR: InstrumentConfiguration(
        instrument_type=InstrumentType.GUITAR,
        string_count=6,
        tuning_name="Standard",
        strings=(
            TuningString(6, "E", 2),
            TuningString(5, "A", 2),
            TuningString(4, "D", 3),
            TuningString(3, "G", 3),
            TuningString(2, "B", 3),
            TuningString(1, "E", 4),
        ),
    ),

    InstrumentType.BASS: InstrumentConfiguration(
        instrument_type=InstrumentType.BASS,
        string_count=4,
        tuning_name="Standard",
        strings=(
            TuningString(4, "E", 1),
            TuningString(3, "A", 1),
            TuningString(2, "D", 2),
            TuningString(1, "G", 2),
        ),
    ),

    InstrumentType.UKULELE: InstrumentConfiguration(
        instrument_type=InstrumentType.UKULELE,
        string_count=4,
        tuning_name="Standard (High G)",
        strings=(
            TuningString(4, "G", 4),
            TuningString(3, "C", 4),
            TuningString(2, "E", 4),
            TuningString(1, "A", 4),
        ),
    ),

    InstrumentType.BARITONE_UKULELE: InstrumentConfiguration(
        instrument_type=InstrumentType.BARITONE_UKULELE,
        string_count=4,
        tuning_name="Standard",
        strings=(
            TuningString(4, "D", 3),
            TuningString(3, "G", 3),
            TuningString(2, "B", 3),
            TuningString(1, "E", 4),
        ),
    ),

    InstrumentType.BANJO: InstrumentConfiguration(
        instrument_type=InstrumentType.BANJO,
        string_count=5,
        tuning_name="Open G",
        strings=(
            TuningString(5, "G", 4, is_short=True),
            TuningString(4, "D", 3),
            TuningString(3, "G", 3),
            TuningString(2, "B", 3),
            TuningString(1, "D", 4),
        ),
    ),
}


# ---------------------------------------------------------------------------
# Public configuration helpers
# ---------------------------------------------------------------------------

def get_standard_configuration(
    instrument_type: InstrumentType | str,
) -> InstrumentConfiguration:
    """
    Return the standard tuning for an instrument.

    Each call returns a new immutable configuration instance.
    """

    try:
        instrument_type = InstrumentType(instrument_type)
    except ValueError as exc:
        raise ValueError(
            f"Unsupported instrument type: {instrument_type}"
        ) from exc

    if instrument_type not in STANDARD_TUNINGS:
        raise ValueError(
            f"No standard tuning defined for {instrument_type.value}."
        )

    return STANDARD_TUNINGS[instrument_type]


def get_available_instruments() -> tuple[str, ...]:
    """Return the supported instrument names for the UI."""

    return tuple(
        instrument.value
        for instrument in InstrumentType
    )


def create_custom_configuration(
    instrument_type: InstrumentType | str,
    strings: tuple[TuningString, ...] | list[TuningString],
) -> InstrumentConfiguration:
    """
    Create a custom tuning configuration.

    The string count is inferred from the supplied strings.
    Physical string numbers must still run from 1 through string_count.
    """

    try:
        instrument_type = InstrumentType(instrument_type)
    except ValueError as exc:
        raise ValueError(
            f"Unsupported instrument type: {instrument_type}"
        ) from exc

    strings = tuple(strings)

    return InstrumentConfiguration(
        instrument_type=instrument_type,
        string_count=len(strings),
        tuning_name="Custom",
        strings=strings,
    )
