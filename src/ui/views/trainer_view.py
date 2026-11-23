"""
src/ui/views/trainer_view.py
============================
Trainer subview driving Single Note, Strummed Chord, and Arpeggio Chord practice
with polyphonic detection, accurate timing hold evaluation, and gamification dispatch.
"""

import random
import time
import flet as ft

from core.app_state import ActiveViewMode, AppState, TrainerSubMode
from domain.chord_definitions import (
    get_chord_pitch_classes,
    select_random_chord,
)
from domain.music_theory import CHROMATIC_SHARPS, MusicTheory
from dsp.audio_engine import AudioEngine
from ui.components.modals.hint_modal import HintModal


class TrainerView(ft.Container):
    """Core practice trainer view handling note, strummed, and arpeggiated targets."""

    def __init__(self) -> None:
        super().__init__()
        self.expand = True
        self.padding = 24
        self.app_state = AppState.get_instance()
        self.audio_engine = AudioEngine.get_instance()

        self.last_advance_time = 0.0
        self.in_tune_start_time: float = 0.0

        self.txt_mode = ft.Text("", size=14, weight=ft.FontWeight.BOLD, color=ft.Colors.CYAN_400)
        self.txt_xp = ft.Text(f"XP: {self.app_state.user_profile.total_xp} (Lvl {self.app_state.user_profile.user_level})", size=14, color=ft.Colors.GREEN_400)
        self.txt_streak = ft.Text(f"Streak: {self.app_state.user_profile.current_streak}", size=14, color=ft.Colors.AMBER_400)
        self.txt_target = ft.Text("", size=32, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE)
        self.txt_subtitle = ft.Text("", size=16, color=ft.Colors.with_opacity(0.7, ft.Colors.WHITE))
        self.txt_live_note = ft.Text("--", size=18, weight=ft.FontWeight.BOLD, color=ft.Colors.RED_400)

        self.btn_hint = ft.Button(
            content=ft.Text("💡 Hint & Theory"),
            icon=ft.Icons.LIGHTBULB,
            style=ft.ButtonStyle(
                bgcolor=ft.Colors.AMBER_700,
                color=ft.Colors.WHITE,
                shape=ft.RoundedRectangleBorder(radius=10),
            ),
            on_click=self._open_hint_modal,
        )
        self.btn_skip = ft.Button(
            content=ft.Text("Skip Target"),
            style=ft.ButtonStyle(
                color=ft.Colors.with_opacity(0.7, ft.Colors.WHITE),
                shape=ft.RoundedRectangleBorder(radius=10),
            ),
            on_click=lambda _: self._skip_target(),
        )

        self.content = self._build_layout()
        self._update_target_display()

        self.app_state.subscribe_view(self._on_view_changed)
        self.app_state.subscribe_pitch(self._on_pitch_changed)
        self.app_state.subscribe_gamification(self._on_gamification_changed)

    def _build_layout(self) -> ft.Control:
        return ft.Column(
            controls=[
                ft.Row(
                    controls=[
                        self.txt_mode,
                        ft.Row(controls=[self.txt_xp, self.txt_streak], spacing=16),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                ),
                ft.Container(
                    content=ft.Column(
                        controls=[
                            self.txt_target,
                            self.txt_subtitle,
                            ft.Divider(height=20, color=ft.Colors.with_opacity(0.24, ft.Colors.WHITE)),
                            ft.Row(
                                controls=[
                                    ft.Text("Live Detected: ", size=14, color=ft.Colors.with_opacity(0.6, ft.Colors.WHITE)),
                                    self.txt_live_note,
                                ],
                                alignment=ft.MainAxisAlignment.CENTER,
                            ),
                        ],
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        alignment=ft.MainAxisAlignment.CENTER,
                    ),
                    bgcolor=ft.Colors.with_opacity(0.8, "#282A36"),
                    border_radius=16,
                    padding=32,
                    alignment=ft.Alignment.CENTER,
                ),
                ft.Row(
                    controls=[self.btn_hint, self.btn_skip],
                    alignment=ft.MainAxisAlignment.CENTER,
                    spacing=16,
                ),
            ],
            spacing=24,
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        )

    def _update_target_display(self) -> None:
        mode = self.app_state.trainer_mode
        self.txt_mode.value = f"MODE: {mode.value.replace('_', ' ')}"
        self.txt_streak.value = f"Streak: {self.app_state.user_profile.current_streak}"
        self.txt_xp.value = f"XP: {self.app_state.user_profile.total_xp} (Lvl {self.app_state.user_profile.user_level})"

        if mode == TrainerSubMode.SINGLE_NOTE:
            self.txt_target.value = f"Play Note: {self.app_state.target_note_name}"
            self.txt_subtitle.value = f"String {self.app_state.target_string_num}"
        elif mode == TrainerSubMode.STRUMMED_CHORD:
            self.txt_target.value = f"Strum Chord: {self.app_state.target_chord_name}"
            self.txt_subtitle.value = "Strum all chord tones simultaneously"
        else:
            self.txt_target.value = f"Arpeggiate: {self.app_state.target_chord_name}"
            self.txt_subtitle.value = "Pick individual notes within 2.5s window"

    def _on_pitch_changed(self) -> None:
        if self.page is not None and self.app_state.current_view == ActiveViewMode.TRAINER:
            live = self.app_state.live_pitch
            self.txt_live_note.value = live.note_name
            self.txt_live_note.color = ft.Colors.GREEN_400 if live.is_in_tune else ft.Colors.RED_400

            self._evaluate_auto_advance()

            try:
                self.update()
            except Exception:
                pass

    def _evaluate_auto_advance(self) -> None:
        now = time.time()
        if (now - self.last_advance_time) < 0.5:
            return

        mode = self.app_state.trainer_mode
        matched = False

        if mode == TrainerSubMode.SINGLE_NOTE:
            live = self.app_state.live_pitch
            if not live.is_silent and live.note_name == self.app_state.target_note_name and live.is_in_tune:
                if self.in_tune_start_time == 0.0:
                    self.in_tune_start_time = now
                elif (now - self.in_tune_start_time) >= self.app_state.hold_duration_sec:
                    matched = True
            else:
                self.in_tune_start_time = 0.0

        elif mode == TrainerSubMode.STRUMMED_CHORD:
            # Uses true polyphonic chromagram pitch classes
            strum_pcs = self.audio_engine.get_active_strum_pcs()
            target_pcs = self.app_state.target_chord_pcs
            if target_pcs and target_pcs.issubset(strum_pcs):
                matched = True

        elif mode == TrainerSubMode.ARPEGGIO_CHORD:
            # Uses time-windowed (2.5s) accumulated pitch classes
            acc_pcs = self.audio_engine.get_accumulated_arpeggio_pcs()
            target_pcs = self.app_state.target_chord_pcs
            if target_pcs and target_pcs.issubset(acc_pcs):
                matched = True

        if matched:
            self.last_advance_time = now
            self.in_tune_start_time = 0.0

            target_name = (
                self.app_state.target_note_name
                if mode == TrainerSubMode.SINGLE_NOTE
                else self.app_state.target_chord_name
            )
            self.app_state.record_attempt(is_correct=True, target_name=target_name)
            self.audio_engine.clear_arpeggio_buffer()
            self._advance_target()

    def _skip_target(self) -> None:
        target_name = (
            self.app_state.target_note_name
            if self.app_state.trainer_mode == TrainerSubMode.SINGLE_NOTE
            else self.app_state.target_chord_name
        )
        self.app_state.record_attempt(is_correct=False, target_name=target_name)
        self.audio_engine.clear_arpeggio_buffer()
        self._advance_target()

    def _advance_target(self) -> None:
        mode = self.app_state.trainer_mode
        if mode == TrainerSubMode.SINGLE_NOTE:
            new_note = random.choice(CHROMATIC_SHARPS)
            new_string = random.randint(1, 6)
            self.app_state.target_note_name = new_note
            self.app_state.target_string_num = new_string
        else:
            previous_chord = self.app_state.target_chord_name

            new_chord = select_random_chord(previous_chord)

            root, quality = new_chord.split(" ", 1)
            pcs = set(get_chord_pitch_classes(root, quality))

            self.app_state.target_chord_name = new_chord
            self.app_state.target_chord_pcs = pcs

        self.app_state.notify_view_changed()

    def _open_hint_modal(self, e: ft.ControlEvent) -> None:
        modal = HintModal()
        target_page = e.page or self.page
        if target_page is not None:
            if hasattr(target_page, "open"):
                target_page.open(modal)
            else:
                target_page.dialog = modal
                modal.open = True
                target_page.update()

    def _on_gamification_changed(self) -> None:
        if self.page is not None:
            try:
                self._update_target_display()
                self.update()
            except Exception:
                pass

    def _on_view_changed(self) -> None:
        if self.page is not None and self.app_state.current_view == ActiveViewMode.TRAINER:
            try:
                self._update_target_display()
                self.update()
            except Exception:
                pass
