import pytest
import numpy as np
from unittest.mock import MagicMock, call

from dsp.audio_engine import AudioEngine
from core.app_state import LivePitch


class FakeAppState:
    def __init__(self):
        self.updated_pitch = None

    def update_live_pitch(self, pitch):
        self.updated_pitch = pitch


@pytest.fixture
def audio_engine(monkeypatch):
    fake_state = FakeAppState()

    class FakeDatabase:
        def __init__(self):
            self.settings = {}

        def get_setting(self, key, default=None):
            return self.settings.get(key, default)

        def set_setting(self, key, value):
            self.settings[key] = value

    fake_db = FakeDatabase()

    devices = [
        {
            "name": "Output Device",
            "max_input_channels": 0,
            "default_samplerate": 44100,
            "hostapi": 1,
        },
        {
            "name": "Microphone Array",
            "max_input_channels": 2,
            "default_samplerate": 44100,
            "hostapi": 1,
        },
        {
            "name": "Multichannel (HeadRush Core)",
            "max_input_channels": 6,
            "default_samplerate": 48000,
            "hostapi": 1,
        },
    ]

    host_apis = [
        {
            "name": "MME",
            "default_input_device": -1,
        },
        {
            "name": "Windows WASAPI",
            "default_input_device": 2,
        },
    ]

    monkeypatch.setattr(
        "dsp.audio_engine.AppState.get_instance",
        lambda: fake_state,
    )

    monkeypatch.setattr(
        "dsp.audio_engine.DatabaseManager.get_instance",
        lambda: fake_db,
    )

    monkeypatch.setattr(
        "dsp.audio_engine.sys.platform",
        "win32",
    )

    monkeypatch.setattr(
        "dsp.audio_engine.sd.query_devices",
        lambda *args, **kwargs: (
            devices if not args else devices[args[0]]
        ),
    )

    monkeypatch.setattr(
        "dsp.audio_engine.sd.query_hostapis",
        lambda *args, **kwargs: host_apis,
    )

    monkeypatch.setattr(
        "dsp.audio_engine.sd.default.device",
        [1, -1],
    )

    engine = AudioEngine()

    yield engine

    engine.stop()


class TestAudioEngineInitialization:

    def test_initializes_with_default_sample_rate(self, audio_engine):
        assert audio_engine.sample_rate == 44100

    def test_initializes_with_default_block_size(self, audio_engine):
        assert audio_engine.block_size == 2048

    def test_initializes_selected_device(self, audio_engine):
        assert audio_engine.device_id == 2

    def test_initializes_stopped(self, audio_engine):
        assert audio_engine.is_running is False

    def test_initializes_4096_sample_buffer(self, audio_engine):
        assert len(audio_engine._pcm_buffer) == 4096

    def test_initializes_empty_audio_queue(self, audio_engine):
        assert audio_engine._audio_queue.empty()

    def test_initializes_dsp_components_at_matching_sample_rate(
        self, audio_engine
    ):
        assert audio_engine.pitch_tracker.sample_rate == 44100
        assert audio_engine.chroma_analyzer.sample_rate == 44100


