import pytest

from core.app_state import (
    ActiveViewMode,
    AppState,
    LivePitch,
    TrainerSubMode,
)
from domain.gamification_policy import HeroBossProgress

from storage.db_manager import (
    DatabaseManager,
    HeroBossData,
    UserProfileData,
)

from domain.instrument_definitions import (
    InstrumentConfiguration,
    InstrumentType,
    TuningString,
    get_standard_configuration,
)


class FakeDatabase:
    def __init__(self):
        self.active_player_id = 1

        self.player_names = {
            1: "Player 1",
            2: "Player 2",
        }

        # Independent data for each player.
        self.profiles = {
            1: UserProfileData(),
            2: UserProfileData(),
        }
        self.badges_by_player = {
            1: set(),
            2: set(),
        }
        self.bosses = {
            1: HeroBossData(),
            2: HeroBossData(),
        }
        self.attempts_by_player = {
            1: [],
            2: [],
        }

        self.instrument_configurations = {
            1: get_standard_configuration(InstrumentType.GUITAR),
            2: get_standard_configuration(InstrumentType.GUITAR),
        }

        # Legacy test histories retained for existing tests.
        self.profile_updates = []
        self.boss_updates = []

        # Player-specific histories for isolation tests.
        self.profile_updates_by_player = {1: [], 2: []}
        self.boss_updates_by_player = {1: [], 2: []}

    # Legacy attributes: always refer to the active player.
    @property
    def profile(self):
        return self.profiles[self.active_player_id]

    @property
    def badges(self):
        return self.badges_by_player[self.active_player_id]

    @property
    def boss(self):
        return self.bosses[self.active_player_id]

    @property
    def attempts(self):
        return self.attempts_by_player[self.active_player_id]

    # Player management.
    def get_active_player_id(self):
        return self.active_player_id

    def set_active_player_id(self, player_id):
        if player_id not in self.player_names:
            raise ValueError(f"Player {player_id} does not exist.")

        self.active_player_id = player_id

    def rename_player(self, player_id, name):
        name = name.strip()

        if not name:
            raise ValueError("Player name cannot be empty.")

        if player_id not in self.player_names:
            raise ValueError(f"Player {player_id} does not exist.")

        self.player_names[player_id] = name

    def delete_player(self, player_id):
        if player_id not in self.profiles:
            raise ValueError(f"Player {player_id} does not exist.")

        if len(self.profiles) <= 1:
            raise ValueError("Cannot delete the last remaining player.")

        if player_id == self.active_player_id:
            replacement_id = next(
                pid for pid in self.profiles if pid != player_id
            )
            self.active_player_id = replacement_id

        for collection in (
            self.profiles,
            self.badges_by_player,
            self.bosses,
            self.attempts_by_player,
            self.instrument_configurations,
            self.profile_updates_by_player,
            self.boss_updates_by_player,
            self.player_names,
        ):
            collection.pop(player_id, None)

        return self.active_player_id

    def reset_player_progress(self, player_id=None):
        player_id = (
            self.active_player_id if player_id is None else player_id
        )

        profile = self.profiles[player_id]
        profile.total_xp = 0
        profile.user_level = 1
        profile.current_streak = 0
        profile.last_practice_date = ""

        self.attempts_by_player[player_id].clear()
        self.badges_by_player[player_id].clear()
        self.bosses[player_id] = HeroBossData()

        # Instrument configuration.
    def get_instrument_configuration(self, player_id=None):
        player_id = player_id or self.active_player_id
        return self.instrument_configurations[player_id]

    def save_instrument_configuration(
        self,
        configuration,
        player_id=None,
    ):
        player_id = player_id or self.active_player_id
        self.instrument_configurations[player_id] = configuration

    # Profile.
    def get_user_profile(self, player_id=None):
        player_id = player_id or self.active_player_id
        return self.profiles[player_id]

    def update_user_profile(self, **kwargs):
        player_id = kwargs.pop("player_id", self.active_player_id)

        self.profile_updates.append(kwargs.copy())
        self.profile_updates_by_player[player_id].append(kwargs.copy())

    # Badges.
    def get_unlocked_badge_ids(self, player_id=None):
        player_id = player_id or self.active_player_id
        return self.badges_by_player[player_id].copy()

    def unlock_badge(self, badge_id, player_id=None):
        player_id = player_id or self.active_player_id
        badges = self.badges_by_player[player_id]

        if badge_id in badges:
            return False

        badges.add(badge_id)
        return True

    # Hero Boss progression.
    def get_hero_boss_progress(self, player_id=None):
        player_id = player_id or self.active_player_id
        return self.bosses[player_id]

    def update_hero_boss_progress(self, notes, chords, arpeggios, player_id=None):
        player_id = player_id or self.active_player_id

        update = {
            "notes": notes,
            "chords": chords,
            "arpeggios": arpeggios,
        }

        self.boss_updates.append(update.copy())
        self.boss_updates_by_player[player_id].append(update.copy())

        self.bosses[player_id] = HeroBossData(
            consecutive_notes=notes,
            consecutive_chords=chords,
            consecutive_arpeggios=arpeggios,
        )

    # Practice attempts and analytics.
    def log_attempt(self, **kwargs):
        player_id = kwargs.pop("player_id", self.active_player_id)
        self.attempts_by_player[player_id].append(kwargs.copy())

    def get_analytics_summary(self, player_id=None):
        player_id = player_id or self.active_player_id
        attempts = self.attempts_by_player[player_id]

        total = len(attempts)
        correct = sum(a["is_correct"] for a in attempts)

        return {
            "total_attempts": total,
            "correct_attempts": correct,
            "accuracy_percentage": (
                correct / total * 100 if total else 0.0
            ),
            "avg_response_speed_sec": 0.0,
            "target_breakdown": {},
        }

