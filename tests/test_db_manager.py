import sqlite3

import pytest

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


@pytest.fixture
def db(tmp_path, monkeypatch):
    """Create an isolated database for each test."""
    db_file = tmp_path / "test_bragi.db"
    monkeypatch.setattr(
        "storage.db_manager.get_db_path",
        lambda: db_file,
    )
    return DatabaseManager()

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

def test_user_profile_enforces_one_profile_per_player(db):
    with pytest.raises(sqlite3.IntegrityError):
        with db._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO user_profile (
                    player_id, total_xp, user_level, current_streak
                )
                VALUES (1, 0, 1, 0)
                """
            )


def test_hero_boss_enforces_one_record_per_player(db):
    with pytest.raises(sqlite3.IntegrityError):
        with db._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO hero_boss_progress (
                    player_id, consecutive_notes,
                    consecutive_chords, consecutive_arpeggios
                )
                VALUES (1, 0, 0, 0)
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

# ============================================================
# MULTI-PLAYER MANAGEMENT
# ============================================================

def test_database_creates_default_player(db):
    players = db.get_players()

    assert len(players) == 1
    assert players[0].id == 1
    assert players[0].name == "Player 1"


def test_default_player_is_active(db):
    assert db.get_active_player_id() == 1


def test_create_player_returns_unique_id(db):
    player_2 = db.create_player("Player 2")
    player_3 = db.create_player("Player 3")

    assert player_2 != player_3
    assert player_2 != 1
    assert player_3 != 1


def test_create_player_persists_name(db):
    player_id = db.create_player("Alex")

    player = db.get_player(player_id)

    assert player is not None
    assert player.id == player_id
    assert player.name == "Alex"


def test_get_players_returns_all_players(db):
    db.create_player("Alex")
    db.create_player("Jordan")

    players = db.get_players()
    names = {player.name for player in players}

    assert names == {"Player 1", "Alex", "Jordan"}


def test_new_player_becomes_active(db):
    player_id = db.create_player("Alex")

    assert db.get_active_player_id() == player_id


def test_switching_active_player_persists(db):
    player_2 = db.create_player("Player 2")

    db.set_active_player_id(1)
    assert db.get_active_player_id() == 1

    db.set_active_player_id(player_2)
    assert db.get_active_player_id() == player_2


def test_cannot_activate_nonexistent_player(db):
    with pytest.raises(ValueError):
        db.set_active_player_id(9999)


def test_player_data_survives_database_reinitialization(db):
    player_id = db.create_player("Alex")

    db._init_db()

    player = db.get_player(player_id)

    assert player is not None
    assert player.name == "Alex"
    assert db.get_active_player_id() == player_id

# ============================================================
# PLAYER-SCOPED DATA
# ============================================================

def test_player_profiles_are_independent(db):
    player_2 = db.create_player("Alex")

    db.update_user_profile(
        500, 5, 10, "2026-11-25", player_id=1
    )
    db.update_user_profile(
        100, 2, 3, "2026-11-24", player_id=player_2
    )

    assert db.get_user_profile(1).total_xp == 500
    assert db.get_user_profile(player_2).total_xp == 100


def test_practice_attempts_are_player_scoped(db):
    player_2 = db.create_player("Alex")

    db.log_attempt("TRAINER", "NOTES", "C4", 1.0, True, 10, player_id=1)
    db.log_attempt("TRAINER", "NOTES", "E4", 2.0, False, 0, player_id=player_2)

    assert db.get_analytics_summary(1)["total_attempts"] == 1
    assert db.get_analytics_summary(player_2)["total_attempts"] == 1


def test_badges_are_player_scoped(db):
    player_2 = db.create_player("Alex")

    assert db.unlock_badge("tr_b1", player_id=1) is True
    assert db.unlock_badge("tr_b1", player_id=player_2) is True

    assert "tr_b1" in db.get_unlocked_badge_ids(1)
    assert "tr_b1" in db.get_unlocked_badge_ids(player_2)


def test_hero_boss_progress_is_player_scoped(db):
    player_2 = db.create_player("Alex")

    db.update_hero_boss_progress(10, 20, 30, player_id=1)
    db.update_hero_boss_progress(5, 6, 7, player_id=player_2)

    assert db.get_hero_boss_progress(1).consecutive_notes == 10
    assert db.get_hero_boss_progress(player_2).consecutive_notes == 5


def test_reset_player_progress_only_resets_selected_player(db):
    player_2 = db.create_player("Alex")

    db.update_user_profile(500, 5, 10, "2026-11-25", player_id=1)
    db.update_user_profile(200, 3, 4, "2026-11-25", player_id=player_2)

    db.log_attempt("TRAINER", "NOTES", "C4", 1.0, True, 10, player_id=1)
    db.log_attempt("TRAINER", "NOTES", "E4", 1.0, True, 10, player_id=player_2)

    db.unlock_badge("tr_b1", player_id=1)
    db.unlock_badge("tr_b1", player_id=player_2)

    db.update_hero_boss_progress(10, 20, 30, player_id=1)
    db.update_hero_boss_progress(5, 6, 7, player_id=player_2)

    drop_d = make_drop_d_configuration()
    db.save_instrument_configuration(drop_d, player_id=1)

    db.reset_player_progress(1)

    assert db.get_user_profile(1).total_xp == 0
    assert db.get_analytics_summary(1)["total_attempts"] == 0
    assert db.get_unlocked_badge_ids(1) == set()
    assert db.get_hero_boss_progress(1).consecutive_notes == 0

    assert db.get_user_profile(player_2).total_xp == 200
    assert db.get_analytics_summary(player_2)["total_attempts"] == 1
    assert "tr_b1" in db.get_unlocked_badge_ids(player_2)
    assert db.get_hero_boss_progress(player_2).consecutive_notes == 5

    assert db.get_instrument_configuration(1) == drop_d

# ============================================================
# INSTRUMENT CONFIGURATION
# ============================================================

def test_default_player_receives_standard_guitar_configuration(db):
    configuration = db.get_instrument_configuration(1)

    expected = get_standard_configuration(InstrumentType.GUITAR)

    assert configuration == expected
    assert configuration.tuning_name == "Standard"
    assert configuration.string_count == 6


def test_new_player_receives_standard_guitar_configuration(db):
    player_id = db.create_player("Alex")

    configuration = db.get_instrument_configuration(player_id)

    assert configuration == get_standard_configuration(
        InstrumentType.GUITAR
    )


def test_custom_instrument_configuration_persists(db):
    configuration = make_drop_d_configuration()

    db.save_instrument_configuration(configuration, player_id=1)

    retrieved = db.get_instrument_configuration(player_id=1)

    assert retrieved == configuration
    assert retrieved.tuning_name == "Drop D"
    assert retrieved.get_string(6).note_name == "D2"


def test_instrument_configurations_are_player_scoped(db):
    player_2 = db.create_player("Alex")

    drop_d = make_drop_d_configuration()
    bass = get_standard_configuration(InstrumentType.BASS)

    db.save_instrument_configuration(drop_d, player_id=1)
    db.save_instrument_configuration(bass, player_id=player_2)

    assert db.get_instrument_configuration(1) == drop_d
    assert db.get_instrument_configuration(player_2) == bass


def test_instrument_configuration_uses_active_player_by_default(db):
    player_2 = db.create_player("Alex")
    configuration = get_standard_configuration(InstrumentType.BASS)

    db.save_instrument_configuration(configuration)

    assert db.get_instrument_configuration() == configuration
    assert db.get_instrument_configuration(1).instrument_type == (
        InstrumentType.GUITAR
    )
    assert db.get_instrument_configuration(player_2) == configuration


def test_instrument_configuration_survives_database_reinitialization(db):
    configuration = make_drop_d_configuration()

    db.save_instrument_configuration(configuration, player_id=1)

    db._init_db()

    assert db.get_instrument_configuration(1) == configuration


def test_instrument_configuration_rejects_non_configuration(db):
    with pytest.raises(TypeError):
        db.save_instrument_configuration(
            {"instrument": "Guitar"},
            player_id=1,
        )


def test_instrument_configuration_rejects_nonexistent_player(db):
    configuration = make_drop_d_configuration()

    with pytest.raises(ValueError):
        db.save_instrument_configuration(
            configuration,
            player_id=9999,
        )

    with pytest.raises(ValueError):
        db.get_instrument_configuration(player_id=9999)

def test_legacy_database_migrates_all_data_to_player_one(
    tmp_path, monkeypatch
):
    """Existing single-player data must survive the multi-player migration."""

    db_file = tmp_path / "legacy_bragi.db"

    # Build a database using the original single-player schema.
    with sqlite3.connect(db_file) as conn:
        conn.executescript(
            """
            CREATE TABLE user_profile (
                id INTEGER PRIMARY KEY,
                total_xp INTEGER NOT NULL DEFAULT 0,
                user_level INTEGER NOT NULL DEFAULT 1,
                current_streak INTEGER NOT NULL DEFAULT 0,
                last_practice_date TEXT DEFAULT ''
            );

            CREATE TABLE practice_attempts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp REAL NOT NULL,
                view_mode TEXT NOT NULL,
                trainer_submode TEXT NOT NULL,
                target_name TEXT NOT NULL,
                response_time_sec REAL NOT NULL,
                is_correct INTEGER NOT NULL,
                xp_earned INTEGER NOT NULL
            );

            CREATE TABLE unlocked_badges (
                badge_id TEXT PRIMARY KEY,
                unlocked_at REAL NOT NULL
            );

            CREATE TABLE hero_boss_progress (
                id INTEGER PRIMARY KEY,
                consecutive_notes INTEGER NOT NULL DEFAULT 0,
                consecutive_chords INTEGER NOT NULL DEFAULT 0,
                consecutive_arpeggios INTEGER NOT NULL DEFAULT 0
            );

            INSERT INTO user_profile (
                id, total_xp, user_level, current_streak,
                last_practice_date
            )
            VALUES (1, 1250, 5, 12, '2026-11-24');

            INSERT INTO practice_attempts (
                timestamp, view_mode, trainer_submode,
                target_name, response_time_sec,
                is_correct, xp_earned
            )
            VALUES (
                1732400000.0, 'chords', 'recognition',
                'C Major', 1.25, 1, 10
            );

            INSERT INTO unlocked_badges (badge_id, unlocked_at)
            VALUES ('first_chord', 1732400000.0);

            INSERT INTO hero_boss_progress (
                id, consecutive_notes, consecutive_chords,
                consecutive_arpeggios
            )
            VALUES (1, 8, 6, 4);
            """
        )

    monkeypatch.setattr(
        "storage.db_manager.get_db_path",
        lambda: db_file,
    )

    # Initializing the manager should migrate the legacy database.
    db = DatabaseManager()

    # Verify profile migration.
    profile = db.get_user_profile()

    assert profile == UserProfileData(
        total_xp=1250,
        user_level=5,
        current_streak=12,
        last_practice_date="2026-11-24",
    )

    # Verify Hero Boss migration.
    boss = db.get_hero_boss_progress()

    assert boss == HeroBossData(
        consecutive_notes=8,
        consecutive_chords=6,
        consecutive_arpeggios=4,
    )

    # Verify player identity and active-player setting.
    assert db.get_active_player_id() == 1

    players = db.get_players()

    assert len(players) == 1
    assert players[0].id == 1
    assert players[0].name == "Player 1"

    with db._get_connection() as conn:
        # Verify practice history.
        attempts = conn.execute(
            """
            SELECT *
            FROM practice_attempts
            WHERE player_id = 1
            """
        ).fetchall()

        assert len(attempts) == 1
        assert attempts[0]["target_name"] == "C Major"
        assert attempts[0]["is_correct"] == 1
        assert attempts[0]["xp_earned"] == 10

        # Verify badge migration.
        badges = conn.execute(
            """
            SELECT *
            FROM unlocked_badges
            WHERE player_id = 1
            """
        ).fetchall()

        assert len(badges) == 1
        assert badges[0]["badge_id"] == "first_chord"

        # Verify migration version.
        version = conn.execute(
            "PRAGMA user_version"
        ).fetchone()[0]

        assert version == 2
        instrument_row = conn.execute(
            """
            SELECT configuration_json
            FROM player_instrument_configurations
            WHERE player_id = 1
            """
        ).fetchone()

        assert instrument_row is not None

        # Verify temporary legacy tables were removed.
        tables = {
            row["name"]
            for row in conn.execute(
                """
                SELECT name
                FROM sqlite_master
                WHERE type = 'table'
                """
            ).fetchall()
        }

        assert not any(
            table.endswith("_legacy")
            for table in tables
        )

    # Reinitialization must not duplicate or erase migrated data.
    db._init_db()

    with db._get_connection() as conn:
        assert conn.execute(
            "SELECT COUNT(*) FROM practice_attempts"
        ).fetchone()[0] == 1

        assert conn.execute(
            "SELECT COUNT(*) FROM unlocked_badges"
        ).fetchone()[0] == 1

    assert db.get_user_profile().total_xp == 1250

def test_failed_migration_rolls_back_all_schema_changes(
    tmp_path, monkeypatch
):
    """A failed migration must leave the original database unchanged."""

    db_file = tmp_path / "failed_migration.db"

    # Create a malformed legacy database.
    # last_practice_date is intentionally missing.
    with sqlite3.connect(db_file) as conn:
        conn.execute(
            """
            CREATE TABLE user_profile (
                id INTEGER PRIMARY KEY,
                total_xp INTEGER NOT NULL DEFAULT 0,
                user_level INTEGER NOT NULL DEFAULT 1,
                current_streak INTEGER NOT NULL DEFAULT 0
            )
            """
        )

        conn.execute(
            """
            INSERT INTO user_profile (
                id, total_xp, user_level, current_streak
            )
            VALUES (1, 750, 4, 9)
            """
        )

    monkeypatch.setattr(
        "storage.db_manager.get_db_path",
        lambda: db_file,
    )

    # Migration should fail when it attempts to read the missing column.
    with pytest.raises(IndexError):
        DatabaseManager()

    # Inspect the database independently after the failed migration.
    with sqlite3.connect(db_file) as conn:
        tables = {
            row[0]
            for row in conn.execute(
                """
                SELECT name
                FROM sqlite_master
                WHERE type = 'table'
                """
            ).fetchall()
        }

        # The original table must retain its original name.
        assert "user_profile" in tables
        assert "user_profile_legacy" not in tables

        # No partially created multi-player schema should remain.
        assert "players" not in tables
        assert "app_settings" not in tables

        # The migration version must remain unchanged.
        version = conn.execute(
            "PRAGMA user_version"
        ).fetchone()[0]

        assert version == 0

        # Original data must remain intact.
        profile = conn.execute(
            "SELECT * FROM user_profile WHERE id = 1"
        ).fetchone()

        assert profile == (1, 750, 4, 9)

def test_rename_player_updates_name_without_changing_progress(db):
    player_id = db.create_player("Alex")

    db.update_user_profile(
        500, 5, 10, "2026-11-25", player_id=player_id
    )
    db.unlock_badge("tr_b1", player_id=player_id)

    db.rename_player(player_id, "Alexander")

    player = db.get_player(player_id)

    assert player.name == "Alexander"
    assert db.get_user_profile(player_id).total_xp == 500
    assert "tr_b1" in db.get_unlocked_badge_ids(player_id)


def test_rename_player_trims_whitespace(db):
    player_id = db.create_player("Alex")

    db.rename_player(player_id, "  Jordan  ")

    assert db.get_player(player_id).name == "Jordan"


def test_rename_player_rejects_empty_name(db):
    with pytest.raises(ValueError):
        db.rename_player(1, "   ")


def test_rename_player_rejects_nonexistent_player(db):
    with pytest.raises(ValueError):
        db.rename_player(9999, "Alex")


def test_delete_inactive_player_preserves_active_player(db):
    player_id = db.create_player("Alex")
    db.set_active_player_id(1)

    resulting_active_id = db.delete_player(player_id)

    assert resulting_active_id == 1
    assert db.get_active_player_id() == 1
    assert db.get_player(player_id) is None


def test_delete_active_player_selects_another_player(db):
    player_2 = db.create_player("Alex")
    player_3 = db.create_player("Jordan")

    assert db.get_active_player_id() == player_3

    resulting_active_id = db.delete_player(player_3)

    assert resulting_active_id == 1
    assert db.get_active_player_id() == 1
    assert db.get_player(player_3) is None
    assert db.get_player(1) is not None
    assert db.get_player(player_2) is not None


def test_delete_player_cascades_all_player_data(db):
    player_id = db.create_player("Alex")

    db.update_user_profile(
        500, 5, 10, "2026-11-25", player_id=player_id
    )
    db.log_attempt(
        "TRAINER", "NOTES", "C4", 1.0, True, 10,
        player_id=player_id,
    )
    db.unlock_badge("tr_b1", player_id=player_id)
    db.update_hero_boss_progress(
        10, 20, 30, player_id=player_id
    )
    db.save_instrument_configuration(
        make_drop_d_configuration(),
        player_id=player_id,
    )

    db.delete_player(player_id)

    assert db.get_player(player_id) is None

    with db._get_connection() as conn:
        for table in (
            "user_profile",
            "practice_attempts",
            "unlocked_badges",
            "hero_boss_progress",
            "player_instrument_configurations",
        ):
            result = conn.execute(
                f"SELECT COUNT(*) FROM {table} WHERE player_id = ?",
                (player_id,),
            ).fetchone()[0]

            assert result == 0, f"{table} still contains player data"


def test_delete_last_remaining_player_is_rejected(db):
    with pytest.raises(ValueError, match="last remaining player"):
        db.delete_player(1)

    assert db.get_player(1) is not None
    assert db.get_active_player_id() == 1


def test_delete_nonexistent_player_is_rejected(db):
    with pytest.raises(ValueError):
        db.delete_player(9999)

def test_get_setting_returns_default_when_missing(db):
    assert db.get_setting("audio_input_device") is None
    assert db.get_setting("audio_input_device", "default-device") == "default-device"


def test_set_and_get_setting(db):
    db.set_setting("audio_input_device", "Windows WASAPI|HeadRush Core|Multichannel")

    assert db.get_setting("audio_input_device") == (
        "Windows WASAPI|HeadRush Core|Multichannel"
    )


def test_set_setting_updates_existing_value(db):
    db.set_setting("audio_input_device", "Device A")
    db.set_setting("audio_input_device", "Device B")

    assert db.get_setting("audio_input_device") == "Device B"


def test_settings_are_global_across_players(db):
    db.set_setting("audio_input_device", "Windows WASAPI|HeadRush Core|Multichannel")

    player_id = db.create_player("Alex")
    db.set_active_player_id(player_id)

    assert db.get_setting("audio_input_device") == (
        "Windows WASAPI|HeadRush Core|Multichannel"
    )


def test_set_setting_rejects_empty_key(db):
    with pytest.raises(ValueError, match="Setting key cannot be empty"):
        db.set_setting("   ", "value")