class TestAudioDeviceDiscovery:

    def test_selects_windows_wasapi(self, audio_engine):
        assert audio_engine.device_id == 2
        assert audio_engine.device_key is not None
        assert "Windows WASAPI" in audio_engine.device_key

    def test_selects_macos_core_audio(self, audio_engine, monkeypatch):
        monkeypatch.setattr(
            "dsp.audio_engine.sys.platform",
            "darwin",
        )

        host_apis = [
            {"name": "MME", "default_input_device": -1},
            {"name": "Core Audio", "default_input_device": 2},
        ]

        monkeypatch.setattr(
            "dsp.audio_engine.sd.query_hostapis",
            lambda: host_apis,
        )

        assert audio_engine._select_input_host_api(
            host_apis,
            [
                {"hostapi": 0, "max_input_channels": 2},
                {"hostapi": 1, "max_input_channels": 2},
            ],
        ) == 1

    def test_prefers_linux_pulseaudio(self, audio_engine, monkeypatch):
        monkeypatch.setattr(
            "dsp.audio_engine.sys.platform",
            "linux",
        )

        host_apis = [
            {"name": "ALSA", "default_input_device": 1},
            {"name": "PulseAudio", "default_input_device": 2},
        ]

        assert audio_engine._select_input_host_api(
            host_apis,
            [
                {"hostapi": 0, "max_input_channels": 2},
                {"hostapi": 1, "max_input_channels": 2},
            ],
        ) == 1

    def test_falls_back_to_linux_alsa(self, audio_engine, monkeypatch):
        monkeypatch.setattr(
            "dsp.audio_engine.sys.platform",
            "linux",
        )

        host_apis = [
            {"name": "ALSA", "default_input_device": 1},
            {"name": "JACK", "default_input_device": -1},
        ]

        assert audio_engine._select_input_host_api(
            host_apis,
            [
                {"hostapi": 0, "max_input_channels": 2},
                {"hostapi": 1, "max_input_channels": 2},
            ],
        ) == 0

    def test_excludes_output_only_devices(self, audio_engine):
        devices = audio_engine.get_input_devices()

        assert all(device["channels"] > 0 for device in devices)
        assert all(device["host_api"] == "Windows WASAPI" for device in devices)

        assert len(devices) == 2

    def test_marks_host_api_default_input(self, audio_engine):
        devices = audio_engine.get_input_devices()

        default_devices = [
            device for device in devices
            if device["is_default"]
        ]

        assert len(default_devices) == 1
        assert default_devices[0]["id"] == 2

    def test_restores_saved_device(self, audio_engine):
        devices = audio_engine.get_input_devices()
        saved_device = devices[0]

        audio_engine.db.set_setting(
            "audio_input_device",
            saved_device["key"],
        )

        audio_engine._initialize_input_device()

        assert audio_engine.device_key == saved_device["key"]
        assert audio_engine.device_id == saved_device["id"]

    def test_falls_back_when_saved_device_is_missing(self, audio_engine):
        audio_engine.db.set_setting(
            "audio_input_device",
            "Missing API|Disconnected Device|2ch",
        )

        audio_engine._initialize_input_device()

        assert audio_engine.device_id == 2
        assert audio_engine.device_key is not None

    def test_persists_selected_device(self, audio_engine, monkeypatch):
        devices = audio_engine.get_input_devices()
        selected_device = devices[0]

        mock_stop = MagicMock()
        mock_start = MagicMock()

        monkeypatch.setattr(audio_engine, "stop", mock_stop)
        monkeypatch.setattr(audio_engine, "start", mock_start)

        audio_engine.set_device(selected_device["key"])

        assert audio_engine.db.get_setting(
            "audio_input_device"
        ) == selected_device["key"]

        assert audio_engine.device_id == selected_device["id"]
        assert audio_engine.device_key == selected_device["key"]

        mock_stop.assert_called_once()
        mock_start.assert_called_once()