@pytest.fixture
def app_state(monkeypatch):
    fake_db = FakeDatabase()

    monkeypatch.setattr(
        DatabaseManager,
        "get_instance",
        classmethod(lambda cls: fake_db),
    )

    monkeypatch.setattr(
        "core.app_state.time.time",
        lambda: 100.0,
    )

    monkeypatch.setattr(
        "core.app_state.time.strftime",
        lambda *args: "2026-11-22",
    )

    state = AppState()

    return state, fake_db

def make_drop_d_configuration():
    """Create a six-string Drop D guitar configuration."""

    return InstrumentConfiguration(
        instrument_type=InstrumentType.GUITAR,
        string_count=6,
        tuning_name="Drop D",
        strings=(
            TuningString(6, "D", 2),
            TuningString(5, "A", 2),
            TuningString(4, "D", 3),
            TuningString(3, "G", 3),
            TuningString(2, "B", 3),
            TuningString(1, "E", 4),
        ),
    )

# ============================================================
# INITIALIZATION
# ============================================================

def test_initial_state_defaults(app_state):
    state, _ = app_state

    assert state.current_view == ActiveViewMode.HOME
    assert state.trainer_mode == TrainerSubMode.SINGLE_NOTE

    assert state.target_note_name == "E4"
    assert state.target_midi_number == 64
    assert state.target_string_num == 1

    assert state.target_chord_name == "C Major"
    assert state.target_chord_pcs == {0, 4, 7}


def test_initial_live_pitch_is_silent(app_state):
    state, _ = app_state

    assert state.live_pitch.frequency == 0.0
    assert state.live_pitch.note_name == "--"
    assert state.live_pitch.is_silent is True


def test_initial_gamification_state_loads_from_database(app_state):
    state, _ = app_state

    assert state.user_profile.total_xp == 0
    assert state.user_profile.user_level == 1
    assert state.unlocked_badge_ids == set()
    assert isinstance(state.hero_boss, HeroBossProgress)


# ============================================================
# VIEW STATE
# ============================================================

def test_set_view_changes_current_view(app_state):
    state, _ = app_state

    state.set_view(ActiveViewMode.TUNER)

    assert state.current_view == ActiveViewMode.TUNER


def test_set_view_notifies_listeners(app_state):
    state, _ = app_state
    calls = []

    state.subscribe_view(lambda: calls.append("changed"))
    state.set_view(ActiveViewMode.TUNER)

    assert calls == ["changed"]


def test_set_view_does_not_notify_when_unchanged(app_state):
    state, _ = app_state
    calls = []

    state.subscribe_view(lambda: calls.append("changed"))
    state.set_view(ActiveViewMode.HOME)

    assert calls == []


def test_duplicate_view_listener_is_not_registered(app_state):
    state, _ = app_state
    calls = []

    listener = lambda: calls.append("changed")

    state.subscribe_view(listener)
    state.subscribe_view(listener)
    state.notify_view_changed()

    assert calls == ["changed"]


