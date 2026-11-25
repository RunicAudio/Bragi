"""
src/storage/db_manager.py
=========================
Thread-safe SQLite database manager for multi-player analytics,
practice logs, badge unlocks, and Hero Boss progression.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
import sqlite3
import threading
import time
from typing import Any, Dict, List, Optional, Set

from storage.path_utils import get_db_path


@dataclass
class UserProfileData:
    total_xp: int = 0
    user_level: int = 1
    current_streak: int = 0
    last_practice_date: str = ""


@dataclass
class HeroBossData:
    consecutive_notes: int = 0
    consecutive_chords: int = 0
    consecutive_arpeggios: int = 0


@dataclass
class PlayerData:
    id: int
    name: str
    created_at: str


class DatabaseManager:
    """Thread-safe SQLite DAO managing persistent application state."""

    _instance: Optional["DatabaseManager"] = None
    _lock = threading.Lock()

    def __init__(self) -> None:
        self.db_path = get_db_path()
        self._init_db()

    @classmethod
    def get_instance(cls) -> "DatabaseManager":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path), timeout=10.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.execute("PRAGMA journal_mode = WAL;")
        return conn

    # ============================================================
    # DATABASE INITIALIZATION AND MIGRATION
    # ============================================================

    def _init_db(self) -> None:
        with self._get_connection() as conn:
            conn.execute("BEGIN IMMEDIATE")

            version = conn.execute("PRAGMA user_version").fetchone()[0]

            if version < 1:
                self._migrate_to_multi_player(conn)

            self._create_missing_rows(conn)

            conn.execute("PRAGMA user_version = 1")
            conn.commit()

    def _migrate_to_multi_player(self, conn: sqlite3.Connection) -> None:
        """Migrate the original single-player database without losing data."""

        existing_tables = {
            row["name"]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            ).fetchall()
        }

        legacy_tables = [
            "user_profile",
            "practice_attempts",
            "unlocked_badges",
            "hero_boss_progress",
        ]

        for table in legacy_tables:
            if table in existing_tables:
                conn.execute(
                    f"ALTER TABLE {table} RENAME TO {table}_legacy"
                )
                existing_tables.add(f"{table}_legacy")

        self._create_schema(conn)

        now = datetime.now(timezone.utc).isoformat()

        # Create the original user's profile.
        conn.execute(
            """
            INSERT INTO players (id, name, created_at)
            VALUES (1, 'Player 1', ?)
            """,
            (now,),
        )

        # Migrate XP and profile information.
        if "user_profile_legacy" in existing_tables:
            row = conn.execute(
                "SELECT * FROM user_profile_legacy LIMIT 1"
            ).fetchone()

            if row:
                conn.execute(
                    """
                    INSERT INTO user_profile (
                        player_id, total_xp, user_level,
                        current_streak, last_practice_date
                    )
                    VALUES (1, ?, ?, ?, ?)
                    """,
                    (
                        row["total_xp"],
                        row["user_level"],
                        row["current_streak"],
                        row["last_practice_date"],
                    ),
                )

        # Migrate practice history.
        if "practice_attempts_legacy" in existing_tables:
            conn.execute(
                """
                INSERT INTO practice_attempts (
                    timestamp, view_mode, trainer_submode,
                    target_name, response_time_sec,
                    is_correct, xp_earned, player_id
                )
                SELECT
                    timestamp, view_mode, trainer_submode,
                    target_name, response_time_sec,
                    is_correct, xp_earned, 1
                FROM practice_attempts_legacy
                """
            )

        # Migrate badge unlocks.
        if "unlocked_badges_legacy" in existing_tables:
            conn.execute(
                """
                INSERT INTO unlocked_badges (
                    player_id, badge_id, unlocked_at
                )
                SELECT 1, badge_id, unlocked_at
                FROM unlocked_badges_legacy
                """
            )

        # Migrate Hero Boss progress.
        if "hero_boss_progress_legacy" in existing_tables:
            row = conn.execute(
                "SELECT * FROM hero_boss_progress_legacy LIMIT 1"
            ).fetchone()

            if row:
                conn.execute(
                    """
                    INSERT INTO hero_boss_progress (
                        player_id, consecutive_notes,
                        consecutive_chords, consecutive_arpeggios
                    )
                    VALUES (1, ?, ?, ?)
                    """,
                    (
                        row["consecutive_notes"],
                        row["consecutive_chords"],
                        row["consecutive_arpeggios"],
                    ),
                )

        # Persist the original player as the active player.
        conn.execute(
            """
            INSERT INTO app_settings (setting_key, setting_value)
            VALUES ('active_player_id', '1')
            """
        )

        # Remove temporary migration tables.
        for table in legacy_tables:
            legacy = f"{table}_legacy"
            if legacy in existing_tables:
                conn.execute(f"DROP TABLE {legacy}")

    def _create_schema(self, conn: sqlite3.Connection) -> None:
        """Create the multi-player schema within the caller's transaction."""

        statements = [
            """
            CREATE TABLE IF NOT EXISTS players (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS app_settings (
                setting_key TEXT PRIMARY KEY,
                setting_value TEXT NOT NULL
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS user_profile (
                player_id INTEGER PRIMARY KEY,
                total_xp INTEGER NOT NULL DEFAULT 0,
                user_level INTEGER NOT NULL DEFAULT 1,
                current_streak INTEGER NOT NULL DEFAULT 0,
                last_practice_date TEXT DEFAULT '',
                FOREIGN KEY (player_id)
                    REFERENCES players(id) ON DELETE CASCADE
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS practice_attempts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp REAL NOT NULL,
                view_mode TEXT NOT NULL,
                trainer_submode TEXT NOT NULL,
                target_name TEXT NOT NULL,
                response_time_sec REAL NOT NULL,
                is_correct INTEGER NOT NULL,
                xp_earned INTEGER NOT NULL,
                player_id INTEGER NOT NULL,
                FOREIGN KEY (player_id)
                    REFERENCES players(id) ON DELETE CASCADE
            )
            """,
            """
            CREATE INDEX IF NOT EXISTS idx_attempts_player
            ON practice_attempts(player_id)
            """,
            """
            CREATE TABLE IF NOT EXISTS unlocked_badges (
                player_id INTEGER NOT NULL,
                badge_id TEXT NOT NULL,
                unlocked_at REAL NOT NULL,
                PRIMARY KEY (player_id, badge_id),
                FOREIGN KEY (player_id)
                    REFERENCES players(id) ON DELETE CASCADE
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS hero_boss_progress (
                player_id INTEGER PRIMARY KEY,
                consecutive_notes INTEGER NOT NULL DEFAULT 0,
                consecutive_chords INTEGER NOT NULL DEFAULT 0,
                consecutive_arpeggios INTEGER NOT NULL DEFAULT 0,
                FOREIGN KEY (player_id)
                    REFERENCES players(id) ON DELETE CASCADE
            )
            """,
        ]

        for statement in statements:
            conn.execute(statement)
    def _create_missing_rows(self, conn: sqlite3.Connection) -> None:
        """Ensure every player has profile and Hero Boss records."""

        players = conn.execute("SELECT id FROM players").fetchall()

        if not players:
            now = datetime.now(timezone.utc).isoformat()
            conn.execute(
                "INSERT INTO players (id, name, created_at) VALUES (1, ?, ?)",
                ("Player 1", now),
            )
            players = conn.execute("SELECT id FROM players").fetchall()

        for player in players:
            player_id = player["id"]

            conn.execute(
                """
                INSERT OR IGNORE INTO user_profile (player_id)
                VALUES (?)
                """,
                (player_id,),
            )

            conn.execute(
                """
                INSERT OR IGNORE INTO hero_boss_progress (player_id)
                VALUES (?)
                """,
                (player_id,),
            )

        conn.execute(
            """
            INSERT OR IGNORE INTO app_settings (
                setting_key, setting_value
            )
            VALUES ('active_player_id', '1')
            """
        )

    # ============================================================
    # PLAYER MANAGEMENT
    # ============================================================

    def get_players(self) -> List[PlayerData]:
        with self._get_connection() as conn:
            rows = conn.execute(
                "SELECT id, name, created_at FROM players ORDER BY id"
            ).fetchall()

            return [
                PlayerData(
                    id=row["id"],
                    name=row["name"],
                    created_at=row["created_at"],
                )
                for row in rows
            ]

    def get_player(self, player_id: int) -> Optional[PlayerData]:
        with self._get_connection() as conn:
            row = conn.execute(
                """
                SELECT id, name, created_at
                FROM players
                WHERE id = ?
                """,
                (player_id,),
            ).fetchone()

            if row is None:
                return None

            return PlayerData(
                id=row["id"],
                name=row["name"],
                created_at=row["created_at"],
            )

    def create_player(self, name: str) -> int:
        name = name.strip()

        if not name:
            raise ValueError("Player name cannot be empty.")

        now = datetime.now(timezone.utc).isoformat()

        with self._get_connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO players (name, created_at)
                VALUES (?, ?)
                """,
                (name, now),
            )

            player_id = cursor.lastrowid

            conn.execute(
                "INSERT INTO user_profile (player_id) VALUES (?)",
                (player_id,),
            )

            conn.execute(
                "INSERT INTO hero_boss_progress (player_id) VALUES (?)",
                (player_id,),
            )

            conn.execute(
                """
                UPDATE app_settings
                SET setting_value = ?
                WHERE setting_key = 'active_player_id'
                """,
                (str(player_id),),
            )

            conn.commit()
            return player_id

    def get_active_player_id(self) -> int:
        with self._get_connection() as conn:
            row = conn.execute(
                """
                SELECT setting_value
                FROM app_settings
                WHERE setting_key = 'active_player_id'
                """
            ).fetchone()

            return int(row["setting_value"]) if row else 1

    def set_active_player_id(self, player_id: int) -> None:
        with self._get_connection() as conn:
            exists = conn.execute(
                "SELECT id FROM players WHERE id = ?",
                (player_id,),
            ).fetchone()

            if exists is None:
                raise ValueError(f"Player {player_id} does not exist.")

            conn.execute(
                """
                UPDATE app_settings
                SET setting_value = ?
                WHERE setting_key = 'active_player_id'
                """,
                (str(player_id),),
            )

            conn.commit()

    def _resolve_player_id(self, player_id: Optional[int]) -> int:
        resolved = (
            self.get_active_player_id()
            if player_id is None
            else player_id
        )

        if self.get_player(resolved) is None:
            raise ValueError(f"Player {resolved} does not exist.")

        return resolved

    # ============================================================
    # PROFILE AND XP OPERATIONS
    # ============================================================

    def get_user_profile(
        self,
        player_id: Optional[int] = None,
    ) -> UserProfileData:
        player_id = self._resolve_player_id(player_id)

        with self._get_connection() as conn:
            row = conn.execute(
                """
                SELECT total_xp, user_level,
                       current_streak, last_practice_date
                FROM user_profile
                WHERE player_id = ?
                """,
                (player_id,),
            ).fetchone()

            if row:
                return UserProfileData(
                    total_xp=row["total_xp"],
                    user_level=row["user_level"],
                    current_streak=row["current_streak"],
                    last_practice_date=row["last_practice_date"],
                )

            return UserProfileData()

    def update_user_profile(
        self,
        total_xp: int,
        user_level: int,
        current_streak: int,
        last_practice_date: str,
        player_id: Optional[int] = None,
    ) -> None:
        player_id = self._resolve_player_id(player_id)

        with self._get_connection() as conn:
            conn.execute(
                """
                UPDATE user_profile
                SET total_xp = ?,
                    user_level = ?,
                    current_streak = ?,
                    last_practice_date = ?
                WHERE player_id = ?
                """,
                (
                    total_xp,
                    user_level,
                    current_streak,
                    last_practice_date,
                    player_id,
                ),
            )

            conn.commit()

    # ============================================================
    # ATTEMPT LOGGING AND ANALYTICS
    # ============================================================

    def log_attempt(
        self,
        view_mode: str,
        trainer_submode: str,
        target_name: str,
        response_time_sec: float,
        is_correct: bool,
        xp_earned: int,
        player_id: Optional[int] = None,
    ) -> None:
        player_id = self._resolve_player_id(player_id)

        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO practice_attempts (
                    timestamp, view_mode, trainer_submode,
                    target_name, response_time_sec,
                    is_correct, xp_earned, player_id
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    time.time(),
                    view_mode,
                    trainer_submode,
                    target_name,
                    response_time_sec,
                    1 if is_correct else 0,
                    xp_earned,
                    player_id,
                ),
            )

            conn.commit()

    def get_analytics_summary(
        self,
        player_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        player_id = self._resolve_player_id(player_id)

        with self._get_connection() as conn:
            summary = conn.execute(
                """
                SELECT
                    COUNT(*) AS total,
                    SUM(is_correct) AS correct,
                    AVG(response_time_sec) AS avg_speed
                FROM practice_attempts
                WHERE player_id = ?
                """,
                (player_id,),
            ).fetchone()

            targets = conn.execute(
                """
                SELECT
                    target_name,
                    COUNT(*) AS cnt,
                    SUM(is_correct) AS correct
                FROM practice_attempts
                WHERE player_id = ?
                GROUP BY target_name
                """,
                (player_id,),
            ).fetchall()

            total = summary["total"] or 0
            correct = summary["correct"] or 0
            avg_speed = summary["avg_speed"] or 0.0

            accuracy = (
                correct / total * 100.0
                if total > 0
                else 0.0
            )

            return {
                "total_attempts": total,
                "correct_attempts": correct,
                "accuracy_percentage": round(accuracy, 1),
                "avg_response_speed_sec": round(avg_speed, 2),
                "target_breakdown": {
                    row["target_name"]: {
                        "attempts": row["cnt"],
                        "correct": row["correct"],
                    }
                    for row in targets
                },
            }

    # ============================================================
    # BADGE UNLOCKS
    # ============================================================

    def get_unlocked_badge_ids(
        self,
        player_id: Optional[int] = None,
    ) -> Set[str]:
        player_id = self._resolve_player_id(player_id)

        with self._get_connection() as conn:
            rows = conn.execute(
                """
                SELECT badge_id
                FROM unlocked_badges
                WHERE player_id = ?
                """,
                (player_id,),
            ).fetchall()

            return {row["badge_id"] for row in rows}

    def unlock_badge(
        self,
        badge_id: str,
        player_id: Optional[int] = None,
    ) -> bool:
        player_id = self._resolve_player_id(player_id)

        with self._get_connection() as conn:
            cursor = conn.execute(
                """
                INSERT OR IGNORE INTO unlocked_badges (
                    player_id, badge_id, unlocked_at
                )
                VALUES (?, ?, ?)
                """,
                (player_id, badge_id, time.time()),
            )

            conn.commit()
            return cursor.rowcount == 1

    # ============================================================
    # HERO BOSS PROGRESS
    # ============================================================

    def get_hero_boss_progress(
        self,
        player_id: Optional[int] = None,
    ) -> HeroBossData:
        player_id = self._resolve_player_id(player_id)

        with self._get_connection() as conn:
            row = conn.execute(
                """
                SELECT consecutive_notes,
                       consecutive_chords,
                       consecutive_arpeggios
                FROM hero_boss_progress
                WHERE player_id = ?
                """,
                (player_id,),
            ).fetchone()

            if row:
                return HeroBossData(
                    consecutive_notes=row["consecutive_notes"],
                    consecutive_chords=row["consecutive_chords"],
                    consecutive_arpeggios=row["consecutive_arpeggios"],
                )

            return HeroBossData()

    def update_hero_boss_progress(
        self,
        notes: int,
        chords: int,
        arpeggios: int,
        player_id: Optional[int] = None,
    ) -> None:
        player_id = self._resolve_player_id(player_id)

        with self._get_connection() as conn:
            conn.execute(
                """
                UPDATE hero_boss_progress
                SET consecutive_notes = ?,
                    consecutive_chords = ?,
                    consecutive_arpeggios = ?
                WHERE player_id = ?
                """,
                (notes, chords, arpeggios, player_id),
            )

            conn.commit()

    # ============================================================
    # RESET PLAYER PROGRESS
    # ============================================================

    def reset_player_progress(
        self,
        player_id: Optional[int] = None,
    ) -> None:
        """Reset all progress for one player without deleting the player."""

        player_id = self._resolve_player_id(player_id)

        with self._get_connection() as conn:
            conn.execute("BEGIN IMMEDIATE")

            conn.execute(
                """
                UPDATE user_profile
                SET total_xp = 0,
                    user_level = 1,
                    current_streak = 0,
                    last_practice_date = ''
                WHERE player_id = ?
                """,
                (player_id,),
            )

            conn.execute(
                "DELETE FROM practice_attempts WHERE player_id = ?",
                (player_id,),
            )

            conn.execute(
                "DELETE FROM unlocked_badges WHERE player_id = ?",
                (player_id,),
            )

            conn.execute(
                """
                UPDATE hero_boss_progress
                SET consecutive_notes = 0,
                    consecutive_chords = 0,
                    consecutive_arpeggios = 0
                WHERE player_id = ?
                """,
                (player_id,),
            )

            conn.commit()
