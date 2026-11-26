"""
src/ui/views/home_view.py
=========================
Bragi home screen with circular navigation.
"""

import flet as ft

from core.app_state import ActiveViewMode, AppState


class HomeView(ft.Container):
    """Central Bragi hub with four circular navigation buttons."""

    def __init__(self) -> None:
        super().__init__()

        self.app_state = AppState.get_instance()
        self.expand = True
        self.alignment = ft.Alignment.CENTER
        self.padding = 16

        self.content = ft.Column(
            controls=[
                ft.Stack(
                    width=600,
                    height=600,
                    controls=[
                        # Outer circular outline.
                        ft.Container(
                            left=50,
                            top=50,
                            width=500,
                            height=500,
                            border=ft.Border.all(
                                3,
                                ft.Colors.AMBER_400,
                            ),
                            border_radius=250,
                            bgcolor=ft.Colors.with_opacity(
                                0.08,
                                "#282A36",
                            ),
                        ),

                        # Trainer — top.
                        self._build_nav_button(
                            "TRAINER",
                            ft.Icons.MUSIC_NOTE,
                            ActiveViewMode.TRAINER,
                            left=240,
                            top=0,
                        ),

                        # Tuner — right.
                        self._build_nav_button(
                            "TUNER",
                            ft.Icons.TUNE,
                            ActiveViewMode.TUNER,
                            left=480,
                            top=240,
                        ),

                        # Ear Training — bottom.
                        self._build_nav_button(
                            "EAR TRAINING",
                            ft.Icons.HEADPHONES,
                            ActiveViewMode.EAR_TRAINING,
                            left=240,
                            top=480,
                        ),

                        # Analytics — left.
                        self._build_nav_button(
                            "ANALYTICS",
                            ft.Icons.BAR_CHART,
                            ActiveViewMode.ANALYTICS,
                            left=0,
                            top=240,
                        ),

                        # Central Bragi hub.
                        ft.Container(
                            left=210,
                            top=210,
                            width=180,
                            height=180,
                            border=ft.Border.all(
                                4,
                                ft.Colors.AMBER_400,
                            ),
                            border_radius=90,
                            bgcolor="#282A36",
                            alignment=ft.Alignment.CENTER,
                            content=ft.Column(
                                controls=[
                                    ft.Image(
                                        src="logo.png",
                                        width=64,
                                        height=64,
                                        error_content=ft.Icon(
                                            ft.Icons.MUSIC_NOTE,
                                            size=48,
                                            color=ft.Colors.AMBER_400,
                                        ),
                                    ),
                                    ft.Text(
                                        "BRAGI",
                                        size=25,
                                        weight=ft.FontWeight.BOLD,
                                        color=ft.Colors.WHITE,
                                    ),
                                ],
                                alignment=ft.MainAxisAlignment.CENTER,
                                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                                spacing=6,
                                tight=True,
                            ),
                        ),
                    ],
                ),
            ],
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            expand=True,
        )

    def _build_nav_button(
        self,
        label: str,
        icon: str,
        view_mode: ActiveViewMode,
        left: float,
        top: float,
    ) -> ft.Control:
        """Create a circular button positioned around the central hub."""

        return ft.Container(
            left=left,
            top=top,
            width=120,
            height=120,
            border=ft.Border.all(
                2,
                ft.Colors.AMBER_400,
            ),
            border_radius=60,
            bgcolor="#343449",
            alignment=ft.Alignment.CENTER,
            ink=True,
            on_click=lambda e: self.app_state.set_view(view_mode),
            content=ft.Column(
                controls=[
                    ft.Icon(
                        icon,
                        size=32,
                        color=ft.Colors.CYAN_300,
                    ),
                    ft.Text(
                        label,
                        size=12,
                        weight=ft.FontWeight.BOLD,
                        color=ft.Colors.WHITE,
                        text_align=ft.TextAlign.CENTER,
                    ),
                ],
                alignment=ft.MainAxisAlignment.CENTER,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=8,
                tight=True,
            ),
        )
