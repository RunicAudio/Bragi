"""
src/ui/components/modals/instrument_modal.py
============================================
Instrument selection and custom tuning configuration modal.
"""

import flet as ft

from core.app_state import AppState
from domain.instrument_definitions import (
    MAX_STRING_COUNT,
    MIN_STRING_COUNT,
    InstrumentConfiguration,
    InstrumentType,
    TuningString,
    get_available_instruments,
    get_standard_configuration,
)


class InstrumentModal(ft.AlertDialog):
    """Configure the active player's instrument and string tuning."""

    def __init__(self) -> None:
        self.app_state = AppState.get_instance()

        # Start with the active player's saved configuration.
        self.configuration = self.app_state.instrument_configuration

        self.instrument_type = self.configuration.instrument_type
        self.string_count = self.configuration.string_count
        self.tuning_name = self.configuration.tuning_name

        self.strings = {
            string.string_number: string
            for string in self.configuration.strings
        }

        self.error_text = ft.Text(
            "",
            color=ft.Colors.RED_300,
            size=12,
        )

        self.instrument_dropdown = ft.Dropdown(
            label="Instrument",
            width=300,
            value=self.instrument_type.value,
            options=[
                ft.DropdownOption(
                    key=name,
                    text=name,
                )
                for name in get_available_instruments()
            ],
            on_select=self._on_instrument_changed,
        )

        self.string_count_dropdown = ft.Dropdown(
            label="Number of Strings",
            width=300,
            value=str(self.string_count),
            options=[
                ft.DropdownOption(
                    key=str(count),
                    text=str(count),
                )
                for count in range(
                    MIN_STRING_COUNT,
                    MAX_STRING_COUNT + 1,
                )
            ],
            on_select=self._on_string_count_changed,
        )

        self.tuning_mode = ft.RadioGroup(
            content=ft.Row(
                controls=[
                    ft.Radio(
                        value="standard",
                        label="Standard",
                    ),
                    ft.Radio(
                        value="custom",
                        label="Custom",
                    ),
                ],
                spacing=16,
            ),
            value=(
                "custom"
                if self.configuration.is_custom
                else "standard"
            ),
            on_change=self._on_tuning_mode_changed,
        )

        self.string_editor = ft.Column(
            controls=[],
            spacing=8,
            scroll=ft.ScrollMode.AUTO,
        )

        self._refresh_string_editor()

        super().__init__(
            modal=True,
            title=ft.Row(
                controls=[
                    ft.Icon(
                        ft.Icons.MUSIC_NOTE,
                        color=ft.Colors.AMBER_300,
                    ),
                    ft.Text(
                        "Instrument & Tuning",
                        weight=ft.FontWeight.BOLD,
                    ),
                ],
                spacing=8,
            ),
            content=ft.Container(
                width=440,
                content=ft.Column(
                    controls=[
                        self.instrument_dropdown,
                        self.string_count_dropdown,
                        ft.Divider(),
                        ft.Text(
                            "Tuning Configuration",
                            weight=ft.FontWeight.BOLD,
                        ),
                        self.tuning_mode,
                        self.string_editor,
                        self.error_text,
                    ],
                    spacing=12,
                    tight=True,
                    scroll=ft.ScrollMode.AUTO,
                ),
                padding=12,
            ),
            actions=[
                ft.Button(
                    content=ft.Text("Cancel"),
                    on_click=self._close,
                ),
                ft.Button(
                    content=ft.Text("Save Configuration"),
                    icon=ft.Icons.SAVE,
                    on_click=self._save,
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )

    def _on_instrument_changed(
        self,
        e: ft.ControlEvent,
    ) -> None:
        """Load the selected instrument's standard tuning."""

        try:
            selected_type = InstrumentType(e.control.value)

            standard = get_standard_configuration(selected_type)

            self.instrument_type = selected_type
            self.string_count = standard.string_count
            self.tuning_name = standard.tuning_name

            self.strings = {
                string.string_number: string
                for string in standard.strings
            }

            self.string_count_dropdown.value = str(
                self.string_count
            )

            self.tuning_mode.value = "standard"

            self.error_text.value = ""

            self._refresh_string_editor()
            self.update()

        except (ValueError, TypeError) as exc:
            self.error_text.value = str(exc)
            self.update()

    def _on_string_count_changed(
        self,
        e: ft.ControlEvent,
    ) -> None:
        """Adjust the number of physical strings."""

        try:
            new_count = int(e.control.value)

            if not MIN_STRING_COUNT <= new_count <= MAX_STRING_COUNT:
                raise ValueError("Invalid string count.")

            standard = get_standard_configuration(
                self.instrument_type
            )

            new_strings = {}

            for number in range(new_count, 0, -1):
                if number in self.strings:
                    new_strings[number] = self.strings[number]

                elif number <= standard.string_count:
                    new_strings[number] = standard.get_string(number)

                else:
                    # Use the nearest existing open-string pitch
                    # as a provisional value for an additional string.
                    nearest = min(
                        self.strings.values(),
                        key=lambda string: abs(
                            string.string_number - number
                        ),
                    )

                    new_strings[number] = TuningString(
                        string_number=number,
                        note=nearest.note,
                        octave=nearest.octave,
                    )

            self.string_count = new_count
            self.strings = new_strings

            self.tuning_name = "Custom"
            self.tuning_mode.value = "custom"

            self.error_text.value = ""

            self._refresh_string_editor()
            self.update()

        except (ValueError, TypeError) as exc:
            self.error_text.value = str(exc)
            self.update()

    def _on_tuning_mode_changed(
        self,
        e: ft.ControlEvent,
    ) -> None:
        """Switch between standard and custom tuning."""

        if e.control.value == "standard":
            standard = get_standard_configuration(
                self.instrument_type
            )

            if self.string_count != standard.string_count:
                self.error_text.value = (
                    "Standard tuning requires "
                    f"{standard.string_count} strings."
                )
                self.tuning_mode.value = "custom"
                self.update()
                return

            self.strings = {
                string.string_number: string
                for string in standard.strings
            }

            self.tuning_name = standard.tuning_name

        else:
            self.tuning_name = "Custom"

        self.error_text.value = ""

        self._refresh_string_editor()
        self.update()

    def _refresh_string_editor(self) -> None:
        """Rebuild the individual string tuning controls."""

        self.string_fields = {}
        rows = []

        is_custom = self.tuning_mode.value == "custom"

        for number in range(self.string_count, 0, -1):
            tuning_string = self.strings[number]

            note_field = ft.TextField(
                label="Note",
                value=tuning_string.note,
                width=110,
                disabled=not is_custom,
                capitalization=ft.TextCapitalization.CHARACTERS,
                max_length=3,
            )

            octave_field = ft.TextField(
                label="Octave",
                value=str(tuning_string.octave),
                width=85,
                disabled=not is_custom,
                keyboard_type=ft.KeyboardType.NUMBER,
                max_length=2,
            )

            self.string_fields[number] = (
                note_field,
                octave_field,
            )

            rows.append(
                ft.Row(
                    controls=[
                        ft.Container(
                            content=ft.Text(
                                f"String {number}",
                                weight=ft.FontWeight.BOLD,
                            ),
                            width=90,
                        ),
                        note_field,
                        octave_field,
                    ],
                    spacing=10,
                )
            )

        self.string_editor.controls = rows

    def _save(
        self,
        e: ft.ControlEvent,
    ) -> None:
        """Validate and save the active player's configuration."""

        try:
            updated_strings = []

            for number in range(self.string_count, 0, -1):
                note_field, octave_field = self.string_fields[number]

                note = note_field.value.strip().upper()
                octave = int(octave_field.value.strip())

                existing_string = self.strings[number]

                updated_strings.append(
                    TuningString(
                        string_number=number,
                        note=note,
                        octave=octave,
                        is_short=existing_string.is_short,
                    )
                )

            configuration = InstrumentConfiguration(
                instrument_type=self.instrument_type,
                string_count=self.string_count,
                tuning_name=self.tuning_name,
                strings=tuple(updated_strings),
            )

            self.app_state.set_instrument_configuration(
                configuration
            )

            self.configuration = configuration
            self._close(e)

        except (ValueError, TypeError, AttributeError) as exc:
            self.error_text.value = str(exc)
            self.update()

    def _close(
        self,
        e: ft.ControlEvent = None,
    ) -> None:
        """Close the instrument configuration modal."""

        if self.page is not None:
            self.page.pop_dialog()