# ============================================================
# TRAINER MODE
# ============================================================

@pytest.mark.parametrize(
    "mode",
    [
        TrainerSubMode.SINGLE_NOTE,
        TrainerSubMode.STRUMMED_CHORD,
        TrainerSubMode.ARPEGGIO_CHORD,
    ],
)
def test_set_trainer_mode_changes_mode(app_state, mode):
    state, _ = app_state

    state.set_trainer_mode(mode)

    assert state.trainer_mode == mode


def test_set_trainer_mode_notifies_view_listeners(app_state):
    state, _ = app_state
    calls = []

    state.subscribe_view(lambda: calls.append("changed"))
    state.set_trainer_mode(TrainerSubMode.STRUMMED_CHORD)

    assert calls == ["changed"]


# ============================================================
# HOLD DURATION
# ============================================================

@pytest.mark.parametrize(
    ("requested", "expected"),
    [
        (0.1, 0.2),
        (0.2, 0.2),
        (0.8, 0.8),
        (2.0, 2.0),
        (3.0, 3.0),
        (5.0, 3.0),
    ],
)
def test_hold_duration_is_clamped(app_state, requested, expected):
    state, _ = app_state

    state.set_hold_duration(requested)

    assert state.hold_duration_sec == expected


# ============================================================
# LIVE PITCH
# ============================================================

def test_update_live_pitch_replaces_current_pitch(app_state):
    state, _ = app_state

    pitch = LivePitch(
        frequency=440.0,
        note_name="A",
        pitch_class=9,
        cents_deviation=0.0,
        is_in_tune=True,
        is_silent=False,
        rms_level=0.5,
    )

    state.update_live_pitch(pitch)

    assert state.live_pitch == pitch


def test_update_live_pitch_notifies_listeners(app_state):
    state, _ = app_state
    calls = []

    state.subscribe_pitch(lambda: calls.append("changed"))

    state.update_live_pitch(
        LivePitch(note_name="A", frequency=440.0)
    )

    assert calls == ["changed"]


# ============================================================
# LISTENER ERROR HANDLING
# ============================================================

def test_listener_exception_does_not_prevent_other_listeners(app_state):
    state, _ = app_state
    calls = []

    def failing_listener():
        raise RuntimeError("Listener failure")

    def working_listener():
        calls.append("working")

    state.subscribe_view(failing_listener)
    state.subscribe_view(working_listener)

    state.notify_view_changed()

    assert calls == ["working"]

# ============================================================
# HERO BOSS VIEW ISOLATION
# ============================================================

@pytest.mark.parametrize("is_correct", [True, False])
def test_ear_training_attempt_does_not_change_hero_boss_progress(
    app_state, is_correct
):
    state, fake_db = app_state

    state.set_view(ActiveViewMode.EAR_TRAINING)

    state.hero_boss.consecutive_notes_under_2s = 4
    state.hero_boss.consecutive_chords_under_2s = 5
    state.hero_boss.consecutive_arpeggios_under_2s = 6

    state.record_attempt(
        is_correct=is_correct,
        target_name="Ear: F#",
    )

    assert state.hero_boss.consecutive_notes_under_2s == 4
    assert state.hero_boss.consecutive_chords_under_2s == 5
    assert state.hero_boss.consecutive_arpeggios_under_2s == 6

    assert fake_db.boss_updates == []

# ============================================================
# RECORD ATTEMPT — XP AND RESPONSE TIME
# ============================================================

def test_correct_attempt_awards_base_and_speed_xp(app_state):
    state, fake_db = app_state

    state.target_start_time = 98.0  # Exactly 2 seconds
    xp_earned = state.record_attempt(
        is_correct=True,
        target_name="F#",
    )

    assert xp_earned == 25
    assert state.user_profile.total_xp == 25
    assert state.user_profile.current_streak == 1


def test_correct_attempt_over_2_seconds_awards_base_xp_only(app_state):
    state, fake_db = app_state

    state.target_start_time = 97.9  # 2.1 seconds
    xp_earned = state.record_attempt(
        is_correct=True,
        target_name="F#",
    )

    assert xp_earned == 15
    assert state.user_profile.total_xp == 15


def test_incorrect_attempt_awards_no_xp_and_resets_streak(app_state):
    state, fake_db = app_state

    state.user_profile.current_streak = 5

    xp_earned = state.record_attempt(
        is_correct=False,
        target_name="F#",
    )

    assert xp_earned == 0
    assert state.user_profile.total_xp == 0
    assert state.user_profile.current_streak == 0


