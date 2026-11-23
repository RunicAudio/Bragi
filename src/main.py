"""
src/main.py
===========
Application entry point launching Flet UI via ft.run(),
initializing Central DSP, and managing thread-safe lifecycle hooks.
"""

from pathlib import Path
import sys

SRC_DIR = Path(__file__).resolve().parent
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

import flet as ft

from core.app_state import ActiveViewMode, AppState
from dsp.audio_engine import AudioEngine
from ui.app_shell import AppShell
from ui.views.analytics_view import AnalyticsView
from ui.views.ear_training_view import EarTrainingView
from ui.views.trainer_view import TrainerView
from ui.views.tuner_view import TunerView


def main(page: ft.Page) -> None:
    page.title = "Bragi - Fretboard Mastery"
    page.window.width = 1100
    page.window.height = 750
    page.theme_mode = ft.ThemeMode.DARK
    page.padding = 0

    # Initialize State Store and Shell
    app_state = AppState.get_instance()
    shell = AppShell(page)
    page.add(shell)

    # Subviews
    trainer_view = TrainerView()
    tuner_view = TunerView()
    ear_view = EarTrainingView()
    analytics_view = AnalyticsView()

    def route_view() -> None:
        view_mode = app_state.current_view
        if view_mode == ActiveViewMode.TRAINER:
            shell.update_active_view(trainer_view)
        elif view_mode == ActiveViewMode.TUNER:
            shell.update_active_view(tuner_view)
        elif view_mode == ActiveViewMode.EAR_TRAINING:
            shell.update_active_view(ear_view)
        elif view_mode == ActiveViewMode.ANALYTICS:
            shell.update_active_view(analytics_view)

    app_state.subscribe_view(route_view)
    route_view()

    # Start audio stream
    audio_engine = AudioEngine.get_instance()
    audio_engine.set_ui_page(page)
    audio_engine.start()

    # Shutdown handlers to prevent background thread crashes on exit
    def cleanup():
        # Prevent further UI updates before shutting down audio.
        audio_engine.set_ui_page(None)
        audio_engine.stop()

    page.on_disconnect = lambda e: cleanup()

    def on_window_event(e):
        if e.data == "close":
            cleanup()

    page.window.on_event = on_window_event


if __name__ == "__main__":
    ft.run(main)
