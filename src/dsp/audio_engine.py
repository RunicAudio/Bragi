"""
src/dsp/audio_engine.py
=======================
Central audio engine capturing microphone input via sounddevice with dynamic
sample rate auto-detection, rolling PCM analysis buffer, dual DSP analysis,
and time-windowed arpeggio accumulation.
"""

import sys
import time
import queue
import threading
import asyncio
import time
from typing import Any, Dict, List, Optional, Set, Tuple

import numpy as np
import sounddevice as sd

from core.app_state import AppState, LivePitch
from dsp.chromagram import ChromagramAnalyzer
from dsp.pitch_tracker import PitchTracker
from storage.db_manager import DatabaseManager


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

        # Persistent application-wide audio input preference.
        self.db = DatabaseManager.get_instance()

        # Runtime device index and persistent device identity.
        self.device_id: Optional[int] = None
        self.device_key: Optional[str] = None

        self._initialize_input_device()

        self.is_running = False

        # Background DSP worker infrastructure
        self._audio_queue = queue.Queue(maxsize=4)
        self._dsp_thread: Optional[threading.Thread] = None
        self._dsp_stop_event = threading.Event()
        self._analysis_lock = threading.Lock()

        self._ui_page = None
        self._ui_page_lock = threading.Lock()

        self._arpeggio_history: List[Tuple[int, float]] = []
        self._last_ui_notify_time = 0.0
        self._active_strum_pcs: Set[int] = set()

    @classmethod
    def get_instance(cls) -> "AudioEngine":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _select_input_host_api(
        self,
        host_apis: List[Dict[str, Any]],
        devices: List[Dict[str, Any]],
    ) -> Optional[int]:
        """
        Select one host API to avoid duplicate representations of devices.

        Windows: WASAPI
        macOS: Core Audio
        Linux: PulseAudio, then ALSA
        Other cases: system default input host API, then first available.
        """

        api_names = [
            api.get("name", "")
            for api in host_apis
        ]

        preferred_names = []

        if sys.platform == "win32":
            preferred_names = ["Windows WASAPI"]

        elif sys.platform == "darwin":
            preferred_names = ["Core Audio"]

        elif sys.platform.startswith("linux"):
            preferred_names = ["PulseAudio", "ALSA"]

        # Use the preferred host API when available and it has inputs.
        for preferred_name in preferred_names:
            for api_index, api_name in enumerate(api_names):
                if api_name.lower() == preferred_name.lower():
                    if any(
                        device.get("hostapi") == api_index
                        and device.get("max_input_channels", 0) > 0
                        for device in devices
                    ):
                        return api_index

        # Fall back to the host API containing the system default input.
        try:
            default_input = sd.default.device[0]

            if default_input is not None and int(default_input) >= 0:
                default_device = sd.query_devices(int(default_input))
                default_api = default_device.get("hostapi")

                if (
                    default_api is not None
                    and any(
                        device.get("hostapi") == default_api
                        and device.get("max_input_channels", 0) > 0
                        for device in devices
                    )
                ):
                    return int(default_api)

        except Exception:
            pass

        # Last resort: first host API with an input-capable device.
        for api_index in range(len(host_apis)):
            if any(
                device.get("hostapi") == api_index
                and device.get("max_input_channels", 0) > 0
                for device in devices
            ):
                return api_index

        return None

    def get_input_devices(self) -> List[Dict[str, Any]]:
        """Return input devices from one selected host API."""

        input_devices = []

        try:
            devices = sd.query_devices()
            host_apis = sd.query_hostapis()

            selected_api = self._select_input_host_api(
                host_apis,
                devices,
            )

            if selected_api is None:
                print("[AudioEngine] No usable audio host API found.")
                return []

            selected_api_name = host_apis[selected_api]["name"]

            default_device_id = host_apis[selected_api].get(
                "default_input_device",
                -1,
            )

            for device_id, device in enumerate(devices):
                if device.get("hostapi") != selected_api:
                    continue

                channels = int(device.get("max_input_channels", 0))

                if channels <= 0:
                    continue

                name = device.get("name", "Unknown input")

                # This identity remains stable when PortAudio indexes change.
                device_key = (
                    f"{selected_api_name}|{name}|{channels}ch"
                )

                input_devices.append({
                    "id": device_id,
                    "key": device_key,
                    "name": name,
                    "channels": channels,
                    "default_samplerate": device.get(
                        "default_samplerate",
                        44100,
                    ),
                    "host_api": selected_api_name,
                    "is_default": device_id == default_device_id,
                })

            print(
                f"[AudioEngine] Using {selected_api_name}: "
                f"{len(input_devices)} input device(s)."
            )

            for device in input_devices:
                default_label = " [DEFAULT]" if device["is_default"] else ""

                print(
                    f"[AudioEngine] {device['id']}: "
                    f"{device['name']} "
                    f"({device['channels']} channels)"
                    f"{default_label}"
                )

        except Exception as error:
            print(
                f"[AudioEngine] Failed to query audio devices: {error}"
            )

        return input_devices

    def _initialize_input_device(self) -> None:
        """Restore the saved input device or use the host API default."""

        devices = self.get_input_devices()

        if not devices:
            self.device_id = None
            self.device_key = None
            print("[AudioEngine] No input devices are currently available.")
            return

        saved_key = self.db.get_setting("audio_input_device")

        selected_device = None

        if saved_key:
            selected_device = next(
                (
                    device for device in devices
                    if device["key"] == saved_key
                ),
                None,
            )

            if selected_device:
                print(
                    f"[AudioEngine] Restored saved input: "
                    f"{selected_device['name']}"
                )
            else:
                print(
                    "[AudioEngine] Saved input is unavailable. "
                    "Using the system default."
                )

        if selected_device is None:
            selected_device = next(
                (
                    device for device in devices
                    if device["is_default"]
                ),
                devices[0],
            )

        self.device_id = selected_device["id"]
        self.device_key = selected_device["key"]

        print(
            f"[AudioEngine] Active input: "
            f"{selected_device['name']} "
            f"({selected_device['host_api']})"
        )

    def set_ui_page(self, page) -> None:
        """Register or detach the Flet page safely across threads."""
        with self._ui_page_lock:
            self._ui_page = page

    def _dispatch_live_pitch(self, live_pitch: LivePitch) -> None:
        """Schedule pitch publication without touching a destroyed Flet session."""

        with self._ui_page_lock:
            page = self._ui_page

        if page is None:
            return

        # Retrieve the event loop before creating the coroutine.
        try:
            loop = page.session.connection.loop
        except RuntimeError:
            with self._ui_page_lock:
                if self._ui_page is page:
                    self._ui_page = None
            return

        coroutine = self._publish_live_pitch(live_pitch)

        try:
            asyncio.run_coroutine_threadsafe(coroutine, loop)
        except RuntimeError:
            coroutine.close()

            with self._ui_page_lock:
                if self._ui_page is page:
                    self._ui_page = None

    def set_device(self, device_key: str) -> None:
        """Switch input devices and persist the selected device identity."""

        devices = self.get_input_devices()

        selected_device = next(
            (
                device for device in devices
                if device["key"] == device_key
            ),
            None,
        )

        if selected_device is None:
            print(
                f"[AudioEngine] Requested input device is unavailable: "
                f"{device_key}"
            )
            return

        if self.device_key == device_key and self.is_running:
            return

        self.device_id = selected_device["id"]
        self.device_key = selected_device["key"]

        self.db.set_setting("audio_input_device", self.device_key)

        print(
            f"[AudioEngine] Switching input to "
            f"{selected_device['name']} "
            f"({selected_device['host_api']})"
        )

        self.stop()
        self.start()

    def start(self) -> None:
        if self.is_running:
            return

        # Determine the selected device's native audio capabilities.
        try:
            if self.device_id is not None:
                dev_info = sd.query_devices(self.device_id, "input")
            else:
                dev_info = sd.query_devices(kind="input")

            native_sr = int(dev_info.get("default_samplerate", 44100))
            max_channels = max(
                1,
                int(dev_info.get("max_input_channels", 1)),
            )

        except Exception as e:
            print(f"[AudioEngine] Query device info warning: {e}")
            native_sr = self.sample_rate
            max_channels = 1

        # Try the native sample rate before the alternate common rate.
        sample_rates = [
            native_sr,
            48000 if native_sr != 48000 else 44100,
        ]

        # Try the lowest channel count first.
        channel_counts = list(range(1, max_channels + 1))

        # Prepare the DSP worker.
        self._dsp_stop_event.clear()

        while not self._audio_queue.empty():
            try:
                self._audio_queue.get_nowait()
            except queue.Empty:
                break

        self._pcm_buffer = np.zeros(4096, dtype=np.float32)
        self._last_ui_notify_time = 0.0

        self._dsp_thread = threading.Thread(
            target=self._process_audio_queue,
            name="Bragi-DSP",
            daemon=True,
        )
        self._dsp_thread.start()

        self.is_running = True

        for sample_rate in sample_rates:
            for channels in channel_counts:
                self.stream = None

                try:
                    self.sample_rate = sample_rate
                    self.pitch_tracker.set_sample_rate(sample_rate)
                    self.chroma_analyzer.sample_rate = sample_rate

                    self.stream = sd.InputStream(
                        device=self.device_id,
                        samplerate=sample_rate,
                        blocksize=self.block_size,
                        channels=channels,
                        callback=self._audio_callback,
                    )

                    self.stream.start()

                    print(
                        f"[AudioEngine] Audio stream started on device "
                        f"{self.device_id} @ {sample_rate}Hz "
                        f"({channels} channel(s))"
                    )
                    return

                except Exception as e:
                    print(
                        f"[AudioEngine] Stream start failed: "
                        f"{sample_rate}Hz, {channels} channel(s): {e}"
                    )

                    if self.stream is not None:
                        try:
                            self.stream.close()
                        except Exception:
                            pass

                        self.stream = None

        print("[AudioEngine] All audio stream start attempts failed.")
        self.stop()


    def stop(self) -> None:
        self.is_running = False

    # Stop audio capture before shutting down DSP processing.
        if self.stream is not None:
            try:
                self.stream.stop()
                self.stream.close()
            except Exception as e:
                print(f"[AudioEngine] Stream shutdown warning: {e}")
            finally:
                self.stream = None

        # Allow the worker to finish processing queued audio.
        self._dsp_stop_event.set()

        if self._dsp_thread is not None:
            if self._dsp_thread is not threading.current_thread():
                self._dsp_thread.join(timeout=3.0)

            if not self._dsp_thread.is_alive():
                self._dsp_thread = None

    def _audio_callback(self, indata: np.ndarray, frames: int, time_info, status) -> None:
        """Capture audio and enqueue it for background DSP processing."""
        if not self.is_running:
            return

        try:
            audio_samples = indata[:, 0].copy()

            try:
                self._audio_queue.put_nowait(audio_samples)
            except queue.Full:
                # Discard the oldest block to prioritize recent audio.
                try:
                    self._audio_queue.get_nowait()
                except queue.Empty:
                    pass

                try:
                    self._audio_queue.put_nowait(audio_samples)
                except queue.Full:
                    pass

        except Exception as e:
            print(f"[AudioEngine] Audio callback error: {e}")

    def _process_audio_queue(self) -> None:
        """Process queued audio independently of the PortAudio callback."""

        while not self._dsp_stop_event.is_set() or not self._audio_queue.empty():
            try:
                audio_samples = self._audio_queue.get(timeout=0.1)
            except queue.Empty:
                continue

            try:
                n_samples = len(audio_samples)

                # Maintain the rolling 4096-sample analysis buffer.
                if n_samples >= 4096:
                    self._pcm_buffer = audio_samples[-4096:].astype(np.float32)
                elif n_samples > 0:
                    self._pcm_buffer = np.roll(self._pcm_buffer, -n_samples)
                    self._pcm_buffer[-n_samples:] = audio_samples

                now = time.time()

                #Monophonic fundamental tracking.
                live_pitch = self.pitch_tracker.process_frame(self._pcm_buffer)

                #Update shared chord detection state safely
                with self._analysis_lock:
                    active_strum_pcs, chrome_vec = self.chroma_analyzer.process_frame(
                        self._pcm_buffer
                    )

                    self._active_strum_pcs = active_strum_pcs

                    if not live_pitch.is_silent and live_pitch.is_in_tune:
                        pc = live_pitch.pitch_class
                        if pc >= 0:
                            self._arpeggio_history.append((pc, now))

                    self._arpeggio_history = [
                        (pc, timestamp)
                        for pc, timestamp in self._arpeggio_history
                        if now - timestamp <= 2.5
                    ]

                # Throttle pitch notifications to approximately 20 Hz.
                if now - self._last_ui_notify_time >= 0.05:
                    self._last_ui_notify_time = now

                    if not self._dsp_stop_event.is_set():
                        self._dispatch_live_pitch(live_pitch)
                        
            except Exception as e:
                print(f"[AudioEngine] DSP worker error: {e}")


    async def _publish_live_pitch(self, live_pitch: LivePitch) -> None:
        """Publish pitch changes through Flet's event loop."""
        self.app_state.update_live_pitch(live_pitch)

    def get_active_strum_pcs(self) -> Set[int]:
        with self._analysis_lock:
            return set(self._active_strum_pcs)


    def get_accumulated_arpeggio_pcs(self) -> Set[int]:
        now = time.time()
        with self._analysis_lock:
            return {
                pc for pc, timestamp in self._arpeggio_history
                if now - timestamp <= 2.5
            }


    def clear_arpeggio_buffer(self) -> None:
        with self._analysis_lock:
            self._arpeggio_history.clear()
            self.chroma_analyzer.clear()
            self._active_strum_pcs.clear()
