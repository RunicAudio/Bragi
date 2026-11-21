"""
src/ui/components/modals/timing_modal.py
========================================
Modal dialog for configuring pitch hold duration directly bound to AppState.
"""

import flet as ft
from core.app_state import AppState


class TimingModal(ft.AlertDialog):
    """Modal dialog managing timing and practice pace preferences."""

    def __init__(self) -> None:
        self.app_state = AppState.get_instance()

        self.slider_speed = ft.Slider(
            min=0.2,
            max=2.0,
            divisions=18,
            value=self.app_state.hold_duration_sec,
            label="{value}s Hold",
            on_change=self._on_slider_changed,
        )

        super().__init__(
            title=ft.Row(
                controls=[
                    ft.Icon(ft.Icons.TIMER, color=ft.Colors.GREEN_300),
                    ft.Text("Auto-Advance Timing", weight=ft.FontWeight.BOLD),
                ],
                spacing=8,
            ),
            content=ft.Container(
                content=ft.Column(
                    controls=[
                        ft.Text(
                            "In-Tune Hold Duration (Seconds):",
                            size=13,
                            color=ft.Colors.with_opacity(0.7, ft.Colors.WHITE),
                        ),
                        self.slider_speed,
                    ],
                    tight=True,
                    spacing=12,
                ),
                width=360,
                padding=12,
            ),
            actions=[
                ft.Button(content=ft.Text("Done"), on_click=lambda e: self._close(e)),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )

    def _on_slider_changed(self, e: ft.ControlEvent) -> None:
        val = float(e.control.value)
        self.app_state.set_hold_duration(val)

    def _close(self, e: ft.ControlEvent) -> None:
        target_page = e.page or self.page
        if target_page is not None:
            if hasattr(target_page, "close"):
                target_page.close(self)
            else:
                self.open = False
                target_page.update()