def test_record_attempt_persists_profile_and_logs_attempt(app_state):
    state, fake_db = app_state

    state.target_start_time = 98.0

    xp_earned = state.record_attempt(
        is_correct=True,
        target_name="F#",
    )

    assert len(fake_db.profile_updates) == 1
    assert fake_db.profile_updates[0] == {
        "total_xp": xp_earned,
        "user_level": state.user_profile.user_level,
        "current_streak": 1,
        "last_practice_date": "2026-11-22",
    }

    assert len(fake_db.attempts) == 1

    attempt = fake_db.attempts[0]
    assert attempt["target_name"] == "F#"
    assert attempt["is_correct"] is True
    assert attempt["response_time_sec"] == 2.0
    assert attempt["xp_earned"] == xp_earned

# ============================================================
# RECORD ATTEMPT — STREAK XP
# ============================================================

@pytest.mark.parametrize(
    "starting_streak, expected_xp",
    [
        (0, 25),   # First correct answer: base + speed
        (1, 25),   # Second correct answer
        (2, 30),   # Third correct answer: +5 streak bonus
        (5, 35),   # Sixth correct answer: +10 streak bonus
        (8, 40),   # Ninth correct answer: +15 streak bonus
        (11, 45),  # Twelfth correct answer: +20 streak bonus
        (20, 45),  # Bonus remains capped at +20
    ],
)
def test_correct_attempt_awards_expected_streak_xp(
    app_state, starting_streak, expected_xp
):
    state, fake_db = app_state

    state.user_profile.current_streak = starting_streak
    state.target_start_time = 99.0

    xp_earned = state.record_attempt(
        is_correct=True,
        target_name="F#",
    )

    assert xp_earned == expected_xp
    assert state.user_profile.current_streak == starting_streak + 1

# ============================================================
# HERO BOSS — TRAINER PROGRESSION
# ============================================================

@pytest.mark.parametrize(
    "trainer_mode, counter_name, db_key",
    [
        (TrainerSubMode.SINGLE_NOTE, "consecutive_notes_under_2s", "notes"),
        (TrainerSubMode.STRUMMED_CHORD, "consecutive_chords_under_2s", "chords"),
        (TrainerSubMode.ARPEGGIO_CHORD, "consecutive_arpeggios_under_2s", "arpeggios"),
    ],
)
def test_correct_fast_attempt_increments_hero_boss_progress(
    app_state, trainer_mode, counter_name, db_key
):
    state, fake_db = app_state

    state.set_view(ActiveViewMode.TRAINER)
    state.set_trainer_mode(trainer_mode)

    xp_counter_names = [
        "consecutive_notes_under_2s",
        "consecutive_chords_under_2s",
        "consecutive_arpeggios_under_2s",
    ]

    for name in xp_counter_names:
        setattr(state.hero_boss, name, 5)

    state.target_start_time = 99.0

    state.record_attempt(
        is_correct=True,
        target_name="Test Target",
    )

    assert getattr(state.hero_boss, counter_name) == 6

    for name in xp_counter_names:
        if name != counter_name:
            assert getattr(state.hero_boss, name) == 5

    assert len(fake_db.boss_updates) == 1
    assert fake_db.boss_updates[0][db_key] == 6


@pytest.mark.parametrize(
    "trainer_mode, counter_name",
    [
        (TrainerSubMode.SINGLE_NOTE, "consecutive_notes_under_2s"),
        (TrainerSubMode.STRUMMED_CHORD, "consecutive_chords_under_2s"),
        (TrainerSubMode.ARPEGGIO_CHORD, "consecutive_arpeggios_under_2s"),
    ],
)
def test_incorrect_attempt_resets_only_relevant_hero_boss_progress(
    app_state, trainer_mode, counter_name
):
    state, fake_db = app_state

    state.set_view(ActiveViewMode.TRAINER)
    state.set_trainer_mode(trainer_mode)

    counters = [
        "consecutive_notes_under_2s",
        "consecutive_chords_under_2s",
        "consecutive_arpeggios_under_2s",
    ]

    for name in counters:
        setattr(state.hero_boss, name, 5)

    state.record_attempt(
        is_correct=False,
        target_name="Test Target",
    )

    assert getattr(state.hero_boss, counter_name) == 0

    for name in counters:
        if name != counter_name:
            assert getattr(state.hero_boss, name) == 5

    assert len(fake_db.boss_updates) == 1


