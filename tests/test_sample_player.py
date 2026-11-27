import numpy as np
import pytest
from unittest.mock import MagicMock

from dsp.sample_player import SamplePlayer
from domain.music_theory import (
    PIANO_MIN_MIDI,
    PIANO_MAX_MIDI,
)


@pytest.fixture
def player():
    return SamplePlayer(sample_rate=8000)


class TestMidiValidation:

    @pytest.mark.parametrize(
        "midi_number",
        [PIANO_MIN_MIDI, 60, 69, PIANO_MAX_MIDI],
    )
    def test_accepts_valid_midi_notes(self, player, midi_number):
        player._validate_midi_notes([midi_number])

    @pytest.mark.parametrize(
        "midi_number",
        [20, 109, -1, 200, 60.5, "60", None, True],
    )
    def test_rejects_invalid_midi_notes(self, player, midi_number):
        with pytest.raises(ValueError):
            player._validate_midi_notes([midi_number])

    def test_rejects_invalid_sample_rate(self):
        with pytest.raises(ValueError):
            SamplePlayer(sample_rate=0)

        with pytest.raises(ValueError):
            SamplePlayer(sample_rate=44100.5)

    def test_rejects_invalid_playback_level(self, player):
        with pytest.raises(ValueError):
            player._validate_playback_settings(1.0, 0)

        with pytest.raises(ValueError):
            player._validate_playback_settings(1.0, 1.1)

    def test_rejects_invalid_duration(self, player):
        with pytest.raises(ValueError):
            player._validate_playback_settings(0, 0.7)


class TestAudioRendering:

    def test_renders_single_midi_note(self, player):
        audio = player._render_midi_notes(
            [60],
            duration_sec=1.0,
            level=0.7,
        )

        assert isinstance(audio, np.ndarray)
        assert audio.dtype == np.float32
        assert len(audio) == 8000
        assert np.max(np.abs(audio)) <= 0.701
        assert np.max(np.abs(audio)) > 0

    def test_renders_different_octaves_differently(self, player):
        c4 = player._render_midi_notes([60], 1.0, 0.7)
        c5 = player._render_midi_notes([72], 1.0, 0.7)

        assert not np.array_equal(c4, c5)

    def test_renders_simultaneous_chord(self, player):
        audio = player._render_midi_notes(
            [60, 64, 67],
            duration_sec=1.0,
            level=0.7,
        )

        assert len(audio) == 8000
        assert np.max(np.abs(audio)) <= 0.701
        assert np.any(audio != 0)

    def test_renders_full_piano_range(self, player):
        low_note = player._render_midi_notes([21], 1.0, 0.7)
        high_note = player._render_midi_notes([108], 1.0, 0.7)

        assert np.any(low_note != 0)
        assert np.any(high_note != 0)

    def test_rejects_invalid_midi_note_during_public_playback(self, player):
        with pytest.raises(ValueError):
            player.play_midi_note(109)


class TestMelodicSequences:

    def test_renders_two_note_sequence(self, player):
        audio = player._render_midi_sequence(
            [60, 64],
            note_duration_sec=0.5,
            gap_sec=0.2,
            level=0.7,
        )

        expected_samples = int(8000 * (0.5 + 0.2 + 0.5))

        assert len(audio) == expected_samples

    def test_renders_three_note_sequence(self, player):
        audio = player._render_midi_sequence(
            [60, 64, 67],
            note_duration_sec=0.5,
            gap_sec=0.2,
            level=0.7,
        )

        expected_samples = int(8000 * (0.5 * 3 + 0.2 * 2))

        assert len(audio) == expected_samples

    def test_preserves_spacing_between_repeated_notes(self, player):
        audio = player._render_midi_sequence(
            [60, 60, 60],
            note_duration_sec=0.5,
            gap_sec=0.2,
            level=0.7,
        )

        expected_samples = int(8000 * (0.5 * 3 + 0.2 * 2))

        assert len(audio) == expected_samples

    def test_zero_gap_creates_contiguous_notes(self, player):
        audio = player._render_midi_sequence(
            [60, 64],
            note_duration_sec=0.5,
            gap_sec=0,
            level=0.7,
        )

        assert len(audio) == 8000


class TestPlaybackAPI:

    def test_play_midi_note_enqueues_audio(self, player, monkeypatch):
        enqueue = MagicMock()
        monkeypatch.setattr(player, "_enqueue", enqueue)

        player.play_midi_note(60)

        enqueue.assert_called_once()

    def test_play_midi_notes_enqueues_audio(self, player, monkeypatch):
        enqueue = MagicMock()
        monkeypatch.setattr(player, "_enqueue", enqueue)

        player.play_midi_notes([60, 64, 67])

        enqueue.assert_called_once()

    def test_play_melodic_interval_enqueues_audio(self, player, monkeypatch):
        enqueue = MagicMock()
        monkeypatch.setattr(player, "_enqueue", enqueue)

        player.play_melodic_interval(60, 64)

        enqueue.assert_called_once()

    def test_play_midi_sequence_enqueues_audio(self, player, monkeypatch):
        enqueue = MagicMock()
        monkeypatch.setattr(player, "_enqueue", enqueue)

        player.play_midi_sequence([60, 64, 67])

        enqueue.assert_called_once()

    def test_empty_chord_does_not_enqueue_audio(self, player, monkeypatch):
        enqueue = MagicMock()
        monkeypatch.setattr(player, "_enqueue", enqueue)

        player.play_midi_notes([])

        enqueue.assert_not_called()

    def test_empty_sequence_does_not_enqueue_audio(self, player, monkeypatch):
        enqueue = MagicMock()
        monkeypatch.setattr(player, "_enqueue", enqueue)

        player.play_midi_sequence([])

        enqueue.assert_not_called()


class TestBackwardCompatibility:

    def test_pitch_class_playback_uses_midi_api(self, player, monkeypatch):
        play_mock = MagicMock()
        monkeypatch.setattr(player, "play_midi_notes", play_mock)

        player.play_pitch_classes({0, 4, 7}, base_octave=4)

        play_mock.assert_called_once_with(
            [60, 64, 67],
            duration_sec=1.2,
        )

    def test_note_name_playback_uses_midi_api(self, player, monkeypatch):
        play_mock = MagicMock()
        monkeypatch.setattr(player, "play_midi_note", play_mock)

        player.play_note("C", octave=4)

        play_mock.assert_called_once_with(
            60,
            duration_sec=1.0,
        )

    def test_invalid_note_name_is_ignored(self, player, monkeypatch):
        play_mock = MagicMock()
        monkeypatch.setattr(player, "play_midi_note", play_mock)

        player.play_note("InvalidNote")

        play_mock.assert_not_called()
