"""
src/ui/views/analytics_view.py
==============================
Analytics subview displaying unlocked badges, total XP, user level,
practice accuracy stats, and Hero Boss Challenge gauntlet progress.
"""

import flet as ft

from core.app_state import AppState
from domain.gamification_policy import SYSTEM_BADGES, MasteryTier


class AnalyticsView(ft.Container):
    """Analytics dashboard displaying real database metrics and badge achievements."""

    def __init__(self) -> None:
        super().__init__()
        self.expand = True
        self.padding = 24
        self.app_state = AppState.get_instance()

        self.content = self._build_content()
        self.app_state.subscribe_gamification(self._on_gamification_changed)

    def _build_content(self) -> ft.Control:
        profile = self.app_state.user_profile
        boss = self.app_state.hero_boss
        unlocked_ids = self.app_state.unlocked_badge_ids
        summary = self.app_state.db.get_analytics_summary()

        badge_controls = []
        for badge in SYSTEM_BADGES:
            is_unlocked = badge.id in unlocked_ids
            icon_color = (
                ft.Colors.AMBER_400
                if (badge.tier == MasteryTier.HERO and is_unlocked)
                else (ft.Colors.CYAN_400 if is_unlocked else ft.Colors.GREY_600)
            )
            badge_controls.append(
                ft.Container(
                    content=ft.Column(
                        controls=[
                            ft.Icon(
                                ft.Icons.EMOJI_EVENTS if is_unlocked else ft.Icons.LOCK,
                                color=icon_color,
                                size=28,
                            ),
                            ft.Text(
                                badge.title,
                                size=12,
                                weight=ft.FontWeight.BOLD,
                                color=ft.Colors.WHITE if is_unlocked else ft.Colors.GREY_400,
                            ),
                            ft.Text(
                                badge.tier.value,
                                size=10,
                                color=ft.Colors.with_opacity(0.6, ft.Colors.WHITE if is_unlocked else ft.Colors.GREY_500),
                            ),
                        ],
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=4,
                    ),
                    bgcolor=ft.Colors.with_opacity(0.3 if is_unlocked else 0.1, "#1E1E2E"),
                    border_radius=10,
                    padding=8,
                    width=140,
                )
            )

        return ft.Column(
            controls=[
                ft.Row(
                    controls=[
                        ft.Text("ANALYTICS & PROGRESSION", size=18, weight=ft.FontWeight.BOLD, color=ft.Colors.CYAN_300),
                        ft.Text(f"Total XP: {profile.total_xp} | Level {profile.user_level}", size=14, color=ft.Colors.GREEN_400),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                ),
                ft.Row(
                    controls=[
                        ft.Text(f"Attempts: {summary.get('total_attempts', 0)}", color=ft.Colors.WHITE),
                        ft.Text(f"Accuracy: {summary.get('accuracy_percentage', 0.0)}%", color=ft.Colors.WHITE),
                        ft.Text(f"Avg Speed: {summary.get('avg_response_speed_sec', 0.0)}s", color=ft.Colors.WHITE),
                        ft.Text(f"Streak: {profile.current_streak} days", color=ft.Colors.AMBER_300),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_AROUND,
                ),
                ft.Container(
                    content=ft.Column(
                        controls=[
                            ft.Text("LEVEL 4 HERO LEVEL: FINAL BOSS CHALLENGE", size=16, weight=ft.FontWeight.BOLD, color=ft.Colors.AMBER_300),
                            ft.Text("Requirement: 50 Notes + 50 Chords + 50 Arpeggios in a row (< 2.0s each)", size=12, color=ft.Colors.with_opacity(0.7, ft.Colors.WHITE)),
                            ft.Row(
                                controls=[
                                    ft.Text(f"Notes: {boss.consecutive_notes_under_2s}/50", color=ft.Colors.WHITE),
                                    ft.Text(f"Chords: {boss.consecutive_chords_under_2s}/50", color=ft.Colors.WHITE),
                                    ft.Text(f"Arpeggios: {boss.consecutive_arpeggios_under_2s}/50", color=ft.Colors.WHITE),
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
                ft.Text(f"Badges Unlocked ({len(unlocked_ids)}/40):", size=14, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
                ft.Container(
                    content=ft.Row(controls=badge_controls, wrap=True, spacing=12),
                    expand=True,
                ),
            ],
            spacing=16,
        )

    def _on_gamification_changed(self) -> None:
        if self.page is not None:
            try:
                self.content = self._build_content()
                self.update()
            except Exception:
                pass
