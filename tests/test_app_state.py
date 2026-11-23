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


class FakeDatabase:
    def __init__(self):
        self.profile = UserProfileData()
        self.badges = set()
        self.boss = HeroBossData()
        self.attempts = []

        self.profile_updates = []
        self.boss_updates = []

    def get_user_profile(self):
        return self.profile

    def get_unlocked_badge_ids(self):
        return self.badges.copy()

    def get_hero_boss_progress(self):
        return self.boss

    def update_user_profile(self, **kwargs):
        self.profile_updates.append(kwargs)

    def log_attempt(self, **kwargs):
        self.attempts.append(kwargs)

    def get_analytics_summary(self):
        total = len(self.attempts)
        correct = sum(a["is_correct"] for a in self.attempts)

        return {
            "total_attempts": total,
            "correct_attempts": correct,
            "accuracy_percentage": (
                correct / total * 100 if total else 0.0
            ),
            "avg_response_speed_sec": 0.0,
            "target_breakdown": {},
        }

    def unlock_badge(self, badge_id):
        if badge_id in self.badges:
            return False

        self.badges.add(badge_id)
        return True

    def update_hero_boss_progress(self, notes, chords, arpeggios):
        self.boss_updates.append({
            "notes": notes,
            "chords": chords,
            "arpeggios": arpeggios,
        })

        self.boss = HeroBossData(
            consecutive_notes=notes,
            consecutive_chords=chords,
            consecutive_arpeggios=arpeggios,
        )


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


# ============================================================
# INITIALIZATION
# ============================================================

def test_initial_state_defaults(app_state):
    state, _ = app_state

    assert state.current_view == ActiveViewMode.TRAINER
    assert state.trainer_mode == TrainerSubMode.SINGLE_NOTE

    assert state.target_note_name == "E"
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
    state.set_view(ActiveViewMode.TRAINER)

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