class TestAudioStreamLifecycle:

    def test_starts_stream_at_native_sample_rate(
        self, audio_engine, monkeypatch
    ):
        mock_stream = MagicMock()

        monkeypatch.setattr(
            "dsp.audio_engine.sd.query_devices",
            lambda *args, **kwargs: {"default_samplerate": 44100},
        )

        monkeypatch.setattr(
            "dsp.audio_engine.sd.InputStream",
            lambda **kwargs: mock_stream,
        )

        audio_engine.start()

        try:
            assert audio_engine.is_running is True
            assert audio_engine.sample_rate == 44100
            assert audio_engine.stream is mock_stream
            mock_stream.start.assert_called_once()
        finally:
            audio_engine.stop()

        mock_stream.stop.assert_called_once()
        mock_stream.close.assert_called_once()

    def test_falls_back_to_48000_when_native_rate_fails(
        self, audio_engine, monkeypatch
    ):
        streams = []

        def create_stream(**kwargs):
            stream = MagicMock()
            streams.append((kwargs, stream))

            if kwargs["samplerate"] == 44100:
                raise RuntimeError("Unsupported sample rate")

            return stream

        monkeypatch.setattr(
            "dsp.audio_engine.sd.query_devices",
            lambda *args, **kwargs: {"default_samplerate": 44100},
        )

        monkeypatch.setattr(
            "dsp.audio_engine.sd.InputStream",
            create_stream,
        )

        audio_engine.start()

        try:
            assert len(streams) == 2
            assert streams[0][0]["samplerate"] == 44100
            assert streams[1][0]["samplerate"] == 48000

            assert audio_engine.sample_rate == 48000
            assert audio_engine.stream is streams[1][1]
            streams[1][1].start.assert_called_once()
        finally:
            audio_engine.stop()

    def test_closes_failed_stream_before_fallback(
        self, audio_engine, monkeypatch
    ):
        streams = []

        def create_stream(**kwargs):
            stream = MagicMock()
            streams.append(stream)

            if len(streams) == 1:
                stream.start.side_effect = RuntimeError(
                    "First stream failed to start"
                )

            return stream

        monkeypatch.setattr(
            "dsp.audio_engine.sd.query_devices",
            lambda *args, **kwargs: {"default_samplerate": 44100},
        )

        monkeypatch.setattr(
            "dsp.audio_engine.sd.InputStream",
            create_stream,
        )

        audio_engine.start()

        try:
            assert len(streams) == 2

            streams[0].start.assert_called_once()
            streams[0].close.assert_called_once()

            streams[1].start.assert_called_once()

            assert audio_engine.stream is streams[1]
            assert audio_engine.sample_rate == 48000

        finally:
            audio_engine.stop()

    def test_retries_with_more_channels_when_mono_is_unsupported(
        self, audio_engine, monkeypatch
    ):
        stream_attempts = []

        def create_stream(**kwargs):
            stream_attempts.append(kwargs)

            if kwargs["channels"] < 6:
                raise RuntimeError("Invalid number of channels")

            return MagicMock()

        monkeypatch.setattr(
            "dsp.audio_engine.sd.query_devices",
            lambda *args, **kwargs: {
                "default_samplerate": 48000,
                "max_input_channels": 6,
            },
        )

        monkeypatch.setattr(
            "dsp.audio_engine.sd.InputStream",
            create_stream,
        )

        audio_engine.start()

        try:
            assert audio_engine.is_running is True
            assert audio_engine.sample_rate == 48000
            assert audio_engine.stream is not None

            assert [
                attempt["channels"]
                for attempt in stream_attempts
            ] == [1, 2, 3, 4, 5, 6]

            assert all(
                attempt["samplerate"] == 48000
                for attempt in stream_attempts
            )

            audio_engine.stream.start.assert_called_once()

        finally:
            audio_engine.stop()

    def test_stops_cleanly_when_already_stopped(self, audio_engine):
        audio_engine.stop()

        assert audio_engine.is_running is False
        assert audio_engine.stream is None
        assert audio_engine._dsp_thread is None

    def test_does_not_start_duplicate_stream(
        self, audio_engine, monkeypatch
    ):
        mock_stream = MagicMock()

        monkeypatch.setattr(
            "dsp.audio_engine.sd.query_devices",
            lambda *args, **kwargs: {"default_samplerate": 44100},
        )

        mock_factory = MagicMock(return_value=mock_stream)

        monkeypatch.setattr(
            "dsp.audio_engine.sd.InputStream",
            mock_factory,
        )

        audio_engine.start()

        try:
            audio_engine.start()

            assert mock_factory.call_count == 1
            mock_stream.start.assert_called_once()
        finally:
            audio_engine.stop()
    def test_shuts_down_worker_when_all_stream_attempts_fail(
        self, audio_engine, monkeypatch
    ):
        monkeypatch.setattr(
            "dsp.audio_engine.sd.query_devices",
            lambda *args, **kwargs: {"default_samplerate": 44100},
        )

        mock_stream = MagicMock()
        mock_stream.start.side_effect = RuntimeError("Device unavailable")

        monkeypatch.setattr(
            "dsp.audio_engine.sd.InputStream",
            lambda **kwargs: mock_stream,
        )

        audio_engine.start()

        assert audio_engine.is_running is False
        assert audio_engine.stream is None
        assert audio_engine._dsp_thread is None
        assert audio_engine._dsp_stop_event.is_set()

        assert mock_stream.start.call_count == 2
        assert mock_stream.close.call_count == 2

