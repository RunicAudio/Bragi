"""
src/core/app_state.py
=====================
Centralized observable application state store managing view routing, practice submodes,
target notes/chords, pitch tracking data, and observer callbacks.
"""

from enum import Enum
from typing import Callable, List, Set
from pydantic import BaseModel


class ActiveViewMode(str, Enum):
    TRAINER = "TRAINER"
    TUNER = "TUNER"
    EAR_TRAINING = "EAR_TRAINING"
    ANALYTICS = "ANALYTICS"


class TrainerSubMode(str, Enum):
    SINGLE_NOTE = "SINGLE_NOTE"
    STRUMMED_CHORD = "STRUMMED_CHORD"
    ARPEGGIO_CHORD = "ARPEGGIO_CHORD"


class LivePitch(BaseModel):
    """Container model for real-time DSP pitch detection results."""

    frequency: float = 0.0
    note_name: str = "--"
    pitch_class: int = -1
    cents_deviation: float = 0.0
    is_in_tune: bool = False
    is_silent: bool = True


class AppState:
    """Singleton observable state container for the entire application."""

    _instance = None

    def __init__(self) -> None:
        self.current_view: ActiveViewMode = ActiveViewMode.TRAINER
        self.trainer_mode: TrainerSubMode = TrainerSubMode.SINGLE_NOTE

        self.target_note_name: str = "E"
        self.target_string_num: int = 1
        self.target_chord_name: str = "C Major"
        self.target_chord_pcs: Set[int] = {0, 4, 7}  # C, E, G

        self.live_pitch: LivePitch = LivePitch()

        self._view_listeners: List[Callable[[], None]] = []
        self._pitch_listeners: List[Callable[[], None]] = []

    @classmethod
    def get_instance(cls) -> "AppState":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def subscribe_view(self, listener: Callable[[], None]) -> None:
        if listener not in self._view_listeners:
            self._view_listeners.append(listener)

    def subscribe_pitch(self, listener: Callable[[], None]) -> None:
        if listener not in self._pitch_listeners:
            self._pitch_listeners.append(listener)

    def notify_view_changed(self) -> None:
        for listener in list(self._view_listeners):
            try:
                listener()
            except Exception:
                pass

    def notify_pitch_changed(self) -> None:
        for listener in list(self._pitch_listeners):
            try:
                listener()
            except Exception:
                pass

    def set_view(self, view: ActiveViewMode) -> None:
        if self.current_view != view:
            self.current_view = view
            self.notify_view_changed()

    def set_trainer_mode(self, mode: TrainerSubMode) -> None:
        self.trainer_mode = mode
        self.notify_view_changed()

    def update_live_pitch(self, pitch: LivePitch) -> None:
        self.live_pitch = pitch
        self.notify_pitch_changed()