@pytest.mark.parametrize(
    "trainer_mode, counter_name",
    [
        (TrainerSubMode.SINGLE_NOTE, "consecutive_notes_under_2s"),
        (TrainerSubMode.STRUMMED_CHORD, "consecutive_chords_under_2s"),
        (TrainerSubMode.ARPEGGIO_CHORD, "consecutive_arpeggios_under_2s"),
    ],
)
def test_slow_correct_attempt_resets_only_relevant_hero_boss_progress(
    app_state, trainer_mode, counter_name
):
    state, fake_db = app_state

    state.set_view(ActiveViewMode.TRAINER)
    state.set_trainer_mode(trainer_mode)

    counters = [
        "consecutive_notes_under_2s",
        "consecutive_chords_under_2s",
        "consecutive_arpeggios_under_2s",
    ]

    for name in counters:
        setattr(state.hero_boss, name, 5)

    state.target_start_time = 97.9  # 2.1 seconds

    state.record_attempt(
        is_correct=True,
        target_name="Test Target",
    )

    assert getattr(state.hero_boss, counter_name) == 0

    for name in counters:
        if name != counter_name:
            assert getattr(state.hero_boss, name) == 5

    assert len(fake_db.boss_updates) == 1

# ============================================================
# BADGE UNLOCKING
# ============================================================

def test_first_attempt_unlocks_trainer_beginner_badge(app_state):
    state, fake_db = app_state

    state.record_attempt(
        is_correct=False,
        target_name="F#",
    )

    assert "tr_b1" in state.unlocked_badge_ids
    assert "tr_b1" in fake_db.badges


def test_repeated_attempts_do_not_duplicate_badge_unlocks(app_state):
    state, fake_db = app_state

    state.record_attempt(False, "F#")
    state.record_attempt(False, "A")
    state.record_attempt(False, "C")

    assert fake_db.badges == {"tr_b1"}


def test_analytics_beginner_badge_unlocks_at_100_xp(app_state):
    state, fake_db = app_state

    state.user_profile.total_xp = 99

    state._evaluate_badges()

    assert "an_b2" not in state.unlocked_badge_ids

    state.user_profile.total_xp = 100
    state._evaluate_badges()

    assert "an_b2" in state.unlocked_badge_ids


def test_analytics_streak_badge_unlocks_at_three(app_state):
    state, fake_db = app_state

    state.user_profile.current_streak = 2
    state._evaluate_badges()

    assert "an_b3" not in state.unlocked_badge_ids

    state.user_profile.current_streak = 3
    state._evaluate_badges()

    assert "an_b3" in state.unlocked_badge_ids


def test_hero_badge_unlocks_when_all_stages_are_completed(app_state):
    state, fake_db = app_state

    state.hero_boss.consecutive_notes_under_2s = 50
    state.hero_boss.consecutive_chords_under_2s = 50
    state.hero_boss.consecutive_arpeggios_under_2s = 50

    state._evaluate_badges()

    assert "an_hero" in state.unlocked_badge_ids
    assert "an_hero" in fake_db.badges


def test_hero_badge_does_not_unlock_until_all_stages_are_completed(app_state):
    state, fake_db = app_state

    state.hero_boss.consecutive_notes_under_2s = 50
    state.hero_boss.consecutive_chords_under_2s = 50
    state.hero_boss.consecutive_arpeggios_under_2s = 49

    state._evaluate_badges()

    assert "an_hero" not in state.unlocked_badge_ids


# ============================================================
# GAMIFICATION LISTENER NOTIFICATIONS
# ============================================================

def test_record_attempt_notifies_gamification_listeners(app_state):
    state, fake_db = app_state

    notifications = []
    state.add_gamification_listener(
        lambda: notifications.append("notified")
    )

    state.record_attempt(
        is_correct=True,
        target_name="F#",
    )

    assert notifications == ["notified"]


def test_gamification_listener_exception_does_not_block_other_listeners(
    app_state,
):
    state, fake_db = app_state

    notifications = []

    def failing_listener():
        raise RuntimeError("Test listener failure")

    state.subscribe_gamification(failing_listener)
    state.add_gamification_listener(
        lambda: notifications.append("notified")
    )

    xp_earned = state.record_attempt(
        is_correct=True,
        target_name="F#",
    )

    assert xp_earned > 0
    assert notifications == ["notified"]
    assert len(fake_db.attempts) == 1