class TestAudioCallback:

    def test_ignores_audio_when_engine_is_stopped(self, audio_engine):
        audio_data = np.ones((512, 1), dtype=np.float32)

        audio_engine.is_running = False
        audio_engine._audio_callback(audio_data, 512, None, None)

        assert audio_engine._audio_queue.empty()

    def test_queues_copy_of_mono_audio(self, audio_engine):
        audio_data = np.ones((512, 1), dtype=np.float32)

        audio_engine.is_running = True
        audio_engine._audio_callback(audio_data, 512, None, None)

        queued_audio = audio_engine._audio_queue.get_nowait()

        np.testing.assert_array_equal(queued_audio, audio_data[:, 0])
        assert queued_audio.ndim == 1
        assert not np.shares_memory(queued_audio, audio_data)

    def test_drops_oldest_block_when_queue_is_full(self, audio_engine):
        audio_engine.is_running = True

        oldest = np.full(512, 1.0, dtype=np.float32)
        second = np.full(512, 2.0, dtype=np.float32)
        third = np.full(512, 3.0, dtype=np.float32)
        fourth = np.full(512, 4.0, dtype=np.float32)
        incoming = np.full((512, 1), 5.0, dtype=np.float32)

        audio_engine._audio_queue.put_nowait(oldest)
        audio_engine._audio_queue.put_nowait(second)
        audio_engine._audio_queue.put_nowait(third)
        audio_engine._audio_queue.put_nowait(fourth)

        assert audio_engine._audio_queue.full()

        audio_engine._audio_callback(incoming, 512, None, None)

        assert audio_engine._audio_queue.qsize() == 4

        blocks = [
            audio_engine._audio_queue.get_nowait()
            for _ in range(4)
        ]

        np.testing.assert_array_equal(blocks[0], second)
        np.testing.assert_array_equal(blocks[1], third)
        np.testing.assert_array_equal(blocks[2], fourth)
        np.testing.assert_array_equal(blocks[3], incoming[:, 0])

    def test_handles_callback_exceptions(self, audio_engine, capsys):
        audio_engine.is_running = True

        class InvalidAudio:
            def __getitem__(self, key):
                raise RuntimeError("Simulated audio error")

        audio_engine._audio_callback(InvalidAudio(), 512, None, None)

        captured = capsys.readouterr()

        assert "Audio callback error" in captured.out
        assert "Simulated audio error" in captured.out
        assert audio_engine.is_running is True

