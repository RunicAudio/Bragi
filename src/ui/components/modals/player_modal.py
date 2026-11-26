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
                width=520,
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
        """Build selectable player rows with management actions."""
        players = self.app_state.db.get_players()
        active_id = self.app_state.active_player_id

        controls = []

        for player in players:
            is_active = player.id == active_id
            can_delete = len(players) > 1

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
                            ft.Button(
                                content=ft.Text("Reset"),
                                icon=ft.Icons.RESTART_ALT,
                                on_click=lambda e, pid=player.id, name=player.name: (
                                    self._show_reset_confirmation(pid, name, e)
                                ),
                            ),
                            ft.IconButton(
                                icon=ft.Icons.EDIT,
                                icon_color=ft.Colors.CYAN_300,
                                tooltip="Rename player",
                                on_click=lambda e, pid=player.id, name=player.name: (
                                    self._show_rename_dialog(pid, name, e)
                                ),
                            ),
                            ft.IconButton(
                                icon=ft.Icons.DELETE_OUTLINE,
                                icon_color=ft.Colors.RED_300,
                                tooltip=(
                                    "Delete player"
                                    if can_delete
                                    else "Cannot delete the only player"
                                ),
                                disabled=not can_delete,
                                on_click=lambda e, pid=player.id, name=player.name: (
                                    self._show_delete_confirmation(pid, name, e)
                                ),
                            ),
                        ],
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=4,
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

    def _show_rename_dialog(
        self,
        player_id: int,
        player_name: str,
        e: ft.ControlEvent,
    ) -> None:
        """Open a dialog for renaming a player."""
        target_page = (e.page if e else None) or self.page

        if target_page is None:
            return

        name_field = ft.TextField(
            label="Player Name",
            value=player_name,
            autofocus=True,
            width=300,
        )

        rename_error = ft.Text(
            "",
            color=ft.Colors.RED_300,
            size=12,
        )

        confirmation = ft.AlertDialog(
            modal=True,
            title=ft.Text("Rename Player"),
            content=ft.Column(
                controls=[
                    name_field,
                    rename_error,
                ],
                tight=True,
            ),
            actions=[
                ft.Button(
                    content=ft.Text("Cancel"),
                    on_click=lambda e: target_page.pop_dialog(),
                ),
                ft.Button(
                    content=ft.Text("Save"),
                    icon=ft.Icons.SAVE,
                    on_click=lambda e: self._rename_player(
                        player_id,
                        name_field,
                        rename_error,
                        target_page,
                    ),
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )

        target_page.show_dialog(confirmation)


    def _rename_player(
        self,
        player_id: int,
        name_field: ft.TextField,
        error_text: ft.Text,
        target_page: ft.Page,
    ) -> None:
        """Save a player's new name and refresh the list."""
        name = name_field.value or ""

        if not name.strip():
            error_text.value = "Player name cannot be empty."
            error_text.update()
            return

        try:
            self.app_state.rename_player(player_id, name)

            target_page.pop_dialog()

            self.error_text.value = ""
            self.player_list.controls = self._build_player_list()
            self.update()

        except (ValueError, RuntimeError) as exc:
            error_text.value = str(exc)
            error_text.update()


    def _show_delete_confirmation(
        self,
        player_id: int,
        player_name: str,
        e: ft.ControlEvent,
    ) -> None:
        """Ask for confirmation before permanently deleting a player."""
        target_page = (e.page if e else None) or self.page

        if target_page is None:
            return

        confirmation = ft.AlertDialog(
            modal=True,
            title=ft.Text("Delete Player?"),
            content=ft.Text(
                f"Are you sure you want to permanently delete "
                f"{player_name}?\n\n"
                "This will permanently remove:\n"
                "• Player profile and progress\n"
                "• XP and player level\n"
                "• Practice history\n"
                "• Unlocked badges\n"
                "• Hero Boss progress\n"
                "• Instrument and tuning configuration\n\n"
                "This action cannot be undone."
            ),
            actions=[
                ft.Button(
                    content=ft.Text("Cancel"),
                    on_click=lambda e: target_page.pop_dialog(),
                ),
                ft.Button(
                    content=ft.Text("Delete Player"),
                    icon=ft.Icons.DELETE_OUTLINE,
                    on_click=lambda e: self._delete_player(
                        player_id,
                        target_page,
                    ),
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )

        target_page.show_dialog(confirmation)


    def _delete_player(
        self,
        player_id: int,
        target_page: ft.Page,
    ) -> None:
        """Delete a player and refresh the player list."""
        try:
            target_page.pop_dialog()

            self.app_state.delete_player(player_id)

            self.error_text.value = ""
            self.player_list.controls = self._build_player_list()
            self.update()

        except (ValueError, RuntimeError) as exc:
            self.error_text.value = str(exc)
            self.update()

    def _show_reset_confirmation(
        self,
        player_id: int,
        player_name: str,
        e: ft.ControlEvent,
    ) -> None:
        """Ask for confirmation before resetting a player's progress."""
        target_page = (e.page if e else None) or self.page

        if target_page is None:
            return

        confirmation = ft.AlertDialog(
            modal=True,
            title=ft.Text("Reset Player Progress?"),
            content=ft.Text(
                f"This will permanently reset all progress for "
                f"{player_name}.\n\n"
                "The following will be cleared:\n"
                "• XP and player level\n"
                "• Practice history\n"
                "• Unlocked badges\n"
                "• Hero Boss progress\n\n"
                "The player profile and instrument configuration "
                "will be preserved."
            ),
            actions=[
                ft.Button(
                    content=ft.Text("Cancel"),
                    on_click=lambda e: target_page.pop_dialog(),
                ),
                ft.Button(
                    content=ft.Text("Reset Progress"),
                    icon=ft.Icons.RESTART_ALT,
                    on_click=lambda e: self._reset_player_progress(
                        player_id, target_page
                    ),
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )

        target_page.show_dialog(confirmation)

    def _reset_player_progress(
        self,
        player_id: int,
        target_page: ft.Page,
    ) -> None:
        """Reset the selected player's progress and refresh the list."""
        try:
            target_page.pop_dialog()

            self.app_state.reset_player_progress(player_id)

            self.error_text.value = ""
            self.player_list.controls = self._build_player_list()
            self.update()

        except (ValueError, RuntimeError) as exc:
            self.error_text.value = str(exc)
            self.update()


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
            target_page.pop_dialog()
