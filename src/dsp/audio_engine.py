"""
src/dsp/audio_engine.py
=======================
Central audio engine capturing microphone input via sounddevice with dynamic
sample rate auto-detection, rolling PCM analysis buffer, dual DSP analysis,
and time-windowed arpeggio accumulation.
"""

import time
from typing import Any, Dict, List, Optional, Set, Tuple
import numpy as np
import sounddevice as sd

from core.app_state import AppState, LivePitch
from dsp.chromagram import ChromagramAnalyzer
from dsp.pitch_tracker import PitchTracker


class AudioEngine:
    """Central DSP manager driving microphone streaming, device selection, and dual DSP analysis."""

    _instance: Optional["AudioEngine"] = None

    def __init__(self, sample_rate: int = 44100, block_size: int = 2048) -> None:
        self.sample_rate = sample_rate
        self.block_size = block_size

        self.app_state = AppState.get_instance()
        self.pitch_tracker = PitchTracker(sample_rate=sample_rate)
        self.chroma_analyzer = ChromagramAnalyzer(sample_rate=sample_rate)

        # Rolling 4096-sample buffer ensuring analysis always receives full windows
        self._pcm_buffer = np.zeros(4096, dtype=np.float32)

        self.stream: Optional[sd.InputStream] = None

        try:
            default_in = sd.default.device[0]
            self.device_id: Optional[int] = int(default_in) if (default_in is not None and default_in >= 0) else None
        except Exception:
            self.device_id = None

        self.is_running = False

        self._arpeggio_history: List[Tuple[int, float]] = []
        self._last_ui_notify_time = 0.0
        self._active_strum_pcs: Set[int] = set()

    @classmethod
    def get_instance(cls) -> "AudioEngine":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def get_input_devices(self) -> List[Dict[str, Any]]:
        """Queries and returns all available audio input hardware devices."""
        input_devs = []
        try:
            devices = sd.query_devices()
            for idx, dev in enumerate(devices):
                if dev.get("max_input_channels", 0) > 0:
                    input_devs.append({
                        "id": idx,
                        "name": dev.get("name", f"Input Device #{idx}"),
                        "channels": dev.get("max_input_channels", 1),
                        "default_samplerate": dev.get("default_samplerate", 44100),
                    })
        except Exception as e:
            print(f"[AudioEngine] Failed to query audio devices: {e}")

        if not input_devs:
            input_devs.append({
                "id": -1,
                "name": "Default System Microphone",
                "channels": 1,
                "default_samplerate": 44100,
            })
        return input_devs

    def set_device(self, device_id: int) -> None:
        """Switches microphone input source to target hardware device ID."""
        target_id = None if device_id < 0 else device_id
        print(f"[AudioEngine] Setting input device to ID: {target_id}")
        self.device_id = target_id
        self.stop()
        self.start()

    def start(self) -> None:
        if self.is_running:
            return

        # Query native sample rate of selected device to prevent PortAudioError
        try:
            if self.device_id is not None:
                dev_info = sd.query_devices(self.device_id, "input")
            else:
                dev_info = sd.query_devices(kind="input")

            native_sr = int(dev_info.get("default_samplerate", 44100))
            if native_sr > 0:
                self.sample_rate = native_sr
                self.pitch_tracker.sample_rate = native_sr
                self.chroma_analyzer.sample_rate = native_sr
        except Exception as e:
            print(f"[AudioEngine] Query device info warning: {e}")

        self.is_running = True
        try:
            self.stream = sd.InputStream(
                device=self.device_id,
                samplerate=self.sample_rate,
                blocksize=self.block_size,
                channels=1,
                callback=self._audio_callback,
            )
            self.stream.start()
            print(f"[AudioEngine] Audio stream started on device {self.device_id} @ {self.sample_rate}Hz")
        except Exception as e:
            print(f"[AudioEngine] Primary start failed @ {self.sample_rate}Hz: {e}")
            fallback_sr = 48000 if self.sample_rate != 48000 else 44100
            try:
                self.sample_rate = fallback_sr
                self.pitch_tracker.sample_rate = fallback_sr
                self.chroma_analyzer.sample_rate = fallback_sr
                self.stream = sd.InputStream(
                    device=self.device_id,
                    samplerate=self.sample_rate,
                    blocksize=self.block_size,
                    channels=1,
                    callback=self._audio_callback,
                )
                self.stream.start()
                print(f"[AudioEngine] Fallback audio stream started on device {self.device_id} @ {self.sample_rate}Hz")
            except Exception as err:
                print(f"[AudioEngine] All audio stream start attempts failed: {err}")
                self.is_running = False

    def stop(self) -> None:
        self.is_running = False
        if self.stream is not None:
            try:
                self.stream.stop()
                self.stream.close()
            except Exception:
                pass
            self.stream = None

    def _audio_callback(self, indata: np.ndarray, frames: int, time_info, status) -> None:
        if not self.is_running:
            return

        audio_samples = indata[:, 0]
        n_samples = len(audio_samples)

        # Accumulate in 4096-sample rolling buffer
        if n_samples > 0:
            if n_samples >= 4096:
                self._pcm_buffer = audio_samples[-4096:].astype(np.float32)
            else:
                self._pcm_buffer = np.roll(self._pcm_buffer, -n_samples)
                self._pcm_buffer[-n_samples:] = audio_samples.astype(np.float32)

        now = time.time()

        # 1. Monophonic Fundamental Tracking
        live_pitch = self.pitch_tracker.process_frame(self._pcm_buffer)

        # 2. Polyphonic Chromagram Extraction
        active_strum_pcs, chroma_vec = self.chroma_analyzer.process_frame(self._pcm_buffer)
        self._active_strum_pcs = active_strum_pcs

        # 3. Time-windowed Arpeggio Accumulation
        if not live_pitch.is_silent and live_pitch.is_in_tune:
            pc = live_pitch.pitch_class
            if pc >= 0:
                self._arpeggio_history.append((pc, now))

        # Purge arpeggio history entries older than 2.5 seconds
        self._arpeggio_history = [(pc, t) for pc, t in self._arpeggio_history if (now - t) <= 2.5]

        # 4. Throttled UI State Dispatch
        if (now - self._last_ui_notify_time) >= 0.05:
            self._last_ui_notify_time = now
            self.app_state.update_live_pitch(live_pitch)

    def get_active_strum_pcs(self) -> Set[int]:
        return set(self._active_strum_pcs)

    def get_accumulated_arpeggio_pcs(self) -> Set[int]:
        now = time.time()
        return {pc for pc, t in self._arpeggio_history if (now - t) <= 2.5}

    def clear_arpeggio_buffer(self) -> None:
        self._arpeggio_history.clear()
        self.chroma_analyzer.clear()
