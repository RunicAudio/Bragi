# Bragi

**A guitar-focused fretboard, pitch-detection, and ear-training application.**

Bragi is a desktop application for practicing musical note recognition, identifying chord tones, developing fretboard familiarity, and improving aural recognition. It combines live audio analysis with guided guitar exercises, a chromatic tuner, generated listening examples, and locally stored practice progression.

The application is built with Python and Flet. Its audio-analysis pipeline uses SoundDevice, NumPy, and SciPy-compatible numerical processing; musical definitions and training rules are separated from the interface and persistence layers.

> **Project status:** Bragi is an actively developed project. The current application includes working trainer, tuner, ear-training, and analytics views. Some detection and progression behavior is still being refined; see [Current Capabilities and Known Limitations](#current-capabilities-and-known-limitations).

---

## Contents

- [Features](#features)
- [Technology](#technology)
- [Project Structure](#project-structure)
- [How the Application Works](#how-the-application-works)
- [Installation](#installation)
- [Running Bragi](#running-bragi)
- [Audio Setup](#audio-setup)
- [Tests](#tests)
- [Local Data](#local-data)
- [Current Capabilities and Known Limitations](#current-capabilities-and-known-limitations)
- [Development](#development)
- [License](#license)

---

## Features

### Guitar Trainer

The Trainer provides three live-input practice modes:

- **Single Note:** displays a target note and string, then advances when the detected note matches the target and is within the configured tuning tolerance for the selected hold duration.
- **Strummed Chord:** analyzes simultaneous pitch classes and checks whether the target chord's pitch classes are present.
- **Arpeggio Chord:** accumulates detected pitch classes over a rolling 2.5-second window and checks for the target chord tones.

The trainer also provides target skipping, theory hints, configurable trainer mode, and adjustable auto-advance hold timing.

### Real-Time Pitch Detection

Bragi captures audio from a selected input device and estimates monophonic fundamental frequency. The live pitch result includes:

- Note name and pitch class.
- Estimated frequency.
- Cents deviation from the nearest equal-tempered note.
- In-tune status.
- Input RMS level and silence status.

The current pitch tracker uses autocorrelation, peak selection, and parabolic interpolation. The tuner and single-note trainer consume the same live pitch state.

### Chord and Pitch-Class Analysis

A separate chromagram analyzer performs FFT-based spectral analysis and maps spectral energy into 12 pitch classes. It uses a short multi-frame history and harmonic attenuation to produce candidate pitch classes for the trainer's strummed-chord mode. The audio engine also maintains the short history used by arpeggio mode.

### Chromatic Tuner

The tuner displays the detected note, cents deviation, and a visual needle. Its status indicator distinguishes in-tune, close-to-pitch, and out-of-tune readings.

### Ear Training

Ear Training currently provides two listening exercise types:

- **Single Pitch:** identify a note from a set of note-name choices.
- **Chord Quality:** distinguish among major, minor, diminished, and suspended-fourth triads.

Bragi generates the examples locally and provides replay controls.

### Analytics and Progression

Bragi stores practice results locally and displays:

- Total experience points (XP) and user level.
- Total attempts, accuracy, and average response time.
- A consecutive-correct-answer streak.
- Defined achievement badges and unlocked badge state.
- Progress counters for the Hero Boss challenge.

The application includes a catalog of 40 badge definitions. Unlock evaluation is currently implemented for a subset of those definitions; the full badge catalog should not be interpreted as evidence that every badge condition is already active.

---

## Technology

| Technology | Role |
|---|---|
| Python 3.10+ | Application language |
| Flet | Desktop UI and event handling |
| NumPy | Audio buffers and numerical analysis |
| SciPy | Scientific-computing dependency |
| SoundDevice | Audio input and generated audio playback |
| Pydantic | Typed data models and validation |
| SQLite | Local practice and progression storage |
| pytest | Automated tests |
| setuptools | Package and editable-install configuration |

Runtime dependencies are declared in `pyproject.toml`. The project does not currently declare SoundFile as a runtime dependency.

---

## Project Structure

The following tree reflects the files currently present on the `main` branch. It excludes generated files, local environments, and user data.

```text
Bragi/
├── .github/
│   └── workflows/
│       └── build.yml
├── .vscode/
│   └── settings.json
├── assets/
│   ├── bg.png
│   ├── logo.ico
│   ├── logo.png
│   └── release-description.md
├── src/
│   ├── main.py
│   ├── core/
│   │   └── app_state.py
│   ├── domain/
│   │   ├── chord_definitions.py
│   │   ├── gamification_policy.py
│   │   ├── music_theory.py
│   │   └── scale_definitions.py
│   ├── dsp/
│   │   ├── audio_engine.py
│   │   ├── chromagram.py
│   │   ├── pitch_tracker.py
│   │   └── sample_player.py
│   ├── storage/
│   │   ├── db_manager.py
│   │   └── path_utils.py
│   └── ui/
│       ├── app_shell.py
│       ├── components/
│       │   ├── header_nav.py
│       │   └── modals/
│       │       ├── device_modal.py
│       │       ├── filter_modal.py
│       │       ├── hint_modal.py
│       │       └── timing_modal.py
│       └── views/
│           ├── analytics_view.py
│           ├── ear_training_view.py
│           ├── trainer_view.py
│           └── tuner_view.py
├── tests/
│   ├── fixtures/
│   │   └── real_guitar/
│   │       └── low_e2.wav
│   ├── test_app_state.py
│   ├── test_audio_engine.py
│   ├── test_chord_definitions.py
│   ├── test_db_manager.py
│   ├── test_gamification_policy.py
│   ├── test_music_theory.py
│   ├── test_pitch_tracker.py
│   └── test_scale_definitions.py
├── analyze_guitar_test.py
├── record_guitar_test.py
├── pyproject.toml
├── .gitignore
└── README.md
```

### Source Responsibilities

| Area | Responsibility |
|---|---|
| `src/main.py` | Application entry point; initializes shared state, views, UI shell, and audio engine. |
| `src/core/` | Central observable application state, view selection, live pitch state, and practice/progression events. |
| `src/domain/` | Music-theory calculations, chord and scale definitions, sequence generation, and gamification rules. |
| `src/dsp/` | Audio-device management, capture and processing pipeline, pitch tracking, chromagram analysis, and generated audio playback. |
| `src/storage/` | SQLite data access and platform-specific application-data paths. |
| `src/ui/` | Flet application shell, navigation, dialogs, and feature views. |
| `tests/` | Unit and integration-oriented tests for state, audio processing, theory, storage, scales, chords, and progression rules. |
| Root diagnostic scripts | Manual audio recording and guitar pitch-analysis utilities. |

---

## How the Application Works

### Audio Processing

The live audio path is separated from the Flet interface:

```text
Audio Input Device
       |
       v
SoundDevice / PortAudio
       |
       v
Audio Callback
       |
       v
Bounded Audio Queue
       |
       v
Background DSP Worker
       |
       +--------------------------+
       |                          |
       v                          v
Autocorrelation Pitch        FFT Chromagram
Tracker                      Analyzer
       |                          |
       v                          v
Live Note / Cents             Active Pitch Classes
       |                          |
       +-------------+------------+
                     |
                     v
                AppState
                     |
                     v
              Flet UI Views
```

The PortAudio callback copies incoming samples into a bounded queue. A background worker maintains the rolling analysis buffer and runs the pitch and chromagram analyzers. Pitch updates are dispatched to the Flet event loop; the interface does not perform the main DSP calculations inside the audio callback.

### Application State and UI

`AppState` is the shared state container. It tracks the active view, trainer mode, target information, live pitch result, timing preference, and progression data. Views subscribe to state notifications and update when relevant state changes.

`AppShell` provides the background, header navigation, and active-view container. Individual screens are implemented separately under `src/ui/views/`, while reusable navigation and dialogs live under `src/ui/components/`.

### Domain and Persistence

The domain layer contains musical definitions and rules without owning the UI. The storage layer provides SQLite access through `DatabaseManager`. The database stores the user profile, practice attempts, unlocked badges, and Hero Boss progress.

---

## Installation

### Requirements

- Python 3.10 or newer.
- Git.
- An audio input device for the live Trainer and Tuner features.
- Windows, macOS, or Linux with a supported audio backend. Audio-device availability depends on the operating system and installed drivers.

### 1. Clone the Repository

```bash
git clone https://github.com/RunicAudio/Bragi.git
cd Bragi
```

### 2. Create a Virtual Environment

**Windows PowerShell**

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

**macOS / Linux**

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install Bragi and Its Dependencies

From the repository root:

```bash
python -m pip install --upgrade pip
python -m pip install -e .
```

On Linux, SoundDevice/PortAudio may require system audio development libraries or PortAudio packages supplied by the distribution.

---

## Running Bragi

Run the application from the repository root:

```bash
python src/main.py
```

The application initializes its shared state and views, then starts the audio engine. Connect and configure an input device before using live-input exercises.

---

## Audio Setup

1. Connect the guitar or other instrument to an audio interface.
2. Connect the interface to the computer and ensure its driver is available to the operating system.
3. Launch Bragi.
4. Open the audio-input setup dialog from the header.
5. Select the intended input device.
6. Play a note and verify that the live input indicator responds.

### Suggested Starting Configuration

| Setting | Starting point |
|---|---|
| Sample rate | Use the input device's native rate; 48 kHz is a suitable common setting. |
| Input | A direct instrument input or a clean interface line input. |
| Input level | Strong enough for reliable analysis without clipping. |
| Signal | Prefer a clean, relatively noise-free signal for pitch exercises. |

Bragi requests mono input for its current live-analysis stream. The audio engine queries the selected device's default sample rate and attempts that rate before trying an alternate common rate.

---

## Tests

Install the project and pytest in the active environment, then run the test suite from the repository root:

```powershell
python -m pytest -v
```

Run an individual test module when working on a specific component:

```powershell
python -m pytest tests/test_pitch_tracker.py -v
python -m pytest tests/test_audio_engine.py -v
```

The real-guitar fixture at `tests/fixtures/real_guitar/low_e2.wav` supports testing against a recorded instrument signal. The root-level `record_guitar_test.py` and `analyze_guitar_test.py` scripts are manual diagnostic tools; they are not part of the automated pytest suite.

---

## Local Data

Bragi uses SQLite for user progression and practice history. The database is created in the operating system's application-data directory by `src/storage/path_utils.py`:

| Platform | Application data directory |
|---|---|
| Windows | `%APPDATA%/Bragi` |
| macOS | `~/Library/Application Support/Bragi` |
| Linux / other Unix | `~/.config/Bragi` |

The default database filename is `bragi_progress.db`. It contains the user profile, practice-attempt history, unlocked badge IDs, and Hero Boss counters. These files are local application data and should not be committed to the repository.

---

## Current Capabilities and Known Limitations

The following describes the implementation on `main`, rather than intended future behavior:

- **Single-note validation:** the trainer checks the detected note name and in-tune state, and displays a target string. It does not currently verify the physical string or octave independently.
- **Continuous pitch analysis:** the pitch tracker analyzes rolling audio frames. A dedicated note-onset detector and robust idle-noise rejection are not yet implemented.
- **Chord recognition:** strummed-chord validation checks for the target pitch classes. It does not identify a complete guitar voicing, inversion, string assignment, or fret position.
- **Arpeggio recognition:** arpeggio mode checks accumulated pitch classes over a 2.5-second window. It does not yet validate note order, rhythmic accuracy, or a specific voicing.
- **Ear-training scope:** the current UI offers single-pitch and four-way chord-quality exercises. Interval training is not currently exposed as an exercise mode.
- **Progression streak:** the stored streak increments after a correct answer and resets after an incorrect answer. It is a consecutive-answer streak, not a calendar-based daily practice streak.
- **Badge progression:** 40 badge definitions are present, but the current unlock evaluation only checks a subset of badge IDs and conditions.
- **Cross-platform audio:** the code uses SoundDevice, but reliable device selection and audio behavior still depend on each platform's audio backend and hardware.

These are active development areas and should be considered when interpreting trainer results or analytics.

---

## Development

### Branching

Use `main` as the stable baseline. Develop changes on `dev` or a focused feature branch, run the relevant tests, and integrate changes into `main` after review.

### Development Practices

- Keep real-time audio capture callbacks short; perform analysis in the background worker.
- Keep DSP algorithms in `src/dsp/` and avoid coupling them to Flet controls.
- Keep music-theory definitions and calculations in `src/domain/`.
- Keep shared application state and event notifications in `src/core/app_state.py`.
- Keep database access and local data paths in `src/storage/`.
- Keep screen-specific presentation in `src/ui/views/` and reusable UI elements in `src/ui/components/`.
- Add or update tests in `tests/` when changing behavior.
- Do not commit virtual environments, local databases, caches, or generated build output.

### Manual Audio Diagnostics

The repository includes two root-level utilities:

- `record_guitar_test.py` — records an input stream for manual inspection.
- `analyze_guitar_test.py` — analyzes recorded guitar audio and reports pitch-detection results.

Use these scripts when investigating input-level, device, or pitch-tracking behavior.

---

## License

No license has been added to the repository yet. Until a license is published, the project should not be assumed to grant permissions for redistribution or reuse.

---

**Bragi — Learn the Notes. Understand the Music. Master the Instrument.**
