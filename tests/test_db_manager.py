import sqlite3

import pytest

from storage.db_manager import (
    DatabaseManager,
    HeroBossData,
    UserProfileData,
)


@pytest.fixture
def db(tmp_path, monkeypatch):
    """Create an isolated database for each test."""
    db_file = tmp_path / "test_bragi.db"
    monkeypatch.setattr(
        "storage.db_manager.get_db_path",
        lambda: db_file,
    )
    return DatabaseManager()


# ============================================================
# INITIALIZATION
# ============================================================

def test_database_initializes_all_tables(db):
    with db._get_connection() as conn:
        rows = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()

    table_names = {row["name"] for row in rows}

    assert {
        "user_profile",
        "practice_attempts",
        "unlocked_badges",
        "hero_boss_progress",
    }.issubset(table_names)


def test_database_creates_default_user_profile(db):
    profile = db.get_user_profile()

    assert profile == UserProfileData(
        total_xp=0,
        user_level=1,
        current_streak=0,
        last_practice_date="",
    )


def test_database_creates_default_hero_boss_progress(db):
    progress = db.get_hero_boss_progress()

    assert progress == HeroBossData(
        consecutive_notes=0,
        consecutive_chords=0,
        consecutive_arpeggios=0,
    )


def test_database_reinitialization_preserves_existing_data(db):
    db.update_user_profile(
        total_xp=250,
        user_level=3,
        current_streak=5,
        last_practice_date="2026-11-22",
    )

    db._init_db()

    profile = db.get_user_profile()

    assert profile.total_xp == 250
    assert profile.user_level == 3
    assert profile.current_streak == 5


# ============================================================
# USER PROFILE
# ============================================================

def test_update_user_profile_persists_all_fields(db):
    db.update_user_profile(
        total_xp=500,
        user_level=4,
        current_streak=7,
        last_practice_date="2026-11-22",
    )

    profile = db.get_user_profile()

    assert profile.total_xp == 500
    assert profile.user_level == 4
    assert profile.current_streak == 7
    assert profile.last_practice_date == "2026-11-22"


def test_user_profile_survives_new_database_instance(db):
    db.update_user_profile(
        total_xp=125,
        user_level=2,
        current_streak=3,
        last_practice_date="2026-11-21",
    )

    second_instance = DatabaseManager.__new__(DatabaseManager)
    second_instance.db_path = db.db_path

    profile = second_instance.get_user_profile()

    assert profile.total_xp == 125
    assert profile.user_level == 2


# ============================================================
# ATTEMPT LOGGING
# ============================================================

def test_log_correct_attempt(db):
    db.log_attempt(
        view_mode="trainer",
        trainer_submode="single_note",
        target_name="F#",
        response_time_sec=1.25,
        is_correct=True,
        xp_earned=25,
    )

    with db._get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM practice_attempts"
        ).fetchone()

    assert row["view_mode"] == "trainer"
    assert row["trainer_submode"] == "single_note"
    assert row["target_name"] == "F#"
    assert row["response_time_sec"] == 1.25
    assert row["is_correct"] == 1
    assert row["xp_earned"] == 25
    assert row["timestamp"] > 0


def test_log_incorrect_attempt(db):
    db.log_attempt(
        view_mode="trainer",
        trainer_submode="single_note",
        target_name="A",
        response_time_sec=2.5,
        is_correct=False,
        xp_earned=0,
    )

    with db._get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM practice_attempts"
        ).fetchone()

    assert row["is_correct"] == 0
    assert row["xp_earned"] == 0


def test_multiple_attempts_are_stored(db):
    for index in range(5):
        db.log_attempt(
            view_mode="trainer",
            trainer_submode="single_note",
            target_name=f"Note {index}",
            response_time_sec=1.0,
            is_correct=True,
            xp_earned=25,
        )

    with db._get_connection() as conn:
        count = conn.execute(
            "SELECT COUNT(*) FROM practice_attempts"
        ).fetchone()[0]

    assert count == 5


# ============================================================
# ANALYTICS
# ============================================================

def test_empty_analytics_returns_zero_values(db):
    summary = db.get_analytics_summary()

    assert summary["total_attempts"] == 0
    assert summary["correct_attempts"] == 0
    assert summary["accuracy_percentage"] == 0.0
    assert summary["avg_response_speed_sec"] == 0.0
    assert summary["target_breakdown"] == {}


