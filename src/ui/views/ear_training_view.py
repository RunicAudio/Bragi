"""
src/ui/views/ear_training_view.py
=================================
Ear training subview supporting Single Note, Interval, and Triad Identification
with non-clipping clean audio playback and attempt logging to SQLite.
"""

from enum import Enum
import random
import flet as ft

from core.app_state import AppState
from domain.music_theory import CHROMATIC_SHARPS
from dsp.sample_player import SamplePlayer


class EarMode(str, Enum):
    SINGLE_NOTE = "Single Pitch"
    TRIAD_QUALITY = "Chord Quality"


class EarTrainingView(ft.Container):
    """Ear training practice view bound to user XP and badge progression."""

    def __init__(self) -> None:
        super().__init__()
        self.expand = True
        self.padding = 24
        self.app_state = AppState.get_instance()
        self.sample_player = SamplePlayer()

        self.current_mode = EarMode.SINGLE_NOTE
        self.target_pcs: set[int] = {0}
        self.current_target_name = "C"
        self.options = ["C", "E", "G", "A"]
        self.feedback_message = "Listen closely and select the correct answer."
        self.is_answered = False

        self._generate_new_question()
        self.content = self._build_content()

    def _generate_new_question(self) -> None:
        self.is_answered = False
        if self.current_mode == EarMode.SINGLE_NOTE:
            self.current_target_name = random.choice(CHROMATIC_SHARPS)
            from domain.music_theory import MusicTheory
            self.target_pcs = {MusicTheory.note_to_pitch_class(self.current_target_name)}
            self.options = [self.current_target_name]
            while len(self.options) < 4:
                opt = random.choice(CHROMATIC_SHARPS)
                if opt not in self.options:
                    self.options.append(opt)
            random.shuffle(self.options)
        else:
            qualities = ["Major", "Minor", "Diminished", "Sus4"]
            self.current_target_name = random.choice(qualities)
            root_pc = random.randint(0, 11)
            if self.current_target_name == "Major":
                self.target_pcs = {root_pc, (root_pc + 4) % 12, (root_pc + 7) % 12}
            elif self.current_target_name == "Minor":
                self.target_pcs = {root_pc, (root_pc + 3) % 12, (root_pc + 7) % 12}
            elif self.current_target_name == "Diminished":
                self.target_pcs = {root_pc, (root_pc + 3) % 12, (root_pc + 6) % 12}
            else:
                self.target_pcs = {root_pc, (root_pc + 5) % 12, (root_pc + 7) % 12}
            self.options = qualities

        self.feedback_message = "Press 'Replay Audio' to listen."

    def _play_target_audio(self) -> None:
        self.sample_player.play_pitch_classes(self.target_pcs, base_octave=4, duration_sec=1.2)

    def _submit_answer(self, selected_option: str) -> None:
        if self.is_answered:
            return
        self.is_answered = True
        is_correct = (selected_option == self.current_target_name)

        if is_correct:
            self.feedback_message = f"✓ Correct! It was {self.current_target_name}."
        else:
            self.feedback_message = f"✕ Incorrect. Correct answer was {self.current_target_name}."

        self.app_state.record_attempt(is_correct=is_correct, target_name=f"Ear: {self.current_target_name}")
        self.content = self._build_content()
        self.update()

    def _toggle_mode(self, mode: EarMode) -> None:
        self.current_mode = mode
        self._generate_new_question()
        self.content = self._build_content()
        self.update()
        self._play_target_audio()

    def _build_content(self) -> ft.Control:
        option_buttons = [
            ft.Button(
                content=ft.Text(opt),
                width=120,
                height=48,
                style=ft.ButtonStyle(
                    bgcolor=ft.Colors.CYAN_700 if self.is_answered and opt == self.current_target_name else None,
                    shape=ft.RoundedRectangleBorder(radius=10),
                ),
                on_click=lambda _, o=opt: self._submit_answer(o),
            )
            for opt in self.options
        ]

        return ft.Column(
            controls=[
                ft.Row(
                    controls=[
                        ft.Text("EAR TRAINING SUITE", size=18, weight=ft.FontWeight.BOLD, color=ft.Colors.CYAN_300),
                        ft.Row(
                            controls=[
                                ft.Button(
                                    content=ft.Text("Single Pitch"),
                                    on_click=lambda _: self._toggle_mode(EarMode.SINGLE_NOTE),
                                ),
                                ft.Button(
                                    content=ft.Text("Chord Quality"),
                                    on_click=lambda _: self._toggle_mode(EarMode.TRIAD_QUALITY),
                                ),
                            ],
                            spacing=8,
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                ),
                ft.Container(
                    content=ft.Column(
                        controls=[
                            ft.Text(f"Mode: {self.current_mode.value}", size=14, color=ft.Colors.AMBER_300),
                            ft.Text(self.feedback_message, size=16, color=ft.Colors.WHITE),
                            ft.IconButton(
                                icon=ft.Icons.VOLUME_UP,
                                icon_size=48,
                                icon_color=ft.Colors.CYAN_400,
                                tooltip="Replay Audio",
                                on_click=lambda _: self._play_target_audio(),
                            ),
                            ft.Row(controls=option_buttons, alignment=ft.MainAxisAlignment.CENTER, spacing=12),
                            ft.Button(
                                content=ft.Text("Next Question"),
                                on_click=lambda _: self._next_question(),
                            ),
                        ],
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=20,
                    ),
                    bgcolor=ft.Colors.with_opacity(0.8, "#282A36"),
                    border_radius=16,
                    padding=32,
                ),
            ],
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=24,
        )

    def _next_question(self) -> None:
        self._generate_new_question()
        self.content = self._build_content()
        self.update()
        self._play_target_audio()
