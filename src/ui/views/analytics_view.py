"""
src/ui/views/analytics_view.py
==============================
Analytics subview displaying 40 badges across 3 tiers (Beginner, Intermediate, Advanced)
and tracking the Level 4 'Hero Level' Final Boss Challenge gauntlet.
"""

import flet as ft

from domain.gamification_policy import SYSTEM_BADGES, HeroBossProgress, MasteryTier


class AnalyticsView(ft.Container):
    """Analytics dashboard featuring badge achievements and the Final Boss Challenge."""

    def __init__(self) -> None:
        super().__init__()
        self.expand = True
        self.padding = 24
        self.boss_progress = HeroBossProgress()

        self.content = self._build_content()

    def _build_content(self) -> ft.Control:
        badge_controls = []
        for badge in SYSTEM_BADGES:
            icon_color = ft.Colors.AMBER_400 if badge.tier == MasteryTier.HERO else ft.Colors.CYAN_400
            badge_controls.append(
                ft.Container(
                    content=ft.Column(
                        controls=[
                            ft.Icon(ft.Icons.EMOJI_EVENTS, color=icon_color, size=28),
                            ft.Text(badge.title, size=12, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
                            ft.Text(badge.tier.value, size=10, color=ft.Colors.with_opacity(0.6, ft.Colors.WHITE)),
                        ],
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=4,
                    ),
                    bgcolor=ft.Colors.with_opacity(0.3, "#1E1E2E"),
                    border_radius=10,
                    padding=8,
                    width=140,
                )
            )

        return ft.Column(
            controls=[
                ft.Text("ANALYTICS & BADGES", size=18, weight=ft.FontWeight.BOLD, color=ft.Colors.CYAN_300),
                ft.Container(
                    content=ft.Column(
                        controls=[
                            ft.Text("LEVEL 4 HERO LEVEL: FINAL BOSS CHALLENGE", size=16, weight=ft.FontWeight.BOLD, color=ft.Colors.AMBER_300),
                            ft.Text("Requirement: 50 Notes + 50 Chords + 50 Arpeggios in a row (< 2.0s each)", size=12, color=ft.Colors.with_opacity(0.7, ft.Colors.WHITE)),
                            ft.Row(
                                controls=[
                                    ft.Text(f"Notes: {self.boss_progress.consecutive_notes_under_2s}/50", color=ft.Colors.WHITE),
                                    ft.Text(f"Chords: {self.boss_progress.consecutive_chords_under_2s}/50", color=ft.Colors.WHITE),
                                    ft.Text(f"Arpeggios: {self.boss_progress.consecutive_arpeggios_under_2s}/50", color=ft.Colors.WHITE),
                                ],
                                alignment=ft.MainAxisAlignment.SPACE_AROUND,
                            ),
                        ],
                        spacing=8,
                    ),
                    bgcolor=ft.Colors.with_opacity(0.85, "#382A4A"),
                    border_radius=12,
                    padding=16,
                ),
                ft.Text("Collected View Badges (40 Total):", size=14, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
                ft.Container(
                    content=ft.Row(controls=badge_controls, wrap=True, spacing=12),
                    expand=True,
                ),
            ],
            spacing=16,
        )