def test_analytics_calculates_accuracy(db):
    attempts = [
        ("A", True, 1.0),
        ("B", True, 2.0),
        ("C", False, 3.0),
        ("D", True, 4.0),
    ]

    for target, correct, response_time in attempts:
        db.log_attempt(
            view_mode="trainer",
            trainer_submode="single_note",
            target_name=target,
            response_time_sec=response_time,
            is_correct=correct,
            xp_earned=25 if correct else 0,
        )

    summary = db.get_analytics_summary()

    assert summary["total_attempts"] == 4
    assert summary["correct_attempts"] == 3
    assert summary["accuracy_percentage"] == 75.0
    assert summary["avg_response_speed_sec"] == 2.5


def test_analytics_groups_attempts_by_target(db):
    attempts = [
        ("F#", True),
        ("F#", False),
        ("A", True),
        ("F#", True),
    ]

    for target, correct in attempts:
        db.log_attempt(
            view_mode="trainer",
            trainer_submode="single_note",
            target_name=target,
            response_time_sec=1.0,
            is_correct=correct,
            xp_earned=25 if correct else 0,
        )

    breakdown = db.get_analytics_summary()["target_breakdown"]

    assert breakdown["F#"] == {"attempts": 3, "correct": 2}
    assert breakdown["A"] == {"attempts": 1, "correct": 1}


# ============================================================
# BADGE UNLOCKS
# ============================================================

def test_unlock_badge_returns_true_for_new_badge(db):
    assert db.unlock_badge("tr_b1") is True


def test_unlock_badge_returns_false_for_duplicate(db):
    assert db.unlock_badge("tr_b1") is True
    assert db.unlock_badge("tr_b1") is False


def test_unlocked_badges_are_retrieved(db):
    db.unlock_badge("tr_b1")
    db.unlock_badge("an_b2")
    db.unlock_badge("an_hero")

    assert db.get_unlocked_badge_ids() == {
        "tr_b1",
        "an_b2",
        "an_hero",
    }


def test_badge_unlock_persists_across_connections(db):
    db.unlock_badge("tr_b1")

    assert "tr_b1" in db.get_unlocked_badge_ids()


# ============================================================
# HERO BOSS PROGRESS
# ============================================================

def test_update_hero_boss_progress(db):
    db.update_hero_boss_progress(
        notes=10,
        chords=5,
        arpeggios=3,
    )

    progress = db.get_hero_boss_progress()

    assert progress == HeroBossData(
        consecutive_notes=10,
        consecutive_chords=5,
        consecutive_arpeggios=3,
    )


def test_hero_boss_progress_persists_across_connections(db):
    db.update_hero_boss_progress(
        notes=12,
        chords=8,
        arpeggios=4,
    )

    progress = db.get_hero_boss_progress()

    assert progress.consecutive_notes == 12
    assert progress.consecutive_chords == 8
    assert progress.consecutive_arpeggios == 4


def test_hero_boss_progress_fields_update_independently(db):
    db.update_hero_boss_progress(
        notes=10,
        chords=20,
        arpeggios=30,
    )

    db.update_hero_boss_progress(
        notes=11,
        chords=20,
        arpeggios=30,
    )

    progress = db.get_hero_boss_progress()

    assert progress.consecutive_notes == 11
    assert progress.consecutive_chords == 20
    assert progress.consecutive_arpeggios == 30


# ============================================================
# DATABASE CONSTRAINTS
# ============================================================

def test_user_profile_enforces_singleton_id(db):
    with pytest.raises(sqlite3.IntegrityError):
        with db._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO user_profile (
                    id, total_xp, user_level, current_streak
                )
                VALUES (2, 0, 1, 0)
                """
            )


def test_hero_boss_enforces_singleton_id(db):
    with pytest.raises(sqlite3.IntegrityError):
        with db._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO hero_boss_progress (
                    id, consecutive_notes, consecutive_chords,
                    consecutive_arpeggios
                )
                VALUES (2, 0, 0, 0)
                """
            )


def test_badge_id_is_unique(db):
    db.unlock_badge("tr_b1")

    with pytest.raises(sqlite3.IntegrityError):
        with db._get_connection() as conn:
            conn.execute(
                "INSERT INTO unlocked_badges (badge_id, unlocked_at) VALUES (?, ?)",
                ("tr_b1", 1234567890.0),
            )
