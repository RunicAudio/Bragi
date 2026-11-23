import pytest

from domain.gamification_policy import (
    SYSTEM_BADGES,
    GamificationPolicy,
    HeroBossProgress,
    MasteryTier,
)


# ============================================================
# LEVEL CALCULATION
# ============================================================

@pytest.mark.parametrize(
    ("total_xp", "expected_level"),
    [
        (0, 1),
        (1, 1),
        (49, 1),
        (50, 2),
        (199, 2),
        (200, 3),
        (449, 3),
        (450, 4),
        (800, 5),
        (1250, 6),
        (1800, 7),
        (5000, 11),
    ],
)
def test_calculate_level(total_xp, expected_level):
    assert GamificationPolicy.calculate_level(total_xp) == expected_level


def test_calculate_level_never_returns_below_one():
    assert GamificationPolicy.calculate_level(0) == 1


def test_calculate_level_increases_at_threshold():
    assert GamificationPolicy.calculate_level(49) == 1
    assert GamificationPolicy.calculate_level(50) == 2


# ============================================================
# XP CALCULATION
# ============================================================

def test_incorrect_attempt_awards_zero_xp():
    assert GamificationPolicy.calculate_attempt_xp(
        is_correct=False,
        response_time_sec=1.0,
        streak=10,
    ) == 0


def test_correct_attempt_base_xp():
    assert GamificationPolicy.calculate_attempt_xp(
        is_correct=True,
        response_time_sec=3.0,
        streak=0,
    ) == 15


def test_correct_attempt_under_two_seconds_gets_speed_bonus():
    assert GamificationPolicy.calculate_attempt_xp(
        is_correct=True,
        response_time_sec=1.5,
        streak=0,
    ) == 25


def test_exactly_two_seconds_gets_speed_bonus():
    assert GamificationPolicy.calculate_attempt_xp(
        is_correct=True,
        response_time_sec=2.0,
        streak=0,
    ) == 25


def test_over_two_seconds_does_not_get_speed_bonus():
    assert GamificationPolicy.calculate_attempt_xp(
        is_correct=True,
        response_time_sec=2.01,
        streak=0,
    ) == 15


def test_zero_response_time_does_not_get_speed_bonus():
    assert GamificationPolicy.calculate_attempt_xp(
        is_correct=True,
        response_time_sec=0.0,
        streak=0,
    ) == 15


# ============================================================
# STREAK BONUS
# ============================================================

@pytest.mark.parametrize(
    ("streak", "expected_xp"),
    [
        (0, 15),
        (1, 15),
        (2, 15),
        (3, 20),
        (4, 20),
        (5, 20),
        (6, 25),
        (8, 25),
        (9, 30),
        (12, 35),
        (15, 35),
        (30, 35),
    ],
)
def test_streak_bonus_calculation(streak, expected_xp):
    assert GamificationPolicy.calculate_attempt_xp(
        is_correct=True,
        response_time_sec=3.0,
        streak=streak,
    ) == expected_xp


def test_speed_and_streak_bonuses_stack():
    assert GamificationPolicy.calculate_attempt_xp(
        is_correct=True,
        response_time_sec=1.0,
        streak=6,
    ) == 35


def test_streak_bonus_is_capped():
    assert GamificationPolicy.calculate_attempt_xp(
        is_correct=True,
        response_time_sec=3.0,
        streak=100,
    ) == 35


# ============================================================
# HERO BOSS PROGRESS
# ============================================================

def test_hero_boss_default_progress():
    boss = HeroBossProgress()

    assert boss.consecutive_notes_under_2s == 0
    assert boss.consecutive_chords_under_2s == 0
    assert boss.consecutive_arpeggios_under_2s == 0
    assert boss.target_required_per_stage == 50


def test_hero_boss_notes_completion():
    boss = HeroBossProgress(consecutive_notes_under_2s=50)

    assert boss.notes_completed is True
    assert boss.chords_completed is False
    assert boss.arpeggios_completed is False
    assert boss.is_boss_defeated is False


def test_hero_boss_chords_completion():
    boss = HeroBossProgress(consecutive_chords_under_2s=50)

    assert boss.chords_completed is True
    assert boss.is_boss_defeated is False


def test_hero_boss_arpeggios_completion():
    boss = HeroBossProgress(consecutive_arpeggios_under_2s=50)

    assert boss.arpeggios_completed is True
    assert boss.is_boss_defeated is False


def test_hero_boss_requires_all_three_stages():
    boss = HeroBossProgress(
        consecutive_notes_under_2s=50,
        consecutive_chords_under_2s=50,
        consecutive_arpeggios_under_2s=49,
    )

    assert boss.notes_completed is True
    assert boss.chords_completed is True
    assert boss.arpeggios_completed is False
    assert boss.is_boss_defeated is False


def test_hero_boss_defeated_when_all_stages_complete():
    boss = HeroBossProgress(
        consecutive_notes_under_2s=50,
        consecutive_chords_under_2s=50,
        consecutive_arpeggios_under_2s=50,
    )

    assert boss.is_boss_defeated is True


def test_hero_boss_supports_custom_stage_requirement():
    boss = HeroBossProgress(
        consecutive_notes_under_2s=10,
        consecutive_chords_under_2s=10,
        consecutive_arpeggios_under_2s=10,
        target_required_per_stage=10,
    )

    assert boss.is_boss_defeated is True


def test_hero_boss_progress_can_exceed_requirement():
    boss = HeroBossProgress(
        consecutive_notes_under_2s=60,
        consecutive_chords_under_2s=60,
        consecutive_arpeggios_under_2s=60,
    )

    assert boss.is_boss_defeated is True


# ============================================================
# BADGE DEFINITIONS
# ============================================================

def test_system_badges_contains_40_badges():
    assert len(SYSTEM_BADGES) == 40


def test_system_badge_ids_are_unique():
    badge_ids = [badge.id for badge in SYSTEM_BADGES]

    assert len(badge_ids) == len(set(badge_ids))


@pytest.mark.parametrize(
    "category",
    ["TRAINER", "TUNER", "EAR_TRAINING", "ANALYTICS"],
)
def test_badges_have_valid_view_categories(category):
    assert any(
        badge.view_category == category
        for badge in SYSTEM_BADGES
    )


def test_all_badges_have_required_fields():
    for badge in SYSTEM_BADGES:
        assert badge.id
        assert badge.title
        assert badge.description
        assert badge.view_category
        assert badge.icon_name
        assert isinstance(badge.tier, MasteryTier)


def test_all_badges_start_locked():
    assert all(badge.unlocked is False for badge in SYSTEM_BADGES)


def test_badge_tiers_are_valid():
    valid_tiers = set(MasteryTier)

    for badge in SYSTEM_BADGES:
        assert badge.tier in valid_tiers
