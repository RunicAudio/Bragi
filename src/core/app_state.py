"""
src/core/app_state.py
=====================
Centralized observable application state store managing view routing, practice submodes,
target notes/chords, live pitch data, hold timing preferences, and gamification state.
"""

from enum import Enum
import time
from typing import Callable, Dict, List, Optional, Set
from pydantic import BaseModel

from domain.gamification_policy import SYSTEM_BADGES, GamificationPolicy, HeroBossProgress
from domain.instrument_definitions import InstrumentConfiguration
from storage.db_manager import DatabaseManager, UserProfileData


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
    rms_level: float = 0.0


class AppState:
    """Singleton observable state container for the entire application."""

    _instance: Optional["AppState"] = None

    def __init__(self) -> None:
        self.current_view: ActiveViewMode = ActiveViewMode.TRAINER
        self.trainer_mode: TrainerSubMode = TrainerSubMode.SINGLE_NOTE

        self.target_note_name: str = "E"
        self.target_string_num: int = 1
        self.target_chord_name: str = "C Major"
        self.target_chord_pcs: Set[int] = {0, 4, 7}  # C, E, G

        self.live_pitch: LivePitch = LivePitch()

        # Timing and Hold Preferences
        self.hold_duration_sec: float = 0.8
        self.target_start_time: float = time.time()

        # Database and Gamification State
        self.db = DatabaseManager.get_instance()
        self.active_player_id: int = self.db.get_active_player_id()

        self._view_listeners: List[Callable[[], None]] = []
        self._pitch_listeners: List[Callable[[], None]] = []
        self._gamification_listeners: List[Callable[[], None]] = []

        self._load_player_data()

    def _load_player_data(self) -> None:
        """Load profile and progression data for the active player."""
        player_id = self.active_player_id

        self.instrument_configuration: InstrumentConfiguration = (
            self.db.get_instrument_configuration(player_id=player_id
        )
)

        self.user_profile: UserProfileData = self.db.get_user_profile(
            player_id=player_id
        )
        self.unlocked_badge_ids: Set[str] = self.db.get_unlocked_badge_ids(
            player_id=player_id
        )

        boss_data = self.db.get_hero_boss_progress(player_id=player_id)

        self.hero_boss = HeroBossProgress(
            consecutive_notes_under_2s=boss_data.consecutive_notes,
            consecutive_chords_under_2s=boss_data.consecutive_chords,
            consecutive_arpeggios_under_2s=boss_data.consecutive_arpeggios,
        )

    def set_instrument_configuration(
        self,
        configuration: InstrumentConfiguration,
    ) -> None:
        """Save and activate an instrument configuration for the active player."""

        if not isinstance(configuration, InstrumentConfiguration):
            raise TypeError(
                "configuration must be an InstrumentConfiguration."
            )

        self.db.save_instrument_configuration(
            configuration,
            player_id=self.active_player_id,
        )

        self.instrument_configuration = configuration
        self.reset_target_timer()
        self.notify_view_changed()

    def switch_player(self, player_id: int) -> bool:
        """
        Switch the active player and reload their progression.

        Returns True when the active player changes, otherwise False.
        Raises ValueError if the requested player does not exist.
        """
        if player_id == self.active_player_id:
            return False

        # Validate and persist the selection before changing application state.
        self.db.set_active_player_id(player_id)

        self.active_player_id = player_id
        self._load_player_data()

        self.reset_target_timer()
        self.notify_gamification_changed()
        self.notify_view_changed()

        return True

    def reset_player_progress(self, player_id: Optional[int] = None) -> None:
        """Reset one player's progress and refresh state if they are active."""

        target_player_id = (
            self.active_player_id if player_id is None else player_id
        )

        self.db.reset_player_progress(player_id=target_player_id)

        # Do not disturb the currently active player's state when
        # resetting another player.
        if target_player_id != self.active_player_id:
            return

        self._load_player_data()
        self.reset_target_timer()
        self.notify_gamification_changed()
        self.notify_view_changed()

    def rename_player(self, player_id: int, name: str) -> None:
        """Rename a player without affecting their progression."""
        self.db.rename_player(player_id, name)

        # Refresh in-memory state if the active player was renamed.
        if player_id == self.active_player_id:
            self._load_player_data()

        self.notify_view_changed()
        
    def delete_player(self, player_id: int) -> int:
        """
        Delete a player and refresh application state if necessary.

        Returns the resulting active player ID.
        """
        previous_active_id = self.active_player_id

        new_active_id = self.db.delete_player(player_id)

        if player_id == previous_active_id:
            self.active_player_id = new_active_id
            self._load_player_data()
            self.reset_target_timer()
            self.notify_gamification_changed()

        self.notify_view_changed()

        return new_active_id

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

    def subscribe_gamification(self, listener: Callable[[], None]) -> None:
        if listener not in self._gamification_listeners:
            self._gamification_listeners.append(listener)

    def add_gamification_listener(self, listener: Callable[[], None]) -> None:
        """Register a listener for gamification state changes."""
        self.subscribe_gamification(listener)

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

    def notify_gamification_changed(self) -> None:
        for listener in list(self._gamification_listeners):
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
        self.reset_target_timer()
        self.notify_view_changed()

    def set_hold_duration(self, seconds: float) -> None:
        self.hold_duration_sec = max(0.2, min(3.0, seconds))

    def update_live_pitch(self, pitch: LivePitch) -> None:
        self.live_pitch = pitch
        self.notify_pitch_changed()

    def reset_target_timer(self) -> None:
        self.target_start_time = time.time()

    # --- Gamification Event Recording ---

    def record_attempt(self, is_correct: bool, target_name: str) -> int:
        now = time.time()
        response_time = max(0.1, now - self.target_start_time)
        self.reset_target_timer()

        if is_correct:
            self.user_profile.current_streak += 1
        else:
            self.user_profile.current_streak = 0

        # XP Calculation
        xp_earned = GamificationPolicy.calculate_attempt_xp(
            is_correct=is_correct,
            response_time_sec=response_time,
            streak=self.user_profile.current_streak,
        )
        self.user_profile.total_xp += xp_earned
        self.user_profile.user_level = GamificationPolicy.calculate_level(self.user_profile.total_xp)
        today_str = time.strftime("%Y-%m-%d")
        self.user_profile.last_practice_date = today_str

        # Persist Profile & Log Attempt
        self.db.update_user_profile(
            total_xp=self.user_profile.total_xp,
            user_level=self.user_profile.user_level,
            current_streak=self.user_profile.current_streak,
            last_practice_date=today_str,
            player_id=self.active_player_id,
        )
        self.db.log_attempt(
            view_mode=self.current_view.value,
            trainer_submode=self.trainer_mode.value,
            target_name=target_name,
            response_time_sec=response_time,
            is_correct=is_correct,
            xp_earned=xp_earned,
            player_id=self.active_player_id,
        )

        # Update Hero Boss Progression (Trainer only)
        if self.current_view == ActiveViewMode.TRAINER:
            if is_correct and response_time <= 2.0:
                if self.trainer_mode == TrainerSubMode.SINGLE_NOTE:
                    self.hero_boss.consecutive_notes_under_2s += 1
                elif self.trainer_mode == TrainerSubMode.STRUMMED_CHORD:
                    self.hero_boss.consecutive_chords_under_2s += 1
                elif self.trainer_mode == TrainerSubMode.ARPEGGIO_CHORD:
                    self.hero_boss.consecutive_arpeggios_under_2s += 1
            else:
                if self.trainer_mode == TrainerSubMode.SINGLE_NOTE:
                    self.hero_boss.consecutive_notes_under_2s = 0
                elif self.trainer_mode == TrainerSubMode.STRUMMED_CHORD:
                    self.hero_boss.consecutive_chords_under_2s = 0
                elif self.trainer_mode == TrainerSubMode.ARPEGGIO_CHORD:
                    self.hero_boss.consecutive_arpeggios_under_2s = 0

            self.db.update_hero_boss_progress(
                notes=self.hero_boss.consecutive_notes_under_2s,
                chords=self.hero_boss.consecutive_chords_under_2s,
                arpeggios=self.hero_boss.consecutive_arpeggios_under_2s,
                player_id=self.active_player_id,
            )

        # Evaluate Badge Unlocks
        self._evaluate_badges()
        self.notify_gamification_changed()

        return xp_earned

    def _evaluate_badges(self) -> None:
        summary = self.db.get_analytics_summary(
            player_id=self.active_player_id
        )
        total_attempts = summary.get("total_attempts", 0)

        badge_checks = {
            "tr_b1": total_attempts >= 1,
            "tr_i2": summary.get("correct_attempts", 0) >= 20,
            "an_b2": self.user_profile.total_xp >= 100,
            "an_b3": self.user_profile.current_streak >= 3,
            "an_i1": self.user_profile.user_level >= 5,
            "an_a1": self.user_profile.user_level >= 10,
            "an_hero": self.hero_boss.is_boss_defeated,
        }

        for badge_id, condition in badge_checks.items():
            if condition and badge_id not in self.unlocked_badge_ids:
                if self.db.unlock_badge(
                    badge_id,
                    player_id=self.active_player_id,
                ):
                    self.unlocked_badge_ids.add(badge_id)
