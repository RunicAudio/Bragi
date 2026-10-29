"""
src/dsp/audio_engine.py
=======================
Central audio engine capturing microphone input via sounddevice with device selection,
frequency analysis, and throttled UI notifications.
"""

import time
from typing import List, Dict, Any, Optional, Set
import numpy as np
import sounddevice as sd

from core.app_state import AppState, LivePitch
from dsp.pitch_tracker import PitchTracker


class AudioEngine:
    """Central DSP manager driving microphone streaming, device selection, and pitch analysis."""

    _instance: Optional["AudioEngine"] = None

    def __init__(self, sample_rate: int = 44100, block_size: int = 2048) -> None:
        self.sample_rate = sample_rate
        self.block_size = block_size

        self.app_state = AppState.get_instance()
        self.pitch_tracker = PitchTracker(sample_rate=sample_rate)

        self.stream: Optional[sd.InputStream] = None
        self.device_id: Optional[int] = None
        self.is_running = False

        self._arpeggio_pcs: Set[int] = set()
        self._last_ui_notify_time = 0.0

    @classmethod
    def get_instance(cls) -> "AudioEngine":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def get_input_devices(self) -> List[Dict[str, Any]]:
        """Queries and returns all available audio input hardware devices."""
        try:
            devices = sd.query_devices()
            input_devs = []
            for idx, dev in enumerate(devices):
                if dev.get("max_input_channels", 0) > 0:
                    input_devs.append({
                        "id": idx,
                        "name": dev.get("name", f"Input Device #{idx}"),
                        "channels": dev.get("max_input_channels", 1),
                        "default_samplerate": dev.get("default_samplerate", 44100),
                    })
            return input_devs
        except Exception as e:
            print(f"[AudioEngine] Failed to query audio devices: {e}")
            return []

    def set_device(self, device_id: int) -> None:
        """Switches microphone input source to target hardware device ID."""
        self.device_id = device_id
        if self.is_running:
            self.stop()
            self.start()

    def start(self) -> None:
        if self.is_running:
            return
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
        except Exception as e:
            print(f"[AudioEngine] Failed to start input stream: {e}")
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
        live_pitch = self.pitch_tracker.process_frame(audio_samples)

        if not live_pitch.is_silent and live_pitch.is_in_tune:
            pc = live_pitch.pitch_class
            if pc >= 0:
                self._arpeggio_pcs.add(pc)

        now = time.time()
        if (now - self._last_ui_notify_time) >= 0.066:
            self._last_ui_notify_time = now
            self.app_state.update_live_pitch(live_pitch)

    def get_accumulated_arpeggio_pcs(self) -> Set[int]:
        return set(self._arpeggio_pcs)

    def clear_arpeggio_buffer(self) -> None:
        self._arpeggio_pcs.clear()