class TestDSPWorkerProcessing:

    def test_updates_rolling_buffer_with_small_audio_block(
        self, audio_engine
    ):
        audio_block = np.array([1.0, 2.0, 3.0], dtype=np.float32)

        audio_engine._audio_queue.put_nowait(audio_block)
        audio_engine._dsp_stop_event.set()

        audio_engine._process_audio_queue()

        np.testing.assert_array_equal(
            audio_engine._pcm_buffer[-3:],
            audio_block,
        )

        np.testing.assert_array_equal(
            audio_engine._pcm_buffer[:-3],
            np.zeros(4093, dtype=np.float32),
        )

    def test_replaces_buffer_with_last_4096_samples_of_large_block(
        self, audio_engine
    ):
        audio_block = np.arange(5000, dtype=np.float32)

        audio_engine._audio_queue.put_nowait(audio_block)
        audio_engine._dsp_stop_event.set()

        audio_engine._process_audio_queue()

        np.testing.assert_array_equal(
            audio_engine._pcm_buffer,
            audio_block[-4096:],
        )
    def test_processes_audio_through_pitch_tracker_and_chromagram(
    self, audio_engine, monkeypatch
):
        from unittest.mock import MagicMock

        audio_block = np.ones(2048, dtype=np.float32)

        mock_pitch = LivePitch(
            note_name="C",
            pitch_class=0,
            frequency=261.63,
            is_silent=False,
            is_in_tune=True,
        )

        mock_pitch_tracker = MagicMock()
        mock_pitch_tracker.process_frame.return_value = mock_pitch

        mock_chroma = MagicMock()
        mock_chroma.process_frame.return_value = (
            {0, 4, 7},
            np.zeros(12, dtype=np.float32),
        )

        monkeypatch.setattr(
            audio_engine.pitch_tracker,
            "process_frame",
            mock_pitch_tracker.process_frame,
        )
        monkeypatch.setattr(
            audio_engine.chroma_analyzer,
            "process_frame",
            mock_chroma.process_frame,
        )

        audio_engine._audio_queue.put_nowait(audio_block)
        audio_engine._dsp_stop_event.set()

        audio_engine._process_audio_queue()

        mock_pitch_tracker.process_frame.assert_called_once()
        mock_chroma.process_frame.assert_called_once()

        np.testing.assert_array_equal(
            mock_pitch_tracker.process_frame.call_args[0][0],
            audio_engine._pcm_buffer,
        )

        assert audio_engine.get_active_strum_pcs() == {0, 4, 7}


    def test_records_in_tune_pitch_class_in_arpeggio_history(
        self, audio_engine, monkeypatch
    ):
        from unittest.mock import MagicMock

        mock_pitch = LivePitch(
            note_name="C",
            pitch_class=0,
            frequency=261.63,
            is_silent=False,
            is_in_tune=True,
        )

        monkeypatch.setattr(
            audio_engine.pitch_tracker,
            "process_frame",
            MagicMock(return_value=mock_pitch),
        )

        monkeypatch.setattr(
            audio_engine.chroma_analyzer,
            "process_frame",
            MagicMock(return_value=(set(), np.zeros(12))),
        )

        audio_engine._audio_queue.put_nowait(
            np.ones(2048, dtype=np.float32)
        )
        audio_engine._dsp_stop_event.set()

        audio_engine._process_audio_queue()

        assert audio_engine.get_accumulated_arpeggio_pcs() == {0}

    @pytest.mark.parametrize(
        "pitch",
        [
            LivePitch(
                pitch_class=0,
                is_silent=True,
                is_in_tune=True,
            ),
            LivePitch(
                pitch_class=4,
                is_silent=False,
                is_in_tune=False,
            ),
            LivePitch(
                pitch_class=-1,
                is_silent=False,
                is_in_tune=True,
            ),
        ],
    )
    def test_does_not_record_invalid_arpeggio_pitches(
        self, audio_engine, monkeypatch, pitch
    ):
        from unittest.mock import MagicMock

        monkeypatch.setattr(
            audio_engine.pitch_tracker,
            "process_frame",
            MagicMock(return_value=pitch),
        )

        monkeypatch.setattr(
            audio_engine.chroma_analyzer,
            "process_frame",
            MagicMock(return_value=(set(), np.zeros(12))),
        )

        audio_engine._audio_queue.put_nowait(
            np.ones(2048, dtype=np.float32)
        )
        audio_engine._dsp_stop_event.set()

        audio_engine._process_audio_queue()

        assert audio_engine.get_accumulated_arpeggio_pcs() == set()

    def test_expires_arpeggio_history_after_2_5_seconds(
        self, audio_engine, monkeypatch
    ):
        from unittest.mock import MagicMock

        mock_pitch = LivePitch(
            pitch_class=0,
            is_silent=False,
            is_in_tune=True,
        )

        monkeypatch.setattr(
            audio_engine.pitch_tracker,
            "process_frame",
            MagicMock(return_value=mock_pitch),
        )

        monkeypatch.setattr(
            audio_engine.chroma_analyzer,
            "process_frame",
            MagicMock(return_value=(set(), np.zeros(12))),
        )

        monkeypatch.setattr(
            "dsp.audio_engine.time.time",
            lambda: 100.0,
        )

        audio_engine._audio_queue.put_nowait(
            np.ones(2048, dtype=np.float32)
        )
        audio_engine._dsp_stop_event.set()

        audio_engine._process_audio_queue()

        assert audio_engine.get_accumulated_arpeggio_pcs() == {0}

        audio_engine._arpeggio_history.append((4, 97.0))

        assert audio_engine.get_accumulated_arpeggio_pcs() == {0}

    def test_dispatches_pitch_to_ui_page(self, audio_engine, monkeypatch):
        from unittest.mock import MagicMock

        mock_pitch = LivePitch(
            note_name="E",
            pitch_class=4,
            frequency=329.63,
            is_silent=False,
            is_in_tune=True,
        )

        monkeypatch.setattr(
            audio_engine.pitch_tracker,
            "process_frame",
            MagicMock(return_value=mock_pitch),
        )

        monkeypatch.setattr(
            audio_engine.chroma_analyzer,
            "process_frame",
            MagicMock(return_value=(set(), np.zeros(12))),
        )

        mock_page = MagicMock()
        audio_engine._ui_page = mock_page

        class FakeStopEvent:
            def __init__(self):
                self.calls = 0

            def is_set(self):
                self.calls += 1
                return self.calls >= 3

            def set(self):
                pass

        audio_engine._dsp_stop_event = FakeStopEvent()

    def test_throttles_ui_dispatch_to_20_hz(
        self, audio_engine, monkeypatch
    ):
        from unittest.mock import MagicMock

        mock_pitch = LivePitch(
            note_name="E",
            pitch_class=4,
            frequency=329.63,
            is_silent=False,
            is_in_tune=True,
        )

        monkeypatch.setattr(
            audio_engine.pitch_tracker,
            "process_frame",
            MagicMock(return_value=mock_pitch),
        )

        monkeypatch.setattr(
            audio_engine.chroma_analyzer,
            "process_frame",
            MagicMock(return_value=(set(), np.zeros(12))),
        )

        dispatch_mock = MagicMock()

        monkeypatch.setattr(
            audio_engine,
            "_dispatch_live_pitch",
            dispatch_mock,
        )

        audio_engine._audio_queue.put_nowait(
            np.ones(2048, dtype=np.float32)
        )
        audio_engine._audio_queue.put_nowait(
            np.ones(2048, dtype=np.float32)
        )
        audio_engine._audio_queue.put_nowait(
            np.ones(2048, dtype=np.float32)
        )

        class FakeStopEvent:
            def __init__(self):
                self.calls = 0

            def is_set(self):
                self.calls += 1
                return self.calls >= 7

            def set(self):
                pass

        audio_engine._dsp_stop_event = FakeStopEvent()

        monkeypatch.setattr(
            "dsp.audio_engine.time.time",
            MagicMock(side_effect=[1.00, 1.01, 1.06]),
        )

        audio_engine._process_audio_queue()

        assert dispatch_mock.call_count == 2

    def test_skips_ui_dispatch_when_page_is_none(
        self, audio_engine, monkeypatch
    ):
        from unittest.mock import MagicMock

        mock_pitch = LivePitch(
            note_name="E",
            pitch_class=4,
            frequency=329.63,
            is_silent=False,
            is_in_tune=True,
        )

        pitch_mock = MagicMock(return_value=mock_pitch)

        monkeypatch.setattr(
            audio_engine.pitch_tracker,
            "process_frame",
            pitch_mock,
        )

        monkeypatch.setattr(
            audio_engine.chroma_analyzer,
            "process_frame",
            MagicMock(return_value=(set(), np.zeros(12))),
        )

        audio_engine._ui_page = None

        audio_engine._audio_queue.put_nowait(
            np.ones(2048, dtype=np.float32)
        )

        audio_engine._dsp_stop_event.set()
        audio_engine._process_audio_queue()

        pitch_mock.assert_called_once()
        assert audio_engine._last_ui_notify_time > 0

    def test_detaches_destroyed_flet_session(
        self, audio_engine, monkeypatch
    ):
        from unittest.mock import MagicMock

        class DestroyedPage:
            @property
            def session(self):
                raise RuntimeError("An attempt to fetch destroyed session.")

        page = DestroyedPage()
        audio_engine.set_ui_page(page)

        publish_mock = MagicMock()

        monkeypatch.setattr(
            audio_engine,
            "_publish_live_pitch",
            publish_mock,
        )

        mock_pitch = LivePitch(
            note_name="E",
            pitch_class=4,
            frequency=329.63,
            is_silent=False,
            is_in_tune=True,
        )

        audio_engine._dispatch_live_pitch(mock_pitch)

        assert audio_engine._ui_page is None
        publish_mock.assert_not_called()

    def test_closes_coroutine_when_event_loop_scheduling_fails(
        self, audio_engine, monkeypatch
    ):
        import inspect
        from types import SimpleNamespace
        from unittest.mock import MagicMock

        page = SimpleNamespace(
            session=SimpleNamespace(
                connection=SimpleNamespace(loop=MagicMock())
            )
        )

        audio_engine.set_ui_page(page)

        async def fake_publish(live_pitch):
            pass

        monkeypatch.setattr(
            audio_engine,
            "_publish_live_pitch",
            fake_publish,
        )

        scheduler_mock = MagicMock(
            side_effect=RuntimeError("Event loop is closed.")
        )

        monkeypatch.setattr(
            "dsp.audio_engine.asyncio.run_coroutine_threadsafe",
            scheduler_mock,
        )

        mock_pitch = LivePitch(
            note_name="E",
            pitch_class=4,
            frequency=329.63,
            is_silent=False,
            is_in_tune=True,
        )

        audio_engine._dispatch_live_pitch(mock_pitch)

        scheduler_mock.assert_called_once()

        scheduled_coroutine = scheduler_mock.call_args.args[0]

        assert inspect.getcoroutinestate(scheduled_coroutine) == (
            inspect.CORO_CLOSED
        )
        assert audio_engine._ui_page is None

    def test_publish_live_pitch_updates_app_state(self, audio_engine):
        import asyncio
        from unittest.mock import MagicMock

        mock_pitch = LivePitch(
            note_name="G",
            pitch_class=7,
            frequency=392.0,
            is_silent=False,
            is_in_tune=True,
        )

        audio_engine.app_state.update_live_pitch = MagicMock()

        asyncio.run(audio_engine._publish_live_pitch(mock_pitch))

        audio_engine.app_state.update_live_pitch.assert_called_once_with(
            mock_pitch
        )

    def test_get_active_strum_pcs_returns_copy(self, audio_engine):
        audio_engine._active_strum_pcs = {0, 4, 7}

        result = audio_engine.get_active_strum_pcs()

        assert result == {0, 4, 7}
        assert result is not audio_engine._active_strum_pcs

        result.add(9)

        assert audio_engine._active_strum_pcs == {0, 4, 7}

    def test_get_accumulated_arpeggio_pcs_filters_expired_entries(
        self, audio_engine, monkeypatch
    ):
        monkeypatch.setattr(
            "dsp.audio_engine.time.time",
            lambda: 100.0,
        )

        audio_engine._arpeggio_history = [
            (0, 99.0),
            (4, 98.0),
            (7, 97.5),
            (9, 97.4),
        ]

        result = audio_engine.get_accumulated_arpeggio_pcs()

        assert result == {0, 4, 7}
        assert len(audio_engine._arpeggio_history) == 4

    def test_clear_arpeggio_buffer_clears_all_arpeggio_state(self, audio_engine):
        audio_engine._arpeggio_history = [
            (0, 99.0),
            (4, 99.5),
            (7, 99.8),
        ]
        audio_engine._active_strum_pcs = {2, 5, 9}

        audio_engine.chroma_analyzer.clear = MagicMock()

        audio_engine.clear_arpeggio_buffer()

        assert audio_engine._arpeggio_history == []
        assert audio_engine._active_strum_pcs == set()
        audio_engine.chroma_analyzer.clear.assert_called_once()
