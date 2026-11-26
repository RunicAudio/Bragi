"""
src/ui/app_shell.py
===================
Master application container providing full-bleed background artwork (bg.png),
header bar navigation, and subview routing.
"""

import flet as ft

from core.app_state import AppState
from ui.components.header_nav import HeaderNav
from ui.components.modals.device_modal import DeviceModal
from ui.components.modals.filter_modal import FilterModal
from ui.components.modals.timing_modal import TimingModal
from ui.components.modals.instrument_modal import InstrumentModal


class AppShell(ft.Stack):
    """Main application shell routing views over full-bleed background artwork."""

    def __init__(self, page: ft.Page) -> None:
        super().__init__()
        self.app_page = page
        self.expand = True

        self.app_state = AppState.get_instance()

        self.header_nav = HeaderNav(
            on_open_filter=self._open_filter_modal,
            on_open_device=self._open_device_modal,
            on_open_instrument=self._open_instrument_modal,
            on_open_timing=self._open_timing_modal,
        )

        self.view_container = ft.Container(expand=True, padding=16)

        self.controls = [
            ft.Image(
                src="bg.png",
                fit="cover",
                width=float("inf"),
                height=float("inf"),
                error_content=ft.Container(bgcolor="#121218"),
            ),
            ft.Column(
                controls=[
                    self.header_nav,
                    self.view_container,
                ],
                expand=True,
                spacing=0,
            ),
        ]

    def update_active_view(self, view_control: ft.Control) -> None:
        self.view_container.content = view_control
        if self.app_page is not None:
            try:
                self.app_page.update()
            except Exception:
                pass

    def _open_modal(self, modal: ft.AlertDialog, e: ft.ControlEvent = None) -> None:
        target_page = (e.page if e else None) or self.app_page

        if target_page is not None:
            target_page.show_dialog(modal)

    def _open_filter_modal(self, e: ft.ControlEvent) -> None:
        self._open_modal(FilterModal(), e)

    def _open_device_modal(self, e: ft.ControlEvent) -> None:
        print("[UI DEBUG] Microphone callback fired")

        try:
            modal = DeviceModal()
            print("[UI DEBUG] DeviceModal constructed successfully")

            self._open_modal(modal, e)
            print("[UI DEBUG] Modal open request sent")

        except Exception:
            import traceback
            traceback.print_exc()

    def _open_instrument_modal(self, e: ft.ControlEvent) -> None:
        """Open instrument and tuning configuration."""
        self._open_modal(InstrumentModal(), e)

    def _open_timing_modal(self, e: ft.ControlEvent) -> None:
        self._open_modal(TimingModal(), e)
