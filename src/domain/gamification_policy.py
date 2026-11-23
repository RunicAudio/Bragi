"""
src/domain/gamification_policy.py
=================================
Gamification rules governing XP rewards, 40 total view badges across 3 tiers,
and the Level 4 'Hero Level' Final Boss Challenge requirement.
"""

from dataclasses import dataclass, field
from enum import Enum
import math
from typing import List, Tuple


class MasteryTier(str, Enum):
    BEGINNER = "Beginner"
    INTERMEDIATE = "Intermediate"
    ADVANCED = "Advanced"
    HERO = "Hero Level"


@dataclass
class BadgeDefinition:
    id: str
    title: str
    description: str
    view_category: str  # TRAINER, TUNER, EAR_TRAINING, ANALYTICS
    tier: MasteryTier
    icon_name: str
    unlocked: bool = False


@dataclass
class HeroBossProgress:
    """Tracks continuous gauntlet progress for the Level 4 Hero Level Final Boss."""
    consecutive_notes_under_2s: int = 0
    consecutive_chords_under_2s: int = 0
    consecutive_arpeggios_under_2s: int = 0
    target_required_per_stage: int = 50

    @property
    def notes_completed(self) -> bool:
        return self.consecutive_notes_under_2s >= self.target_required_per_stage

    @property
    def chords_completed(self) -> bool:
        return self.consecutive_chords_under_2s >= self.target_required_per_stage

    @property
    def arpeggios_completed(self) -> bool:
        return self.consecutive_arpeggios_under_2s >= self.target_required_per_stage

    @property
    def is_boss_defeated(self) -> bool:
        return self.notes_completed and self.chords_completed and self.arpeggios_completed


