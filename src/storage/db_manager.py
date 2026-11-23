"""
src/storage/db_manager.py
=========================
Thread-safe SQLite database manager for user analytics, practice logs,
badge unlocks, and Hero Boss gauntlet progression.
"""

from dataclasses import dataclass, field
from datetime import date
import sqlite3
import threading
import time
from typing import Any, Dict, List, Optional, Set, Tuple

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
        conn.execute("PRAGMA journal_mode=WAL;")
        return conn

    def _init_db(self) -> None:
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # User profile table
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS user_profile (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    total_xp INTEGER NOT NULL DEFAULT 0,
                    user_level INTEGER NOT NULL DEFAULT 1,
                    current_streak INTEGER NOT NULL DEFAULT 0,
                    last_practice_date TEXT DEFAULT ''
                );
            """
            )

            # Ensure singleton profile row exists
            cursor.execute(
                """
                INSERT OR IGNORE INTO user_profile (id, total_xp, user_level, current_streak, last_practice_date)
                VALUES (1, 0, 1, 0, '');
            """
            )

            # Practice history log
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS practice_attempts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp REAL NOT NULL,
                    view_mode TEXT NOT NULL,
                    trainer_submode TEXT NOT NULL,
                    target_name TEXT NOT NULL,
                    response_time_sec REAL NOT NULL,
                    is_correct INTEGER NOT NULL,
                    xp_earned INTEGER NOT NULL
                );
            """
            )

            # Unlocked badges tracking
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS unlocked_badges (
                    badge_id TEXT PRIMARY KEY,
                    unlocked_at REAL NOT NULL
                );
            """
            )

            # Hero Boss Gauntlet state
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS hero_boss_progress (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    consecutive_notes INTEGER NOT NULL DEFAULT 0,
                    consecutive_chords INTEGER NOT NULL DEFAULT 0,
                    consecutive_arpeggios INTEGER NOT NULL DEFAULT 0
                );
            """
            )

            # Ensure singleton boss progress row exists
            cursor.execute(
                """
                INSERT OR IGNORE INTO hero_boss_progress (id, consecutive_notes, consecutive_chords, consecutive_arpeggios)
                VALUES (1, 0, 0, 0);
            """
            )

            conn.commit()

    # --- Profile & XP Operations ---

    def get_user_profile(self) -> UserProfileData:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT total_xp, user_level, current_streak, last_practice_date FROM user_profile WHERE id = 1"
            )
            row = cursor.fetchone()
            if row:
                return UserProfileData(
                    total_xp=row["total_xp"],
                    user_level=row["user_level"],
                    current_streak=row["current_streak"],
                    last_practice_date=row["last_practice_date"],
                )
            return UserProfileData()

    def update_user_profile(self, total_xp: int, user_level: int, current_streak: int, last_practice_date: str) -> None:
        with self._get_connection() as conn:
            conn.execute(
                """
                UPDATE user_profile
                SET total_xp = ?, user_level = ?, current_streak = ?, last_practice_date = ?
                WHERE id = 1;
            """,
                (total_xp, user_level, current_streak, last_practice_date),
            )
            conn.commit()

    # --- Attempt Logging & Analytics ---

    def log_attempt(
        self,
        view_mode: str,
        trainer_submode: str,
        target_name: str,
        response_time_sec: float,
        is_correct: bool,
        xp_earned: int,
    ) -> None:
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO practice_attempts (timestamp, view_mode, trainer_submode, target_name, response_time_sec, is_correct, xp_earned)
                VALUES (?, ?, ?, ?, ?, ?, ?);
            """,
                (
                    time.time(),
                    view_mode,
                    trainer_submode,
                    target_name,
                    response_time_sec,
                    1 if is_correct else 0,
                    xp_earned,
                ),
            )
            conn.commit()

    def get_analytics_summary(self) -> Dict[str, Any]:
        with self._get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("SELECT COUNT(*) as total, SUM(is_correct) as correct, AVG(response_time_sec) as avg_speed FROM practice_attempts;")
            summary_row = cursor.fetchone()

            cursor.execute("SELECT target_name, COUNT(*) as cnt, SUM(is_correct) as correct FROM practice_attempts GROUP BY target_name;")
            target_rows = cursor.fetchall()

            total_attempts = summary_row["total"] if summary_row and summary_row["total"] else 0
            correct_attempts = summary_row["correct"] if summary_row and summary_row["correct"] else 0
            avg_speed = summary_row["avg_speed"] if summary_row and summary_row["avg_speed"] else 0.0

            accuracy = (correct_attempts / total_attempts * 100.0) if total_attempts > 0 else 0.0

            return {
                "total_attempts": total_attempts,
                "correct_attempts": correct_attempts,
                "accuracy_percentage": round(accuracy, 1),
                "avg_response_speed_sec": round(avg_speed, 2),
                "target_breakdown": {row["target_name"]: {"attempts": row["cnt"], "correct": row["correct"]} for row in target_rows},
            }

    # --- Badge Unlocks ---

    def get_unlocked_badge_ids(self) -> Set[str]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT badge_id FROM unlocked_badges;")
            return {row["badge_id"] for row in cursor.fetchall()}

    def unlock_badge(self, badge_id: str) -> bool:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT badge_id FROM unlocked_badges WHERE badge_id = ?;", (badge_id,))
            if cursor.fetchone() is None:
                cursor.execute("INSERT INTO unlocked_badges (badge_id, unlocked_at) VALUES (?, ?);", (badge_id, time.time()))
                conn.commit()
                return True
            return False

    # --- Hero Boss Progress ---

    def get_hero_boss_progress(self) -> HeroBossData:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT consecutive_notes, consecutive_chords, consecutive_arpeggios FROM hero_boss_progress WHERE id = 1;")
            row = cursor.fetchone()
            if row:
                return HeroBossData(
                    consecutive_notes=row["consecutive_notes"],
                    consecutive_chords=row["consecutive_chords"],
                    consecutive_arpeggios=row["consecutive_arpeggios"],
                )
            return HeroBossData()

    def update_hero_boss_progress(self, notes: int, chords: int, arpeggios: int) -> None:
        with self._get_connection() as conn:
            conn.execute(
                """
                UPDATE hero_boss_progress
                SET consecutive_notes = ?, consecutive_chords = ?, consecutive_arpeggios = ?
                WHERE id = 1;
            """,
                (notes, chords, arpeggios),
            )
            conn.commit()
