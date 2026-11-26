"""
src/ui/views/tuner_view.py
==========================
Chromatic tuner subview featuring a dynamic needle dial and background color transitions.
"""

import flet as ft
from core.app_state import ActiveViewMode, AppState


class TunerView(ft.Container):
    """Chromatic tuner dial with dynamic color changing gauge background."""

    def __init__(self) -> None:
        super().__init__()
        self.expand = True
        self.padding = 24
        self.alignment = ft.Alignment.CENTER
        self.app_state = AppState.get_instance()

        # Persistent dynamic controls
        self.txt_note = ft.Text("--", size=72, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE)
        self.txt_cents = ft.Text("--", size=20, color=ft.Colors.with_opacity(0.9, ft.Colors.WHITE))
        self.txt_status = ft.Text("PLAY A STRING", size=16, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE)
        self.needle_container = ft.Container(
            alignment=ft.Alignment(0, 0),
            content=ft.Container(width=6, height=36, bgcolor=ft.Colors.WHITE, border_radius=3),
        )

        self.gauge_container = ft.Container(
            content=ft.Column(
                controls=[
                    self.txt_note,
                    self.txt_cents,
                    ft.Container(
                        content=ft.Stack(
                            controls=[
                                ft.Container(
                                    alignment=ft.Alignment.CENTER,
                                    content=ft.VerticalDivider(
                                        width=2,
                                        color=ft.Colors.with_opacity(
                                            0.54, ft.Colors.WHITE
                                        ),
                                    ),
                                ),
                                self.needle_container,
                            ]
                        ),
                        width=280,
                        height=40,
                        bgcolor=ft.Colors.with_opacity(
                            0.38, ft.Colors.BLACK
                        ),
                        border_radius=20,
                    ),
                    self.txt_status,
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                alignment=ft.MainAxisAlignment.CENTER,
                spacing=16,
                tight=True,
            ),
            width=340,
            height=340,
            bgcolor=ft.Colors.with_opacity(0.6, "#2A2A3C"),
            border=ft.Border.all(4, ft.Colors.AMBER_400),
            border_radius=170,
            padding=28,
            alignment=ft.Alignment.CENTER,
        )

        self.content = ft.Column(
            controls=[
                ft.Text("CHROMATIC TUNER", size=18, weight=ft.FontWeight.BOLD, color=ft.Colors.CYAN_300),
                self.gauge_container,
            ],
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=24,
        )

        self.app_state.subscribe_pitch(self._on_pitch_changed)

    def _on_pitch_changed(self) -> None:
        if self.page is not None and self.app_state.current_view == ActiveViewMode.TUNER:
            live = self.app_state.live_pitch
            cents = live.cents_deviation

            if live.is_silent or live.note_name == "--":
                self.gauge_container.bgcolor = ft.Colors.with_opacity(0.6, "#2A2A3C")
                self.txt_status.value = "PLAY A STRING"
                self.txt_note.value = "--"
                self.txt_cents.value = "--"
                self.needle_container.alignment = ft.Alignment(0, 0)
            else:
                self.txt_note.value = live.note_name
                self.txt_cents.value = f"{cents:+.1f} Cents"
                if abs(cents) <= 5.0:
                    self.gauge_container.bgcolor = ft.Colors.with_opacity(0.85, ft.Colors.GREEN_800)
                    self.txt_status.value = "IN TUNE"
                elif abs(cents) <= 15.0:
                    self.gauge_container.bgcolor = ft.Colors.with_opacity(0.85, ft.Colors.AMBER_800)
                    self.txt_status.value = "CLOSE TO PITCH"
                else:
                    self.gauge_container.bgcolor = ft.Colors.with_opacity(0.85, ft.Colors.RED_800)
                    self.txt_status.value = "OUT OF TUNE"

                cents_clamped = max(-50.0, min(50.0, cents))
                needle_x = cents_clamped / 50.0
                self.needle_container.alignment = ft.Alignment(needle_x, 0)

            try:
                self.update()
            except Exception:
                pass
