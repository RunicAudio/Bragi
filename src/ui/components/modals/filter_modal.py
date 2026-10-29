"""
src/ui/components/modals/filter_modal.py
========================================
Modal dropdown dialog for selecting trainer submodes and chord filters.
"""

import flet as ft
from core.app_state import AppState, TrainerSubMode


class FilterModal(ft.AlertDialog):
    """Modal popup dialog for configuring practice modes and filters."""

    def __init__(self) -> None:
        self.app_state = AppState.get_instance()

        self.radio_mode = ft.RadioGroup(
            content=ft.Column(
                controls=[
                    ft.Radio(value=TrainerSubMode.SINGLE_NOTE.value, label="Single Note Auto-Advance"),
                    ft.Radio(value=TrainerSubMode.STRUMMED_CHORD.value, label="Strummed Chord Auto-Advance"),
                    ft.Radio(value=TrainerSubMode.ARPEGGIO_CHORD.value, label="Arpeggio Chord Auto-Advance"),
                ]
            ),
            value=self.app_state.trainer_mode.value,
            on_change=self._on_mode_selected,
        )

        super().__init__(
            title=ft.Text("Trainer Filters & Modes", weight=ft.FontWeight.BOLD),
            content=ft.Container(
                content=ft.Column(
                    controls=[
                        ft.Text("Select Practice Submode:", size=14, color=ft.Colors.with_opacity(0.7, ft.Colors.WHITE)),
                        self.radio_mode,
                    ],
                    tight=True,
                    spacing=12,
                ),
                width=360,
                padding=12,
            ),
            actions=[
                ft.Button(content=ft.Text("Close"), on_click=lambda e: self._close(e)),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )

    def _on_mode_selected(self, e: ft.ControlEvent) -> None:
        selected_mode = TrainerSubMode(e.control.value)
        self.app_state.set_trainer_mode(selected_mode)

    def _close(self, e: ft.ControlEvent) -> None:
        target_page = e.page or self.page
        if target_page is not None:
            if hasattr(target_page, "close"):
                target_page.close(self)
            else:
                self.open = False
                target_page.update()
