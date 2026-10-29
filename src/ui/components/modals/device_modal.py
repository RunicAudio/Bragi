"""
src/ui/components/modals/device_modal.py
========================================
Modal dialog for selecting active microphone input hardware.
"""

import flet as ft
from dsp.audio_engine import AudioEngine


class DeviceModal(ft.AlertDialog):
    """Modal popup dialog allowing users to pick an active audio input device."""

    def __init__(self) -> None:
        self.audio_engine = AudioEngine.get_instance()
        devices = self.audio_engine.get_input_devices()

        options = [
            ft.DropdownOption(
                key=str(dev["id"]),
                text=f"{dev['name']} ({dev['channels']} in)",
            )
            for dev in devices
        ]

        current_key = (
            str(self.audio_engine.device_id)
            if self.audio_engine.device_id is not None
            else (options[0].key if options else None)
        )

        self.dd_devices = ft.Dropdown(
            options=options,
            value=current_key,
            width=340,
            on_select=self._on_device_selected,
        )

        super().__init__(
            title=ft.Row(
                controls=[
                    ft.Icon(ft.Icons.MIC, color=ft.Colors.AMBER_300),
                    ft.Text("Audio Input Device", weight=ft.FontWeight.BOLD),
                ],
                spacing=8,
            ),
            content=ft.Container(
                content=ft.Column(
                    controls=[
                        ft.Text(
                            "Select Microphone / Input Source:",
                            size=13,
                            color=ft.Colors.with_opacity(0.7, ft.Colors.WHITE),
                        ),
                        self.dd_devices if options else ft.Text("No input audio devices detected.", color=ft.Colors.RED_400),
                    ],
                    tight=True,
                    spacing=12,
                ),
                width=380,
                padding=12,
            ),
            actions=[
                ft.Button(content=ft.Text("Close"), on_click=lambda e: self._close(e)),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )

    def _on_device_selected(self, e: ft.ControlEvent) -> None:
        val = e.control.value or e.data
        if val:
            try:
                dev_id = int(val)
                self.audio_engine.set_device(dev_id)
            except ValueError:
                pass

    def _close(self, e: ft.ControlEvent) -> None:
        target_page = e.page or self.page
        if target_page is not None:
            if hasattr(target_page, "close"):
                target_page.close(self)
            else:
                self.open = False
                target_page.update()