# ============================================================
# MULTI-PLAYER STATE
# ============================================================

def test_initialization_loads_active_player_id(app_state):
    state, fake_db = app_state

    assert state.active_player_id == fake_db.active_player_id == 1


def test_switch_player_loads_player_specific_progress(app_state):
    state, fake_db = app_state

    fake_db.profiles[2] = UserProfileData(
        total_xp=250,
        user_level=3,
        current_streak=5,
        last_practice_date="2026-11-24",
    )
    fake_db.badges_by_player[2] = {"tr_b1", "an_b2"}
    fake_db.bosses[2] = HeroBossData(
        consecutive_notes=7,
        consecutive_chords=4,
        consecutive_arpeggios=2,
    )

    assert state.switch_player(2) is True

    assert state.active_player_id == 2
    assert fake_db.active_player_id == 2

    assert state.user_profile.total_xp == 250
    assert state.user_profile.user_level == 3
    assert state.user_profile.current_streak == 5

    assert state.unlocked_badge_ids == {"tr_b1", "an_b2"}

    assert state.hero_boss.consecutive_notes_under_2s == 7
    assert state.hero_boss.consecutive_chords_under_2s == 4
    assert state.hero_boss.consecutive_arpeggios_under_2s == 2


def test_switching_players_notifies_listeners(app_state):
    state, _ = app_state

    view_notifications = []
    gamification_notifications = []

    state.subscribe_view(
        lambda: view_notifications.append(True)
    )
    state.subscribe_gamification(
        lambda: gamification_notifications.append(True)
    )

    assert state.switch_player(2) is True

    assert len(view_notifications) == 1
    assert len(gamification_notifications) == 1


def test_switching_to_current_player_does_nothing(app_state):
    state, fake_db = app_state

    view_notifications = []
    gamification_notifications = []

    state.subscribe_view(
        lambda: view_notifications.append(True)
    )
    state.subscribe_gamification(
        lambda: gamification_notifications.append(True)
    )

    assert state.switch_player(1) is False

    assert state.active_player_id == 1
    assert fake_db.active_player_id == 1
    assert view_notifications == []
    assert gamification_notifications == []


def test_invalid_player_switch_preserves_current_player(app_state):
    state, fake_db = app_state

    with pytest.raises(ValueError):
        state.switch_player(999)

    assert state.active_player_id == 1
    assert fake_db.active_player_id == 1


def test_attempt_progress_is_isolated_between_players(app_state):
    state, fake_db = app_state

    state.set_view(ActiveViewMode.TRAINER)

    # Give Player 1 some existing progress.
    fake_db.profiles[1].total_xp = 150
    fake_db.profiles[1].current_streak = 4
    fake_db.badges_by_player[1].add("an_b2")

    # Switch to Player 2 and record an attempt.
    state.switch_player(2)
    xp_earned = state.record_attempt(
        is_correct=True,
        target_name="C",
    )

    assert xp_earned > 0

    # Player 2 receives the new progress.
    assert len(fake_db.attempts_by_player[2]) == 1
    assert len(fake_db.profile_updates_by_player[2]) == 1
    assert len(fake_db.boss_updates_by_player[2]) == 1
    assert "tr_b1" in fake_db.badges_by_player[2]

    # Player 1 remains unchanged.
    assert fake_db.attempts_by_player[1] == []
    assert fake_db.profile_updates_by_player[1] == []
    assert fake_db.boss_updates_by_player[1] == []
    assert fake_db.badges_by_player[1] == {"an_b2"}

    assert fake_db.profiles[1].total_xp == 150
    assert fake_db.profiles[1].current_streak == 4


def test_switching_back_restores_previous_player_state(app_state):
    state, fake_db = app_state

    fake_db.profiles[1].total_xp = 150
    fake_db.profiles[1].current_streak = 4
    fake_db.badges_by_player[1] = {"an_b2"}

    fake_db.profiles[2].total_xp = 300
    fake_db.profiles[2].current_streak = 8
    fake_db.badges_by_player[2] = {"tr_b1", "an_b3"}

    state.switch_player(2)

    assert state.user_profile.total_xp == 300
    assert state.unlocked_badge_ids == {"tr_b1", "an_b3"}

    state.switch_player(1)

    assert state.active_player_id == 1
    assert state.user_profile.total_xp == 150
    assert state.user_profile.current_streak == 4
    assert state.unlocked_badge_ids == {"an_b2"}

