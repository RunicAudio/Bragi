"""
src/ui/components/modals/player_modal.py
========================================
Player management modal for selecting and creating player profiles.
"""

import flet as ft

from core.app_state import AppState


class PlayerModal(ft.AlertDialog):
    """Modal for selecting existing players or creating a new player."""

    def __init__(self) -> None:
        self.app_state = AppState.get_instance()

        self.name_field = ft.TextField(
            label="Player Name",
            hint_text="Enter a name",
            autofocus=False,
            width=300,
            on_submit=self._create_player,
        )

        self.error_text = ft.Text(
            "",
            color=ft.Colors.RED_300,
            size=12,
        )

        self.player_list = ft.Column(
            controls=self._build_player_list(),
            spacing=8,
            tight=True,
        )

        super().__init__(
            modal=True,
            title=ft.Text(
                "Manage Players",
                weight=ft.FontWeight.BOLD,
            ),
            content=ft.Container(
                width=380,
                content=ft.Column(
                    controls=[
                        ft.Text(
                            "Select a Player",
                            size=14,
                            weight=ft.FontWeight.BOLD,
                        ),
                        self.player_list,
                        ft.Divider(),
                        ft.Text(
                            "Add New Player",
                            size=14,
                            weight=ft.FontWeight.BOLD,
                        ),
                        self.name_field,
                        self.error_text,
                        ft.Button(
                            content=ft.Text("Add Player"),
                            icon=ft.Icons.PERSON_ADD,
                            on_click=self._create_player,
                        ),
                    ],
                    spacing=12,
                    tight=True,
                    scroll=ft.ScrollMode.AUTO,
                ),
                padding=8,
            ),
            actions=[
                ft.Button(
                    content=ft.Text("Close"),
                    on_click=self._close,
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )

    def _build_player_list(self) -> list[ft.Control]:
        """Build a selectable row for each existing player."""
        players = self.app_state.db.get_players()
        active_id = self.app_state.active_player_id

        controls = []

        for player in players:
            is_active = player.id == active_id

            controls.append(
                ft.Container(
                    content=ft.Row(
                        controls=[
                            ft.Icon(
                                ft.Icons.PERSON,
                                color=(
                                    ft.Colors.CYAN_300
                                    if is_active
                                    else ft.Colors.WHITE_70
                                ),
                            ),
                            ft.Text(
                                player.name,
                                expand=True,
                                weight=(
                                    ft.FontWeight.BOLD
                                    if is_active
                                    else ft.FontWeight.NORMAL
                                ),
                            ),
                            (
                                ft.Text(
                                    "ACTIVE",
                                    size=11,
                                    color=ft.Colors.GREEN_300,
                                    weight=ft.FontWeight.BOLD,
                                )
                                if is_active
                                else ft.Button(
                                    content=ft.Text("Select"),
                                    on_click=lambda e, pid=player.id: (
                                        self._select_player(pid)
                                    ),
                                )
                            ),
                        ],
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    padding=10,
                    border_radius=8,
                    bgcolor=(
                        ft.Colors.with_opacity(0.15, ft.Colors.CYAN_700)
                        if is_active
                        else ft.Colors.with_opacity(0.06, ft.Colors.WHITE)
                    ),
                )
            )

        return controls

    def _select_player(self, player_id: int) -> None:
        """Activate an existing player and close the modal."""
        try:
            self.app_state.switch_player(player_id)
            self._close()

        except ValueError as exc:
            self.error_text.value = str(exc)
            self.update()

    def _create_player(self, e: ft.ControlEvent = None) -> None:
        """Create a named player and activate their profile."""
        name = self.name_field.value or ""

        if not name.strip():
            self.error_text.value = "Enter a player name."
            self.update()
            return

        try:
            player_id = self.app_state.db.create_player(name)

            # Synchronize AppState with the newly created database player.
            self.app_state.switch_player(player_id)

            self.name_field.value = ""
            self.error_text.value = ""

            self._close()

        except ValueError as exc:
            self.error_text.value = str(exc)
            self.update()

    def _close(self, e: ft.ControlEvent = None) -> None:
        """Close this dialog."""
        target_page = (e.page if e else None) or self.page

        if target_page is not None:
            if hasattr(target_page, "close"):
                target_page.close(self)
            else:
                self.open = False
                target_page.update()

