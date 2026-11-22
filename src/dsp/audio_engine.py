"""
src/dsp/audio_engine.py
=======================
Central audio engine capturing microphone input via sounddevice with dynamic
sample rate auto-detection, rolling PCM analysis buffer, dual DSP analysis,
and time-windowed arpeggio accumulation.
"""

import time
import queue
import threading
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

        self.device_id = self._find_preferred_input_device()

        if self.device_id is None:
            try:
                default_in = sd.default.device[0]
                self.device_id = (
                    int(default_in)
                    if default_in is not None and default_in >= 0
                    else None
                )
                print(
                    f"[AudioEngine] HeadRush WASAPI not found. "
                    f"Using system default input: {self.device_id}"
                )
            except Exception:
                self.device_id = None
        else:
            print(
                f"[AudioEngine] Preferred HeadRush input found: "
                f"device {self.device_id}"
            )

        self.is_running = False

        # Background DSP worker infrastructure
        self._audio_queue = queue.Queue(maxsize=4)
        self._dsp_thread: Optional[threading.Thread] = None
        self._dsp_stop_event = threading.Event()
        self._analysis_lock = threading.Lock()

        self._ui_page = None

        self._arpeggio_history: List[Tuple[int, float]] = []
        self._last_ui_notify_time = 0.0
        self._active_strum_pcs: Set[int] = set()

    @classmethod
    def get_instance(cls) -> "AudioEngine":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @staticmethod
    def _find_preferred_input_device() -> Optional[int]:
        """Find the HeadRush Core Line 1/2 input using Windows WASAPI."""

        try:
            devices = sd.query_devices()

            for idx, device in enumerate(devices):
                name = device.get("name", "")

                if (
                    "HeadRush Core" not in name
                    or "Line 1/2" not in name
                    or device.get("max_input_channels", 0) < 1
                ):
                    continue

                host_api = sd.query_hostapis(device["hostapi"])["name"]

                if "WASAPI" in host_api:
                    return idx

        except Exception as error:
            print(
                f"[AudioEngine] Preferred device detection failed: {error}"
            )

        return None

    def get_input_devices(self) -> List[Dict[str, Any]]:
        """Return primary audio inputs without duplicate host API entries."""

        input_devs = []

        try:
            devices = sd.query_devices()
            host_apis = sd.query_hostapis()

            preferred_devices = [
                # All HeadRush input configurations
                ("HeadRush Core", "Line 1/2", "Windows WASAPI"),
                ("HeadRush Core", "Line 3/4", "Windows WASAPI"),
                ("HeadRush Core", "Line 5/6", "Windows WASAPI"),
                ("HeadRush Core", "Multichannel", "Windows WASAPI"),

                # Other useful inputs
                ("Intel", "Microphone Array", "Windows WASAPI"),
                ("Voicemeeter", "Out B1", "Windows WASAPI"),
                ("Realtek", "Microphone", "Windows WDM-KS"),
            ]

            for manufacturer, endpoint, preferred_api in preferred_devices:
                for idx, dev in enumerate(devices):

                    if dev.get("max_input_channels", 0) <= 0:
                        continue

                    name = dev.get("name", "")
                    host_api = host_apis[dev["hostapi"]]["name"]

                    if manufacturer.lower() not in name.lower():
                        continue

                    if endpoint.lower() not in name.lower():
                        continue

                    if host_api != preferred_api:
                        continue

                    input_devs.append({
                        "id": idx,
                        "name": name,
                        "channels": dev["max_input_channels"],
                        "default_samplerate": dev["default_samplerate"],
                        "host_api": host_api,
                    })

                    break

        except Exception as e:
            print(f"[AudioEngine] Failed to query audio devices: {e}")

        print(f"[AudioEngine] Found {len(input_devs)} primary input devices.")

        for dev in input_devs:
            print(
                f"[AudioEngine] {dev['id']}: "
                f"{dev['name']} ({dev['channels']} channels)"
            )

        return input_devs

    def set_ui_page(self, page) -> None:
        """Registers the Flet page for thread-safe UI dispatch."""
        self._ui_page = page

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

        # Determine the selected device's native sample rate.
        try:
            if self.device_id is not None:
                dev_info = sd.query_devices(self.device_id, "input")
            else:
                dev_info = sd.query_devices(kind="input")

            native_sr = int(dev_info.get("default_samplerate", 44100))
        except Exception as e:
            print(f"[AudioEngine] Query device info warning: {e}")
            native_sr = self.sample_rate

        # Try native rate first, then the alternate common rate.
        sample_rates = [native_sr, 48000 if native_sr != 48000 else 44100]

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
            try:
                self.sample_rate = sample_rate
                self.pitch_tracker.set_sample_rate(sample_rate)
                self.chroma_analyzer.sample_rate = sample_rate

                self.stream = sd.InputStream(
                    device=self.device_id,
                    samplerate=sample_rate,
                    blocksize=self.block_size,
                    channels=1,
                    callback=self._audio_callback,
                )

                self.stream.start()

                print(
                    f"[AudioEngine] Audio stream started on device "
                    f"{self.device_id} @ {sample_rate}Hz"
                )
                return

            except Exception as e:
                print(
                    f"[AudioEngine] Stream start failed @ "
                    f"{sample_rate}Hz: {e}"
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

                    page = self._ui_page
                    if page is not None:
                        try:
                            page.run_task(self._publish_live_pitch, live_pitch)
                        except Exception as e:
                            print(f"[AudioEngine] UI dispatch error: {e}")

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