def test_initialization_loads_default_instrument_configuration(app_state):
    state, fake_db = app_state

    expected = get_standard_configuration(InstrumentType.GUITAR)

    assert state.instrument_configuration == expected
    assert fake_db.instrument_configurations[1] == expected


def test_set_instrument_configuration_persists_for_active_player(app_state):
    state, fake_db = app_state
    configuration = make_drop_d_configuration()

    state.set_instrument_configuration(configuration)

    assert state.instrument_configuration == configuration
    assert fake_db.instrument_configurations[1] == configuration


def test_instrument_configuration_is_player_scoped(app_state):
    state, fake_db = app_state
    configuration = make_drop_d_configuration()

    state.set_instrument_configuration(configuration)

    state.switch_player(2)

    player_two_default = get_standard_configuration(
        InstrumentType.GUITAR
    )

    assert state.instrument_configuration == player_two_default
    assert fake_db.instrument_configurations[1] == configuration
    assert fake_db.instrument_configurations[2] == player_two_default


def test_switch_player_loads_player_specific_instrument_configuration(
    app_state,
):
    state, fake_db = app_state

    configuration = make_drop_d_configuration()
    fake_db.instrument_configurations[2] = configuration

    assert state.switch_player(2) is True
    assert state.instrument_configuration == configuration


def test_switching_back_restores_previous_instrument_configuration(
    app_state,
):
    state, fake_db = app_state

    player_one_configuration = make_drop_d_configuration()
    player_two_configuration = get_standard_configuration(
        InstrumentType.BASS
    )

    state.set_instrument_configuration(player_one_configuration)
    state.switch_player(2)

    state.set_instrument_configuration(player_two_configuration)
    state.switch_player(1)

    assert state.instrument_configuration == player_one_configuration

    state.switch_player(2)

    assert state.instrument_configuration == player_two_configuration


def test_set_instrument_configuration_rejects_invalid_type(app_state):
    state, fake_db = app_state
    original_configuration = state.instrument_configuration

    with pytest.raises(TypeError):
        state.set_instrument_configuration("Drop D")

    assert state.instrument_configuration == original_configuration
    assert (
        fake_db.instrument_configurations[1]
        == original_configuration
    )

def test_reset_active_player_progress_refreshes_app_state(app_state):
    state, fake_db = app_state

    fake_db.profiles[1] = UserProfileData(
        total_xp=500,
        user_level=4,
        current_streak=12,
        last_practice_date="2026-11-24",
    )
    fake_db.badges_by_player[1] = {"tr_b1", "an_b2"}
    fake_db.attempts_by_player[1].append({"is_correct": True})
    fake_db.bosses[1] = HeroBossData(
        consecutive_notes=5,
        consecutive_chords=3,
        consecutive_arpeggios=2,
    )

    configuration = make_drop_d_configuration()
    state.set_instrument_configuration(configuration)

    view_notifications = []
    gamification_notifications = []

    state.subscribe_view(lambda: view_notifications.append(True))
    state.subscribe_gamification(
        lambda: gamification_notifications.append(True)
    )

    state.reset_player_progress(1)

    assert state.user_profile.total_xp == 0
    assert state.user_profile.user_level == 1
    assert state.user_profile.current_streak == 0
    assert state.user_profile.last_practice_date == ""

    assert state.unlocked_badge_ids == set()
    assert state.hero_boss.consecutive_notes_under_2s == 0
    assert state.hero_boss.consecutive_chords_under_2s == 0
    assert state.hero_boss.consecutive_arpeggios_under_2s == 0

    assert fake_db.attempts_by_player[1] == []
    assert state.instrument_configuration == configuration

    assert len(view_notifications) == 1
    assert len(gamification_notifications) == 1


