"""
src/ui/components/modals/hint_modal.py
======================================
Fretboard mapping hint modal with target note highlights and music theory explanations.
"""

import flet as ft
from core.app_state import AppState, TrainerSubMode


class HintModal(ft.AlertDialog):
    """Modal dialog presenting theoretical explanations and physical fretboard landmarks."""

    def __init__(self) -> None:
        self.app_state = AppState.get_instance()

        title_text = f"Hint: {self.app_state.target_note_name}"
        if self.app_state.trainer_mode != TrainerSubMode.SINGLE_NOTE:
            title_text = f"Hint: {self.app_state.target_chord_name}"

        if self.app_state.trainer_mode == TrainerSubMode.SINGLE_NOTE:
            explanation = (
                f"Target Note {self.app_state.target_note_name} is located on String "
                f"{self.app_state.target_string_num}. Find the note by referencing "
                f"fret position markers at Frets 3, 5, 7, 9, and 12."
            )
        else:
            explanation = (
                f"Target Chord '{self.app_state.target_chord_name}' contains pitch classes "
                f"{sorted(list(self.app_state.target_chord_pcs))}. Strum or arpeggiate all "
                f"individual chord tones clearly."
            )

        super().__init__(
            title=ft.Row(
                controls=[
                    ft.Icon(ft.Icons.LIGHTBULB, color=ft.Colors.AMBER_400),
                    ft.Text(title_text, weight=ft.FontWeight.BOLD),
                ],
                spacing=8,
            ),
            content=ft.Container(
                content=ft.Column(
                    controls=[
                        ft.Text("Theory Breakdown:", size=14, weight=ft.FontWeight.BOLD, color=ft.Colors.CYAN_300),
                        ft.Text(explanation, size=13, color=ft.Colors.with_opacity(0.9, ft.Colors.WHITE)),
                    ],
                    tight=True,
                    spacing=10,
                ),
                width=400,
                padding=12,
            ),
            actions=[
                ft.Button(content=ft.Text("Got It"), on_click=lambda e: self._close(e)),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )

    def _close(self, e: ft.ControlEvent) -> None:
        target_page = e.page or self.page

        if target_page is not None:
            target_page.pop_dialog()
