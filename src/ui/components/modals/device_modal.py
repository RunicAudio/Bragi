"""
src/ui/components/modals/device_modal.py
========================================
Modal dialog for selecting audio input device with a live signal test meter.
"""

import flet as ft
from core.app_state import AppState
from dsp.audio_engine import AudioEngine


class DeviceModal(ft.AlertDialog):
    """Modal popup dialog for selecting audio input device and testing mic input."""

    def __init__(self) -> None:
        self.audio_engine = AudioEngine.get_instance()
        self.app_state = AppState.get_instance()

        self.pb_level = ft.ProgressBar(value=0.0, width=320, color=ft.Colors.GREEN_400)
        self.txt_live_status = ft.Text("Live Input: --", size=13, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE)

        self.radio_group = ft.RadioGroup(
            content=ft.Column(controls=[], spacing=8, scroll=ft.ScrollMode.AUTO),
            on_change=self._on_radio_changed,
        )

        self._populate_devices()

        super().__init__(
            title=ft.Row(
                controls=[
                    ft.Icon(ft.Icons.MIC, color=ft.Colors.AMBER_300),
                    ft.Text("Audio Input Setup", weight=ft.FontWeight.BOLD),
                ],
                spacing=8,
            ),
            content=ft.Container(
                content=ft.Column(
                    controls=[
                        ft.Text("Select Active Input Source:", size=13, color=ft.Colors.with_opacity(0.7, ft.Colors.WHITE)),
                        ft.Container(
                            content=self.radio_group,
                            height=180,
                            border=ft.Border.all(1, ft.Colors.with_opacity(0.2, ft.Colors.WHITE)),
                            border_radius=8,
                            padding=8,
                        ),
                        ft.Divider(height=16, color=ft.Colors.with_opacity(0.2, ft.Colors.WHITE)),
                        ft.Text("Live Input Test:", size=13, weight=ft.FontWeight.BOLD, color=ft.Colors.CYAN_300),
                        self.pb_level,
                        self.txt_live_status,
                    ],
                    tight=True,
                    spacing=10,
                ),
                width=380,
                padding=12,
            ),
            actions=[
                ft.Button(content=ft.Text("Refresh List"), on_click=lambda e: self._refresh_devices(e)),
                ft.Button(content=ft.Text("Done"), on_click=lambda e: self._close(e)),
            ],
            actions_alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        )

        self.app_state.subscribe_pitch(self._on_pitch_update)

    def _populate_devices(self) -> None:
        # Prevent initialization from triggering device changes.
        self.radio_group.on_change = None

        devices = self.audio_engine.get_input_devices()
        current_key = self.audio_engine.device_key

        radios = []

        for dev in devices:
            device_key = dev["key"]

            label = (
                f"{dev['name']} "
                f"({dev['channels']} ch) "
                f"— {dev['host_api']}"
            )

            if dev["is_default"]:
                label += " [Default]"

            radios.append(
                ft.Radio(
                    value=device_key,
                    label=label,
                )
            )

        if not radios:
            radios.append(
                ft.Text(
                    "No audio input devices detected.",
                    color=ft.Colors.RED_300,
                    size=13,
                )
            )

        self.radio_group.content.controls = radios

        available_keys = {dev["key"] for dev in devices}

        if current_key in available_keys:
            self.radio_group.value = current_key
        elif devices:
            default_device = next(
                (dev for dev in devices if dev["is_default"]),
                devices[0],
            )
            self.radio_group.value = default_device["key"]
        else:
            self.radio_group.value = None

        # Enable device switching after initialization.
        self.radio_group.on_change = self._on_radio_changed

    def _on_radio_changed(self, e: ft.ControlEvent) -> None:
        device_key = e.control.value

        if not device_key:
            return

        if device_key == self.audio_engine.device_key:
            return

        self.audio_engine.set_device(device_key)

    def _refresh_devices(self, e: ft.ControlEvent) -> None:
        self.audio_engine.stop()

        # Re-resolve the saved preference against currently connected devices.
        self.audio_engine._initialize_input_device()

        self._populate_devices()
        self.audio_engine.start()

        if self.page:
            self.update()

    def _on_pitch_update(self) -> None:
        live = self.app_state.live_pitch
        level = min(1.0, live.rms_level * 30.0)
        self.pb_level.value = level

        if live.is_silent or live.note_name == "--":
            self.txt_live_status.value = f"Signal Level: {int(level * 100)}% (Listening...)"
            self.txt_live_status.color = ft.Colors.WHITE
        else:
            self.txt_live_status.value = f"Detected: {live.note_name} ({live.cents_deviation:+.1f}c)"
            self.txt_live_status.color = ft.Colors.GREEN_400

        if self.page:
            try:
                self.update()
            except Exception:
                pass

    def _close(self, e: ft.ControlEvent) -> None:
        target_page = e.page or self.page
        if target_page is not None:
            if hasattr(target_page, "close"):
                target_page.close(self)
            else:
                self.open = False
                target_page.update()