def test_reset_inactive_player_does_not_change_active_state(app_state):
    state, fake_db = app_state

    fake_db.profiles[1].total_xp = 250
    fake_db.profiles[2].total_xp = 500
    fake_db.badges_by_player[2] = {"tr_b1"}
    fake_db.attempts_by_player[2].append({"is_correct": True})

    view_notifications = []
    gamification_notifications = []

    state.subscribe_view(lambda: view_notifications.append(True))
    state.subscribe_gamification(
        lambda: gamification_notifications.append(True)
    )

    state.reset_player_progress(2)

    assert state.active_player_id == 1
    assert state.user_profile.total_xp == 250

    assert fake_db.profiles[2].total_xp == 0
    assert fake_db.profiles[2].user_level == 1
    assert fake_db.badges_by_player[2] == set()
    assert fake_db.attempts_by_player[2] == []

    assert view_notifications == []
    assert gamification_notifications == []

# ============================================================
# PLAYER RENAME AND DELETE
# ============================================================

def test_rename_player_updates_name_without_changing_progress(app_state):
    state, fake_db = app_state

    fake_db.profiles[1].total_xp = 500
    fake_db.profiles[1].user_level = 4
    fake_db.badges_by_player[1].add("tr_b1")

    state.rename_player(1, "Arty")

    assert fake_db.player_names[1] == "Arty"
    assert state.user_profile.total_xp == 500
    assert state.user_profile.user_level == 4
    assert "tr_b1" in state.unlocked_badge_ids


def test_rename_player_notifies_view_listeners(app_state):
    state, _ = app_state
    notifications = []

    state.subscribe_view(lambda: notifications.append(True))

    state.rename_player(1, "New Name")

    assert len(notifications) == 1


def test_rename_invalid_player_raises_value_error(app_state):
    state, _ = app_state

    with pytest.raises(ValueError):
        state.rename_player(999, "Invalid")


def test_delete_inactive_player_preserves_active_state(app_state):
    state, fake_db = app_state

    fake_db.profiles[1].total_xp = 250
    original_profile = state.user_profile

    resulting_active_id = state.delete_player(2)

    assert resulting_active_id == 1
    assert state.active_player_id == 1
    assert fake_db.active_player_id == 1
    assert state.user_profile is original_profile
    assert 2 not in fake_db.profiles


def test_delete_active_player_loads_replacement_state(app_state):
    state, fake_db = app_state

    fake_db.profiles[2] = UserProfileData(
        total_xp=750,
        user_level=6,
        current_streak=12,
        last_practice_date="2026-11-25",
    )
    fake_db.badges_by_player[2] = {"tr_b1", "an_b2"}
    fake_db.bosses[2] = HeroBossData(
        consecutive_notes=10,
        consecutive_chords=20,
        consecutive_arpeggios=30,
    )

    drop_d = make_drop_d_configuration()
    fake_db.instrument_configurations[2] = drop_d

    resulting_active_id = state.delete_player(1)

    assert resulting_active_id == 2
    assert state.active_player_id == 2

    assert state.user_profile.total_xp == 750
    assert state.user_profile.user_level == 6
    assert state.user_profile.current_streak == 12

    assert state.unlocked_badge_ids == {"tr_b1", "an_b2"}

    assert state.hero_boss.consecutive_notes_under_2s == 10
    assert state.hero_boss.consecutive_chords_under_2s == 20
    assert state.hero_boss.consecutive_arpeggios_under_2s == 30

    assert state.instrument_configuration == drop_d

    assert 1 not in fake_db.profiles


def test_delete_active_player_notifies_listeners(app_state):
    state, _ = app_state

    view_notifications = []
    gamification_notifications = []

    state.subscribe_view(
        lambda: view_notifications.append(True)
    )
    state.subscribe_gamification(
        lambda: gamification_notifications.append(True)
    )

    state.delete_player(1)

    assert len(view_notifications) == 1
    assert len(gamification_notifications) == 1


def test_delete_inactive_player_only_notifies_view(app_state):
    state, _ = app_state

    view_notifications = []
    gamification_notifications = []

    state.subscribe_view(
        lambda: view_notifications.append(True)
    )
    state.subscribe_gamification(
        lambda: gamification_notifications.append(True)
    )

    state.delete_player(2)

    assert len(view_notifications) == 1
    assert len(gamification_notifications) == 0


def test_delete_nonexistent_player_raises_value_error(app_state):
    state, _ = app_state

    with pytest.raises(ValueError):
        state.delete_player(999)


def test_delete_last_remaining_player_is_rejected(app_state):
    state, fake_db = app_state

    fake_db.delete_player(2)

    with pytest.raises(ValueError, match="last remaining player"):
        state.delete_player(1)

    assert state.active_player_id == 1
    assert 1 in fake_db.profiles
