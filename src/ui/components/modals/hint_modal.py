"""
src/ui/components/modals/hint_modal.py
======================================
Progressive music theory hints and chord construction explanations.
"""

import flet as ft

from core.app_state import AppState, TrainerSubMode
from domain.chord_theory import explain_chord, CHORD_FORMULAS


class HintModal(ft.AlertDialog):
    """Dialog presenting progressive hints and complete theory explanations."""

    def __init__(self) -> None:
        self.app_state = AppState.get_instance()
        self.is_single_note = (
            self.app_state.trainer_mode == TrainerSubMode.SINGLE_NOTE
        )

        self._hint_index = 0
        self._chord_explanation = None

        if self.is_single_note:
            title_text = f"Hint: {self.app_state.target_note_name}"
            content = self._build_single_note_content()
            actions = [
                ft.Button(
                    content=ft.Text("Got It"),
                    on_click=self._close,
                )
            ]
        else:
            title_text = f"Hint: {self.app_state.target_chord_name}"

            root, quality = self._parse_chord_name(
                self.app_state.target_chord_name
            )
            self._chord_explanation = explain_chord(root, quality)

            content = self._build_chord_intro()
            actions = self._build_chord_actions()

        super().__init__(
            title=ft.Row(
                controls=[
                    ft.Icon(
                        ft.Icons.LIGHTBULB,
                        color=ft.Colors.AMBER_400,
                    ),
                    ft.Text(
                        title_text,
                        weight=ft.FontWeight.BOLD,
                    ),
                ],
                spacing=8,
            ),
            content=ft.Container(
                content=content,
                width=520,
                padding=12,
            ),
            actions=actions,
            actions_alignment=ft.MainAxisAlignment.END,
        )

    @staticmethod
    def _parse_chord_name(chord_name: str) -> tuple[str, str]:
        """Separate a generated chord name into its root and quality."""

        for quality in sorted(CHORD_FORMULAS, key=len, reverse=True):
            suffix = f" {quality}"

            if chord_name.endswith(suffix):
                root = chord_name[:-len(suffix)]
                return root, quality

        raise ValueError(f"Unsupported chord name: {chord_name}")

    def _build_single_note_content(self) -> ft.Control:
        explanation = (
            f"Target Note {self.app_state.target_note_name} is located on "
            f"String {self.app_state.target_string_num}. Find the note by "
            f"referencing fret position markers at Frets 3, 5, 7, 9, and 12."
        )

        return ft.Column(
            controls=[
                ft.Text(
                    "Theory Breakdown:",
                    size=14,
                    weight=ft.FontWeight.BOLD,
                    color=ft.Colors.CYAN_300,
                ),
                ft.Text(
                    explanation,
                    size=13,
                    color=ft.Colors.with_opacity(0.9, ft.Colors.WHITE),
                ),
            ],
            tight=True,
            spacing=10,
        )

    def _build_chord_intro(self) -> ft.Control:
        return ft.Column(
            controls=[
                ft.Text(
                    "Build Your Understanding",
                    size=16,
                    weight=ft.FontWeight.BOLD,
                    color=ft.Colors.CYAN_300,
                ),
                ft.Text(
                    f"Your target is {self._chord_explanation.chord_name}.",
                    size=14,
                ),
                ft.Text(
                    "Try to identify the chord's structure before revealing "
                    "the complete explanation.",
                    size=13,
                ),
                ft.Divider(),
                ft.Text(
                    "Choose how much help you need:",
                    size=13,
                    weight=ft.FontWeight.BOLD,
                ),
            ],
            tight=True,
            spacing=10,
        )

    def _build_chord_actions(self) -> list[ft.Control]:
        return [
            ft.Button(
                content=ft.Text("Guide Me"),
                icon=ft.Icons.LIGHTBULB_OUTLINE,
                on_click=self._show_next_hint,
            ),
            ft.Button(
                content=ft.Text("Show Me the Answer"),
                icon=ft.Icons.VISIBILITY,
                on_click=self._show_answer,
            ),
            ft.Button(
                content=ft.Text("Close"),
                on_click=self._close,
            ),
        ]

    def _show_next_hint(self, e: ft.ControlEvent) -> None:
        """Reveal one additional hint without showing the complete answer."""

        hints = self._chord_explanation.hints

        if self._hint_index >= len(hints):
            return

        visible_hints = [
            ft.Text(
                f"Hint {index + 1}",
                size=13,
                weight=ft.FontWeight.BOLD,
                color=ft.Colors.CYAN_300,
            )
            for index in range(self._hint_index + 1)
        ]

        for index, hint in enumerate(hints[:self._hint_index + 1]):
            visible_hints.append(
                ft.Text(
                    hint,
                    size=13,
                )
            )

        self._hint_index += 1

        if self._hint_index >= len(hints):
            button_label = "All Hints Shown"
            button_disabled = True
        else:
            button_label = "Next Hint"
            button_disabled = False

        self.content = ft.Container(
            content=ft.Column(
                controls=[
                    ft.Text(
                        "Guided Hints",
                        size=16,
                        weight=ft.FontWeight.BOLD,
                        color=ft.Colors.CYAN_300,
                    ),
                    *visible_hints,
                    ft.Divider(),
                    ft.Text(
                        "Use these clues to work out the chord before "
                        "revealing the answer.",
                        size=12,
                        italic=True,
                    ),
                ],
                tight=True,
                spacing=8,
                scroll=ft.ScrollMode.AUTO,
            ),
            width=520,
            padding=12,
        )

        self.actions = [
            ft.Button(
                content=ft.Text(button_label),
                icon=ft.Icons.LIGHTBULB_OUTLINE,
                on_click=self._show_next_hint,
                disabled=button_disabled,
            ),
            ft.Button(
                content=ft.Text("Show Me the Answer"),
                icon=ft.Icons.VISIBILITY,
                on_click=self._show_answer,
            ),
            ft.Button(
                content=ft.Text("Close"),
                on_click=self._close,
            ),
        ]

        self.update()

    def _show_answer(self, e: ft.ControlEvent) -> None:
        """Display the complete chord construction explanation."""

        explanation = self._chord_explanation

        formula = " – ".join(
            degree.replace("b", "♭")
            for degree in explanation.formula
        )

        tone_controls = []

        for tone in explanation.tones:
            formula_degree = tone.formula_degree.replace("b", "♭")

            if tone.scale_degree is not None:
                scale_degree = tone.scale_degree.replace("b", "♭")
                scale_description = (
                    f"{scale_degree} — {tone.scale_degree_name}"
                )
            else:
                scale_description = "Not assigned"

            tone_controls.append(
                ft.Container(
                    content=ft.Column(
                        controls=[
                            ft.Text(
                                tone.note_name,
                                size=16,
                                weight=ft.FontWeight.BOLD,
                                color=ft.Colors.CYAN_300,
                            ),
                            ft.Text(
                                f"Chord formula: {formula_degree}",
                                size=12,
                            ),
                            ft.Text(
                                f"Interval: {tone.interval_name}",
                                size=12,
                            ),
                            ft.Text(
                                f"Reference scale degree: {scale_description}",
                                size=12,
                            ),
                        ],
                        spacing=3,
                        tight=True,
                    ),
                    padding=8,
                    border=ft.Border.all(
                        1,
                        ft.Colors.with_opacity(0.25, ft.Colors.WHITE),
                    ),
                    border_radius=8,
                )
            )

        reference_text = (
            f"Reference context: {explanation.reference_context}"
            if explanation.reference_context
            else "Reference context: Root-relative intervals"
        )

        self.content = ft.Container(
            content=ft.Column(
                controls=[
                    ft.Text(
                        explanation.chord_name,
                        size=17,
                        weight=ft.FontWeight.BOLD,
                        color=ft.Colors.CYAN_300,
                    ),
                    ft.Text(
                        f"Chord formula: {formula}",
                        size=14,
                        weight=ft.FontWeight.BOLD,
                    ),
                    ft.Text(
                        reference_text,
                        size=12,
                        italic=True,
                    ),
                    ft.Divider(),
                    ft.Text(
                        "Chord Tones",
                        size=14,
                        weight=ft.FontWeight.BOLD,
                    ),
                    *tone_controls,
                    ft.Divider(),
                    ft.Text(
                        "Construction Explanation",
                        size=14,
                        weight=ft.FontWeight.BOLD,
                    ),
                    ft.Text(
                        explanation.construction_explanation,
                        size=13,
                    ),
                ],
                spacing=8,
                tight=True,
                scroll=ft.ScrollMode.AUTO,
            ),
            width=520,
            padding=12,
        )

        self.actions = [
            ft.Button(
                content=ft.Text("Close"),
                on_click=self._close,
            )
        ]

        self.update()

    def _close(self, e: ft.ControlEvent) -> None:
        target_page = e.page or self.page

        if target_page is not None:
            target_page.pop_dialog()