# 10 Badges per View across 3 Tiers (30 standard badges + 10 analytics/hero badges)
SYSTEM_BADGES: List[BadgeDefinition] = [
    # Trainer View Badges
    BadgeDefinition("tr_b1", "First Note", "Match 1 note target", "TRAINER", MasteryTier.BEGINNER, "MUSIC_NOTE"),
    BadgeDefinition("tr_b2", "Note Novice", "Match 10 notes under 3s", "TRAINER", MasteryTier.BEGINNER, "TIMER"),
    BadgeDefinition("tr_b3", "Strum Starter", "Match 5 strummed chords", "TRAINER", MasteryTier.BEGINNER, "TUNE"),
    BadgeDefinition("tr_i1", "Speed Demon", "Match 15 notes under 2s each", "TRAINER", MasteryTier.INTERMEDIATE, "BOLT"),
    BadgeDefinition("tr_i2", "Chord Detective", "Match 20 chords successfully", "TRAINER", MasteryTier.INTERMEDIATE, "EXPLORER"),
    BadgeDefinition("tr_i3", "Arpeggio Picker", "Complete 10 arpeggiated chords", "TRAINER", MasteryTier.INTERMEDIATE, "GRAIN"),
    BadgeDefinition("tr_a1", "Fretboard Master", "Achieve 95% accuracy over 50 attempts", "TRAINER", MasteryTier.ADVANCED, "STAR"),
    BadgeDefinition("tr_a2", "Lightning Reflexes", "Match a note under 1.0 second", "TRAINER", MasteryTier.ADVANCED, "FLASH_ON"),
    BadgeDefinition("tr_a3", "CAGED Expert", "Complete 30 CAGED chord voicings", "TRAINER", MasteryTier.ADVANCED, "GRID_ON"),
    BadgeDefinition("tr_a4", "Streak Legend", "Reach a 25-note consecutive streak", "TRAINER", MasteryTier.ADVANCED, "LOCAL_FIRE_DEPARTMENT"),

    # Tuner View Badges
    BadgeDefinition("tn_b1", "Pitch Conscious", "Open Tuner view for first time", "TUNER", MasteryTier.BEGINNER, "TUNE"),
    BadgeDefinition("tn_b2", "In Tune Standard", "Tune Low E string perfectly", "TUNER", MasteryTier.BEGINNER, "CHECK_CIRCLE"),
    BadgeDefinition("tn_b3", "String Setter", "Tune all 6 strings in standard tuning", "TUNER", MasteryTier.BEGINNER, "SETTINGS_VOICE"),
    BadgeDefinition("tn_i1", "Cents Precision", "Hold pitch within 3 cents for 3s", "TUNER", MasteryTier.INTERMEDIATE, "GPS_FIXED"),
    BadgeDefinition("tn_i2", "Alt Tuning Explorer", "Tune to Drop D or Open G tuning", "TUNER", MasteryTier.INTERMEDIATE, "ALT_ROUTE"),
    BadgeDefinition("tn_i3", "Quick Pitch", "Tune entire instrument under 30 seconds", "TUNER", MasteryTier.INTERMEDIATE, "SPEED"),
    BadgeDefinition("tn_a1", "Master Luthier", "Tune 5 distinct custom tunings", "TUNER", MasteryTier.ADVANCED, "BUILD"),
    BadgeDefinition("tn_a2", "Micro-Tuner", "Zero-out pitch cents 50 times", "TUNER", MasteryTier.ADVANCED, "CENTER_FOCUS_STRONG"),
    BadgeDefinition("tn_a3", "Ear Tuner", "Tune string without reference visual aid", "TUNER", MasteryTier.ADVANCED, "HEARING"),
    BadgeDefinition("tn_a4", "Perfect Pitch Lock", "Maintain zero-cents lock for 5s", "TUNER", MasteryTier.ADVANCED, "LOCK"),

    # Ear Training View Badges
    BadgeDefinition("et_b1", "Listener", "Complete 1 ear training exercise", "EAR_TRAINING", MasteryTier.BEGINNER, "HEARING"),
    BadgeDefinition("et_b2", "Thirds Listener", "Identify Major 3rd interval", "EAR_TRAINING", MasteryTier.BEGINNER, "MUSIC_NOTE"),
    BadgeDefinition("et_b3", "Triad Ear", "Distinguish Major vs Minor chord", "EAR_TRAINING", MasteryTier.BEGINNER, "GRAPHIC_EQ"),
    BadgeDefinition("et_i1", "Interval Scholar", "Identify 15 intervals correctly", "EAR_TRAINING", MasteryTier.INTERMEDIATE, "SCHOOL"),
    BadgeDefinition("et_i2", "7th Chord Ear", "Identify Dominant 7th vs Major 7th", "EAR_TRAINING", MasteryTier.INTERMEDIATE, "LIB_MUSIC"),
    BadgeDefinition("et_i3", "Pitch Identifier", "Identify 10 single pitches by ear", "EAR_TRAINING", MasteryTier.INTERMEDIATE, "MIC_NONE"),
    BadgeDefinition("et_a1", "Perfect Ear", "Get 20 consecutive ear answers correct", "EAR_TRAINING", MasteryTier.ADVANCED, "VERIFIED"),
    BadgeDefinition("et_a2", "Inversion Listener", "Identify 10 inverted chord voicings", "EAR_TRAINING", MasteryTier.ADVANCED, "SWAP_VERT"),
    BadgeDefinition("et_a3", "Prodigy Hearing", "Complete 50 ear exercises", "EAR_TRAINING", MasteryTier.ADVANCED, "EMOJI_EVENTS"),
    BadgeDefinition("et_a4", "Chromatic Ear Master", "Identify all 12 intervals without error", "EAR_TRAINING", MasteryTier.ADVANCED, "AUTO_AWESOME"),

    # Analytics View & Hero Boss Badges
    BadgeDefinition("an_b1", "Data Tracker", "View Analytics dashboard", "ANALYTICS", MasteryTier.BEGINNER, "BAR_CHART"),
    BadgeDefinition("an_b2", "XP Collector", "Earn your first 100 XP", "ANALYTICS", MasteryTier.BEGINNER, "ADD_REACTION"),
    BadgeDefinition("an_b3", "Consistency", "Maintain a 3-day practice streak", "ANALYTICS", MasteryTier.BEGINNER, "DATE_RANGE"),
    BadgeDefinition("an_i1", "Level 5 Achiever", "Reach User Level 5", "ANALYTICS", MasteryTier.INTERMEDIATE, "MILITARY_TECH"),
    BadgeDefinition("an_i2", "Mastery Bronze", "Reach Bronze tier on all 12 notes", "ANALYTICS", MasteryTier.INTERMEDIATE, "WORKSPACE_PREMIUM"),
    BadgeDefinition("an_i3", "Dedicated Musician", "Log 50 total practice attempts", "ANALYTICS", MasteryTier.INTERMEDIATE, "FITNESS_CENTER"),
    BadgeDefinition("an_a1", "Level 10 Master", "Reach User Level 10", "ANALYTICS", MasteryTier.ADVANCED, "SHIELD"),
    BadgeDefinition("an_a2", "Gold Chromatic", "Reach Gold tier on all 12 notes", "ANALYTICS", MasteryTier.ADVANCED, "STAR_HALF"),
    BadgeDefinition("an_a3", "Streak Titan", "Maintain a 14-day practice streak", "ANALYTICS", MasteryTier.ADVANCED, "WHATSHOT"),
    BadgeDefinition("an_hero", "Fretboard Hero (Final Boss)", "50 notes + 50 chords + 50 arpeggios in a row under 2s", "ANALYTICS", MasteryTier.HERO, "MILITARY_TECH"),
]


class GamificationPolicy:
    """Calculates user level formulas, streaks, and Hero Boss Challenge qualification."""

    @staticmethod
    def calculate_level(total_xp: int) -> int:
        if total_xp <= 0:
            return 1
        return int(math.floor(math.sqrt(total_xp / 50.0))) + 1

    @staticmethod
    def calculate_attempt_xp(is_correct: bool, response_time_sec: float, streak: int) -> int:
        if not is_correct:
            return 0
        base_xp = 15
        if 0.0 < response_time_sec <= 2.0:
            base_xp += 10
        streak_bonus = min(20, (streak // 3) * 5)
        return base_xp + streak_bonus
