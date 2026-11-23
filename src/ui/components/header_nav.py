"""
src/ui/components/header_nav.py
===============================
In-line top header bar with persistent view feature icons and modal triggers.
"""

from typing import Callable
import flet as ft

from core.app_state import ActiveViewMode, AppState


class HeaderNav(ft.Container):
    """In-line header navigation bar featuring icon buttons and modal action triggers."""

    def __init__(
        self,
        on_open_filter: Callable[[ft.ControlEvent], None],
        on_open_instrument: Callable[[ft.ControlEvent], None],
        on_open_timing: Callable[[ft.ControlEvent], None],
    ) -> None:
        super().__init__()
        self.app_state = AppState.get_instance()

        self.on_open_filter = on_open_filter
        self.on_open_instrument = on_open_instrument
        self.on_open_timing = on_open_timing

        self.padding = ft.Padding.symmetric(horizontal=16, vertical=8)
        self.bgcolor = ft.Colors.with_opacity(0.85, "#1E1E2E")
        self.border_radius = 12

        self.btn_trainer = self._make_nav_btn("🎯 Trainer", ActiveViewMode.TRAINER)
        self.btn_tuner = self._make_nav_btn("🎛️ Tuner", ActiveViewMode.TUNER)
        self.btn_ear = self._make_nav_btn("🎧 Ear Training", ActiveViewMode.EAR_TRAINING)
        self.btn_analytics = self._make_nav_btn("📊 Analytics", ActiveViewMode.ANALYTICS)

        btn_filter = ft.IconButton(
            icon=ft.Icons.TUNE,
            icon_color=ft.Colors.CYAN_300,
            tooltip="Practice Filters & Modes",
            on_click=lambda e: self.on_open_filter(e),
        )
        btn_instrument = ft.IconButton(
            icon=ft.Icons.MIC,
            icon_color=ft.Colors.AMBER_300,
            tooltip="Audio Device & Input Setup",
            on_click=lambda e: self.on_open_instrument(e),
        )
        btn_timing = ft.IconButton(
            icon=ft.Icons.TIMER,
            icon_color=ft.Colors.GREEN_300,
            tooltip="Timer & Auto-Advance",
            on_click=lambda e: self.on_open_timing(e),
        )

        self.content = ft.Row(
            controls=[
                ft.Row(
                    controls=[
                        ft.Image(src="logo.png", width=28, height=28, error_content=ft.Icon(ft.Icons.SPEAKER_GROUP)),
                        ft.Text("BRAGI", size=20, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
                    ],
                    spacing=8,
                ),
                ft.VerticalDivider(width=1, color=ft.Colors.with_opacity(0.24, ft.Colors.WHITE)),
                ft.Row(
                    controls=[self.btn_trainer, self.btn_tuner, self.btn_ear, self.btn_analytics],
                    spacing=4,
                ),
                ft.Container(expand=True),
                ft.Row(
                    controls=[btn_filter, btn_instrument, btn_timing],
                    spacing=4,
                ),
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )

        self._update_button_styles()
        self.app_state.subscribe_view(self._on_view_changed)

    def _make_nav_btn(self, label: str, view_mode: ActiveViewMode) -> ft.Control:
        return ft.Button(
            content=ft.Text(label),
            on_click=lambda _: self.app_state.set_view(view_mode),
        )

    def _update_button_styles(self) -> None:
        curr = self.app_state.current_view
        btns = [
            (self.btn_trainer, ActiveViewMode.TRAINER),
            (self.btn_tuner, ActiveViewMode.TUNER),
            (self.btn_ear, ActiveViewMode.EAR_TRAINING),
            (self.btn_analytics, ActiveViewMode.ANALYTICS),
        ]
        for btn, mode in btns:
            is_active = (mode == curr)
            btn.style = ft.ButtonStyle(
                color=ft.Colors.CYAN_400 if is_active else ft.Colors.with_opacity(0.7, ft.Colors.WHITE),
                bgcolor=ft.Colors.with_opacity(0.2, ft.Colors.CYAN_700) if is_active else ft.Colors.TRANSPARENT,
                shape=ft.RoundedRectangleBorder(radius=8),
            )

    def _on_view_changed(self) -> None:
        if self.page is not None:
            try:
                self._update_button_styles()
                self.update()
            except Exception:
                pass
