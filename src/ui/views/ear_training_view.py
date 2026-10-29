"""
src/ui/views/ear_training_view.py
=================================
Ear training subview offering single note, interval, chord quality, and inversion identification.
"""

import random
import flet as ft

from domain.music_theory import CHROMATIC_SHARPS
from dsp.sample_player import SamplePlayer


class EarTrainingView(ft.Container):
    """Ear training practice view utilizing non-clipping clean piano audio playback."""

    def __init__(self) -> None:
        super().__init__()
        self.expand = True
        self.padding = 24
        self.sample_player = SamplePlayer()

        self.current_target_note = "C"
        self.options = ["C", "E", "G", "A"]
        self.feedback_message = "Listen closely and select the correct pitch."
        self.is_answered = False

        self._generate_new_question()
        self.content = self._build_content()

    def _generate_new_question(self) -> None:
        self.current_target_note = random.choice(CHROMATIC_SHARPS)
        self.options = [self.current_target_note]
        while len(self.options) < 4:
            opt = random.choice(CHROMATIC_SHARPS)
            if opt not in self.options:
                self.options.append(opt)
        random.shuffle(self.options)
        self.is_answered = False
        self.feedback_message = "Press 'Replay Audio' to listen again."

    def _play_target_audio(self) -> None:
        self.sample_player.play_note(self.current_target_note, octave=4, duration_sec=1.2)

    def _submit_answer(self, selected_option: str) -> None:
        if self.is_answered:
            return
        self.is_answered = True
        if selected_option == self.current_target_note:
            self.feedback_message = f"✓ Correct! The note was {self.current_target_note}."
        else:
            self.feedback_message = f"✕ Incorrect. Target note was {self.current_target_note}."
        self.update()

    def _build_content(self) -> ft.Control:
        option_buttons = [
            ft.Button(
                content=ft.Text(opt),
                width=120,
                height=48,
                style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10)),
                on_click=lambda _, o=opt: self._submit_answer(o),
            )
            for opt in self.options
        ]

        return ft.Column(
            controls=[
                ft.Text("EAR TRAINING SUITE", size=18, weight=ft.FontWeight.BOLD, color=ft.Colors.CYAN_300),
                ft.Container(
                    content=ft.Column(
                        controls=[
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
