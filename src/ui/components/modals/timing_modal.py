"""
src/ui/components/modals/timing_modal.py
========================================
Modal dialog for configuring pitch hold duration and auto-advance delay.
"""

import flet as ft


class TimingModal(ft.AlertDialog):
    """Modal dialog managing timing and practice pace preferences."""

    def __init__(self) -> None:
        self.slider_speed = ft.Slider(
            min=0.2,
            max=2.0,
            divisions=18,
            value=0.8,
            label="{value}s Hold",
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
                        ft.Text("In-Tune Hold Duration (Seconds):", size=13, color=ft.Colors.with_opacity(0.7, ft.Colors.WHITE)),
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

    def _close(self, e: ft.ControlEvent) -> None:
        target_page = e.page or self.page
        if target_page is not None:
            if hasattr(target_page, "close"):
                target_page.close(self)
            else:
                self.open = False
                target_page.update()
