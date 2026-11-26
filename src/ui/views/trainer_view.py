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
from domain.music_theory import MusicTheory
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
        self.txt_target = ft.Text(
            "",
            size=48,
            weight=ft.FontWeight.BOLD,
            color=ft.Colors.WHITE,
            text_align=ft.TextAlign.CENTER,
        )

        self.txt_subtitle = ft.Text(
            "",
            size=16,
            color=ft.Colors.with_opacity(0.85, ft.Colors.WHITE),
            text_align=ft.TextAlign.CENTER,
        )

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
                # Top status row — preserve existing layout.
                ft.Row(
                    controls=[
                        self.txt_mode,
                        ft.Row(
                            controls=[self.txt_xp, self.txt_streak],
                            spacing=16,
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                ),

                # Circular target display.
                ft.Container(
                    width=340,
                    height=340,
                    border=ft.Border.all(
                        4,
                        ft.Colors.AMBER_400,
                    ),
                    border_radius=170,
                    bgcolor=ft.Colors.with_opacity(
                        0.55,
                        "#282A36",
                    ),
                    alignment=ft.Alignment.CENTER,
                    padding=28,
                    content=ft.Column(
                        controls=[
                            self.txt_subtitle,
                            self.txt_target,
                            ft.Container(height=8),
                            ft.Row(
                                controls=[
                                    ft.Text(
                                        "Live Detected:",
                                        size=14,
                                        color=ft.Colors.with_opacity(
                                            0.7,
                                            ft.Colors.WHITE,
                                        ),
                                    ),
                                    self.txt_live_note,
                                ],
                                alignment=ft.MainAxisAlignment.CENTER,
                                spacing=6,
                            ),
                        ],
                        alignment=ft.MainAxisAlignment.CENTER,
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=12,
                        tight=True,
                    ),
                ),

                # Existing Hint and Skip buttons — unchanged.
                ft.Row(
                    controls=[
                        self.btn_hint,
                        self.btn_skip,
                    ],
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
            string_number = self.app_state.target_string_num
            configuration = self.app_state.instrument_configuration

            try:
                open_string_note = configuration.get_string(
                    string_number
                ).note

                self.txt_subtitle.value = (
                    f"String {string_number} ({open_string_note})"
                )

            except ValueError:
                self.txt_subtitle.value = f"String {string_number}"

            self.txt_target.value = self.app_state.target_note_name

        elif mode == TrainerSubMode.STRUMMED_CHORD:
            self.txt_target.value = self.app_state.target_chord_name
            self.txt_subtitle.value = "STRUM CHORD"

        else:
            self.txt_target.value = self.app_state.target_chord_name
            self.txt_subtitle.value = "ARPEGGIATE CHORD"

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
            if (
                not live.is_silent
                and live.midi_number == self.app_state.target_midi_number
                and live.is_in_tune
            ):
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
            configuration = self.app_state.instrument_configuration
            selected_string = random.choice(configuration.strings)

            # Short drone strings, such as the fifth banjo string,
            # can only be selected as open-string targets.
            fret = (
                0
                if selected_string.is_short
                else random.randint(0, configuration.fret_count)
            )

            target_midi = selected_string.midi_number + fret

            self.app_state.target_midi_number = target_midi
            self.app_state.target_note_name = (
                MusicTheory.midi_number_to_note_name(target_midi)
            )
            self.app_state.target_string_num = selected_string.string_number
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
            target_page.show_dialog(modal)

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
