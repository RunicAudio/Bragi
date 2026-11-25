# Bragi

**Train your ear. Understand every chord. Build a stronger fretboard.**

Bragi is a desktop music-practice application built for guitarists and other stringed-instrument players who want to connect what they hear, what they play, and what they understand about music theory.

It combines live instrument input, chromatic pitch detection, practical note and chord exercises, ear training, interactive theory explanations, and player-specific progress tracking in one application. Instead of functioning only as a tuner or a collection of flash cards, Bragi gives players a place to practise musical recognition, test their understanding against a live instrument, and track their development over time.

Bragi is actively developed in Python with Flet. Its audio-analysis pipeline uses SoundDevice, NumPy, and SciPy-compatible numerical processing, while music theory, application state, and local persistence are separated into dedicated modules.

> **Project status:** Bragi currently includes working Trainer, Tuner, Ear Training, and Analytics views, plus player-profile management and contextual chord-theory hints. Audio-device behavior and some progression rules continue to evolve. See [Current Capabilities and Known Limitations](#current-capabilities-and-known-limitations) for the implemented scope.

---

## Why Bragi?

Musicians often practise technique, learn chord shapes, tune their instruments, and study theory in separate places. Bragi brings several of those activities together around a simple loop:

1. **See a musical target** — a note or chord to identify and play.
2. **Play it on your instrument** — Bragi listens to the incoming audio.
3. **Get immediate feedback** — the app evaluates the detected pitch or chord pitch classes.
4. **Understand what you played** — open contextual hints to explore chord formulas, intervals, and note spelling.
5. **Build consistency** — review practice statistics, XP, achievements, and challenge progress.

The goal is not just to play the right shape. It is to recognize the notes and intervals that make the music work.

## Features

### Live Instrument Trainer

Practise against real audio input in three modes:

- **Single Note:** receive a target note and string, play it, and advance when the detected note matches and remains within the configured tuning tolerance for the selected hold duration.
- **Strummed Chord:** play a chord and let Bragi compare the detected pitch classes with the target chord.
- **Arpeggio Chord:** pick through a chord; Bragi accumulates detected pitch classes over a rolling 2.5-second window and checks whether the target chord tones have been played.

The Trainer includes target skipping, configurable trainer mode, adjustable auto-advance hold timing, live pitch feedback, and contextual theory hints.

### Interactive Chord Theory

The Hint & Theory dialog turns a chord target into a short theory lesson.

- Reveal progressive hints before viewing the full answer.
- Inspect the chord's root and quality.
- See its chord formula (for example, 1–b3–5).
- Review each chord tone, its correctly spelled note name, interval name, and reference-scale degree when defined.
- Explore why a chord is built from those notes rather than memorizing a shape alone.

The underlying theory engine separates diatonic interval spelling, chromatic semitone distance, chord formulas, and reference-scale degrees. This helps distinguish notes that sound enharmonically alike but have different theoretical spellings.

### Chromatic Tuner and Pitch Detection

Bragi analyses live mono input and estimates the fundamental frequency of a played note. The live pitch state includes:

- Note name and pitch class.
- Estimated frequency.
- Cents deviation from the nearest equal-tempered note.
- In-tune status.
- Input RMS level and silence status.

The chromatic tuner presents the detected note, cents deviation, and a visual tuning indicator. A live input setup dialog lists available input devices and provides a signal-level test.

The current pitch tracker uses autocorrelation, peak selection, and parabolic interpolation. The tuner and Single Note Trainer share the same live pitch state.

### Chord and Pitch-Class Analysis

A separate FFT-based chromagram analyzer maps spectral energy into the 12 pitch classes. A short multi-frame history and harmonic attenuation help produce candidate pitch classes for strummed-chord practice. The audio engine also maintains the rolling pitch-class history used by arpeggio practice.

This allows Bragi to work beyond a single isolated note: players can practise hearing and producing chord tones as part of a complete sound.

### Ear Training

Ear Training currently offers two locally generated listening exercises:

- **Single Pitch:** identify a note from a set of note-name choices.
- **Chord Quality:** distinguish between major, minor, diminished, and suspended-fourth triads.

Examples include replay controls so players can listen again before answering.

### Player Profiles, Analytics, and Progression

Bragi supports multiple named player profiles on the same installation. Each profile maintains its own:

- XP and user level.
- Practice-attempt history and analytics.
- Current consecutive-correct-answer streak.
- Unlocked achievement badges.
- Hero Boss challenge progress.

Switch profiles from the **Players** control in the header, or create a new named profile. The database uses player-scoped records, and the original single-player database is migrated into the initial Player 1 profile.

The Analytics view reports total attempts, accuracy, average response time, XP, level, unlocked badges, and progress toward the Hero Boss challenge. The challenge tracks consecutive note, chord, and arpeggio successes completed within its response-time requirement.

**Progress terminology:** the current streak is a consecutive-correct-answer count, not a calendar-based daily practice streak.

There are 40 badge definitions across the Trainer, Tuner, Ear Training, and Analytics categories. Unlock evaluation is currently implemented for a subset of those definitions; the full catalog should not be interpreted as meaning every badge condition is active.

---

## Supported Musical Scope

Bragi is designed around practical note and chord recognition for fretted string instruments, especially guitar. Its chromatic pitch analysis can also be useful with bass and other instruments that produce a clear monophonic signal within the tracker’s working range.

Current practice content includes:

- Chromatic note names, including sharp and flat spellings.
- Single-note targets.
- Major, minor, dominant seventh, major seventh, minor seventh, suspended, and diminished chord structures where supported by the chord-definition engine.
- Strummed chord pitch-class matching.
- Arpeggiated chord-tone accumulation.
- Single-pitch and basic triad-quality ear training.

Bragi is an audio-based practice and learning tool. It does not currently identify a complete guitar fingering, fretboard position, inversion, or exact string-by-string voicing from a recording.

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
| SQLite | Local player profiles, practice history, and progression |
| pytest | Automated tests |
| setuptools | Package and editable-install configuration |

Runtime dependencies are declared in `pyproject.toml`.

---

## Project Structure

The following tree reflects the current `main` branch at the time of this update. It excludes generated files, local environments, and user data.

```text
Bragi/
├── .github/
│   └── workflows/
│       └── build.yml
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
│   │   ├── chord_theory.py
│   │   ├── gamification_policy.py
│   │   ├── music_theory.py
│   │   ├── note_spelling.py
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
│       │       ├── player_modal.py
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
│   ├── test_chord_theory.py
│   ├── test_db_manager.py
│   ├── test_gamification_policy.py
│   ├── test_music_theory.py
│   ├── test_note_spelling.py
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
| `src/core/` | Shared observable application state, view selection, live pitch state, player switching, and practice/progression events. |
| `src/domain/` | Music-theory calculations, chord and scale definitions, note spelling, chord explanations, and gamification rules. |
| `src/dsp/` | Audio-device management, capture and processing pipeline, pitch tracking, chromagram analysis, and generated audio playback. |
| `src/storage/` | SQLite data access, multi-player persistence, database migration, and platform-specific application-data paths. |
| `src/ui/` | Flet application shell, navigation, dialogs, player management, and feature views. |
| `tests/` | Automated tests for application state, audio processing, theory, storage, scales, chords, note spelling, and progression rules. |
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

`AppState` is the shared state container. It tracks the active view, trainer mode, target information, live pitch result, timing preference, active player, and progression data. Views subscribe to state notifications and update when relevant state changes.

`AppShell` provides the background, header navigation, and active-view container. Individual screens are implemented under `src/ui/views/`, while reusable navigation and dialogs live under `src/ui/components/`.

### Domain and Persistence

The domain layer contains musical definitions and rules without owning the UI. Chord construction and note spelling are handled independently of audio processing and Flet. The storage layer provides SQLite access through `DatabaseManager`, with records scoped to individual player IDs.

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

1. Connect your instrument to an audio interface or supported audio input.
2. Connect the interface to the computer and ensure its driver is available to the operating system.
3. Launch Bragi.
4. Open **Audio Input Setup** from the header.
5. Select the intended input device.
6. Play a note and verify that the live input meter and pitch display respond.

### Suggested Starting Configuration

| Setting | Starting point |
|---|---|
| Sample rate | Use the input device's native rate; 48 kHz is a suitable common setting. |
| Input | A direct instrument input or a clean interface line/instrument input. |
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
python -m pytest tests/test_chord_theory.py -v
python -m pytest tests/test_db_manager.py -v
```

The real-guitar fixture at `tests/fixtures/real_guitar/low_e2.wav` supports testing against a recorded instrument signal. The root-level `record_guitar_test.py` and `analyze_guitar_test.py` scripts are manual diagnostic tools; they are not part of the automated pytest suite.

---

## Local Data

Bragi uses SQLite for player profiles, XP, practice history, unlocked badges, and Hero Boss progress. The database is created in the operating system's application-data directory by `src/storage/path_utils.py`:

| Platform | Application data directory |
|---|---|
| Windows | `%APPDATA%/Bragi` |
| macOS | `~/Library/Application Support/Bragi` |
| Linux / other Unix | `~/.config/Bragi` |

The default database filename is `bragi_progress.db`. Existing single-player data is migrated into the initial Player 1 profile when the multi-player schema is initialized. These files are local application data and should not be committed to the repository.

---

## Current Capabilities and Known Limitations

The following describes the implementation on `main`, rather than intended future behavior:

- **Single-note validation:** the Trainer checks the detected note name and in-tune state, and displays a target string. It does not currently verify the physical string or octave independently.
- **Continuous pitch analysis:** the pitch tracker analyzes rolling audio frames. A dedicated note-onset detector and robust idle-noise rejection are not yet implemented.
- **Chord recognition:** strummed-chord validation checks for the target pitch classes. It does not identify a complete guitar voicing, inversion, string assignment, or fret position.
- **Arpeggio recognition:** arpeggio mode checks accumulated pitch classes over a 2.5-second window. It does not yet validate note order, rhythmic accuracy, or a specific voicing.
- **Ear-training scope:** the current UI offers single-pitch and four-way chord-quality exercises. Interval training is not currently exposed as an exercise mode.
- **Tuning scope:** the tuner is chromatic. Alternate-tuning workflows and string-by-string tuning plans are not currently exposed as dedicated features.
- **Progression streak:** the stored streak increments after a correct answer and resets after an incorrect answer. It is a consecutive-answer streak, not a calendar-based daily practice streak.
- **Badge progression:** 40 badge definitions are present, but the current unlock evaluation only checks a subset of badge IDs and conditions.
- **Cross-platform audio:** the code uses SoundDevice, but reliable device selection and audio behavior still depend on each platform's audio backend and hardware.

These limitations are active development areas and should be considered when interpreting trainer results or analytics.

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

**Bragi — Hear the Notes. Understand the Chords. Master the Fretboard.**
