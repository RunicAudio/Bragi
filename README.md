# Bragi

**Train your ear. Understand every chord. Build a stronger fretboard.**

Bragi is a desktop music-practice application for guitarists and other fretted-string players. It brings live instrument input, pitch detection, note and chord exercises, ear training, music-theory explanations, configurable instrument tunings, and player-specific progress tracking into one application.

Bragi is built with Python and Flet. Its audio pipeline uses SoundDevice/PortAudio, NumPy, and SciPy-compatible numerical processing. Music theory, application state, and local persistence are separated into dedicated modules.

> **Project status — Beta:** The current release line is **0.2.0**. The `v0.2.0-beta.1` tag has been pushed and the Windows release workflow is being validated. The workflow is configured to publish a Windows installer and portable ZIP when its build and tests succeed. Check [GitHub Actions](https://github.com/RunicAudio/Bragi/actions) and [Releases](https://github.com/RunicAudio/Bragi/releases) for the latest status and available downloads.

## What Bragi Does

Bragi is designed around a practice loop:

1. Receive a note or chord target.
2. Play the target through an audio interface or supported input.
3. Get live pitch feedback and automatic exercise evaluation.
4. Open a contextual theory hint to understand the chord's construction.
5. Track practice accuracy, XP, achievements, and challenge progress.

It is an audio-based practice and learning tool. It does not currently identify a complete guitar fingering, fretboard position, inversion, or exact string-by-string voicing from a recording.

## Features

### Home and Navigation

- Home screen with a central Bragi hub and four circular navigation buttons for Trainer, Tuner, Ear Training, and Analytics.
- Header navigation remains available throughout the app.
- Clicking the Bragi logo in the header returns to Home.
- Each main view has its own background image.

### Live Instrument Trainer

The Trainer provides three exercise modes:

- **Single Note:** receive a note and string target, play it, and advance when the detected pitch satisfies the note and tuning checks for the configured hold duration.
- **Strummed Chord:** strum a chord and let Bragi compare detected pitch classes with the target chord.
- **Arpeggio Chord:** pick through a chord. Bragi accumulates detected pitch classes over a rolling 2.5-second window and checks for the required chord tones.

The Trainer also includes:

- Target skipping.
- Adjustable auto-advance hold timing.
- Live pitch feedback.
- Instrument-aware string numbering and tuning labels.
- Contextual chord-theory hints.

### Chord Theory and Hint Dialog

The Hint & Theory dialog provides progressive guidance for the current chord target:

- Reveal hints before displaying the full explanation.
- Inspect the chord root and quality.
- Review the chord formula, such as 1–b3–5.
- See correctly spelled chord-tone names and interval names.
- Review reference-scale degrees where defined.

The theory layer separates diatonic interval spelling from chromatic semitone distance. It supports enharmonic spellings and helps distinguish notes that sound the same but have different theoretical spellings.

### Chromatic Tuner and Pitch Detection

The tuner displays:

- Detected note name.
- Estimated frequency.
- Cents deviation from the nearest equal-tempered pitch.
- In-tune feedback.
- A visual tuning indicator.

The live pitch tracker uses autocorrelation, peak selection, and parabolic interpolation. The Tuner and Single Note Trainer share the same live pitch state.

### Chord and Pitch-Class Analysis

A separate FFT-based chromagram analyzer maps spectral energy into the 12 pitch classes. A short multi-frame history and harmonic attenuation help identify candidate pitch classes for strummed-chord practice. The audio engine also maintains the rolling pitch-class history used by arpeggio practice.

### Ear Training

The current Ear Training view includes two locally generated exercise types:

- **Single Pitch:** identify a note from a set of note-name choices.
- **Chord Quality:** distinguish major, minor, diminished, and suspended-fourth triads.

Questions include replay controls so the player can listen again before answering.

### Instruments and Custom Tunings

The instrument configuration system currently supports:

- Guitar
- Bass
- Ukulele
- Baritone ukulele
- Banjo

Each instrument has a standard tuning configuration. Players can also configure custom string counts and individual string note/octave assignments, within the supported 1–12 string range.

Instrument and tuning configurations are saved separately for each player. The Trainer uses the active configuration when displaying string targets and selecting string numbers.

### Player Profiles and Progression

Multiple named player profiles can be used on the same installation. Each player has independent:

- XP and level.
- Practice-attempt history and analytics.
- Consecutive-correct-answer streak.
- Unlocked badges.
- Hero Boss challenge progress.
- Instrument and tuning configuration.

The Players dialog supports creating, switching, renaming, resetting, and deleting profiles. Resetting clears the selected player's progress while retaining the profile and its instrument configuration. Deleting a player removes that player's associated records; the last remaining player cannot be deleted. Deleting the active player switches the app to another remaining profile.

The original single-player database is migrated into the initial Player 1 profile.

### Analytics

The Analytics view reports practice totals and progression, including:

- Total attempts and accuracy.
- Average response time.
- XP and level.
- Unlocked badges.
- Hero Boss challenge progress.

The Hero Boss challenge tracks consecutive note, chord, and arpeggio successes against its response-time requirement.

There are 40 badge definitions across the application categories. Unlock evaluation is currently implemented for a subset of those definitions; the full catalog does not mean every badge condition is active.

**Streak terminology:** the stored streak is a count of consecutive correct answers. It is not a calendar-based daily practice streak. The current Analytics screen still labels this value as “days”; that display label is inaccurate.

## Supported Musical Scope

Current theory and practice content includes:

- Chromatic note names, including sharp, flat, enharmonic, and Unicode accidental spellings.
- Major and minor triads.
- Dominant seventh, major seventh, and minor seventh chords.
- Suspended-second and suspended-fourth chords.
- Diminished triads.
- Single-note targets.
- Strummed chord pitch-class matching.
- Arpeggiated chord-tone accumulation.
- Single-pitch and basic triad-quality ear training.

Bragi does not yet validate a specific fretboard position, complete guitar voicing, inversion, string assignment, note order in an arpeggio, or rhythmic accuracy.

## Platform and Release Status

### Current beta distribution target

The current automated release workflow builds **Windows x64** packages:

- **Installer:** `Bragi-0.2.0-setup.exe`
- **Portable archive:** `Bragi-0.2.0-Windows-x64.zip`

The installer is created with Inno Setup and provides an application shortcut and uninstaller. The portable ZIP contains the complete Flet application bundle. Extract the ZIP before launching Bragi; do not run the executable from inside the compressed archive.

The Windows build bundles the application runtime and required files. Users do not need to install Python separately to run the packaged Windows application.

The current workflow is triggered by pushing a version tag beginning with `v`. It checks that the tag's base version matches `project.version` in `pyproject.toml`, installs dependencies, runs pytest, builds the Windows application, creates the installer and ZIP, and publishes a GitHub prerelease. For example:

```powershell
git checkout main
git pull --ff-only origin main
git tag -a v0.2.0-beta.1 -m "Bragi 0.2.0 Beta 1"
git push origin v0.2.0-beta.1
```

The workflow uses Python 3.12 for its build environment and the project-pinned Flet 1.0.4 release.

### Other platforms

Linux and macOS source execution may be possible where Python, Flet, PortAudio, and a compatible audio backend are available, but automated Linux and macOS packages are not part of the current beta workflow.

Audio-device discovery is currently Windows-oriented: the preferred device list searches for specific Windows WASAPI and WDM-KS endpoints, including HeadRush and common Windows audio devices. The audio engine can fall back to the system's default input, but generic device enumeration and selection have not yet been generalized across operating systems.

Android and iOS packages are not currently supported. Mobile distribution requires additional platform-specific audio capture and packaging work.

## Technology

| Technology | Role |
|---|---|
| Python 3.10+ | Application language and development runtime |
| Flet 1.0.4 | Desktop UI and event handling |
| NumPy | Audio buffers and numerical analysis |
| SciPy | Scientific-computing dependency |
| SoundDevice / PortAudio | Audio input and generated audio playback |
| Pydantic | Typed data models and validation |
| SQLite | Local player profiles, practice history, and progression |
| pytest | Automated tests |
| setuptools | Package and editable-install configuration |
| Inno Setup | Windows installer generation |

Runtime dependencies and Flet packaging metadata are declared in `pyproject.toml`.

## Project Structure

The following tree shows the main application and release files on the current `main` branch. Generated build output, local environments, and user data are excluded.

```text
Bragi/
├── .github/
│   └── workflows/
│       └── build.yml
├── installer.iss
├── src/
│   ├── assets/
│   │   ├── analytic_bg.png
│   │   ├── ear_trainer_bg.png
│   │   ├── home_bg.png
│   │   ├── trainer_bg.png
│   │   ├── tuner_bg.png
│   │   ├── icon.ico
│   │   ├── icon.png
│   │   ├── logo.ico
│   │   ├── logo.png
│   │   └── release-description.md
│   ├── main.py
│   ├── core/
│   │   └── app_state.py
│   ├── domain/
│   │   ├── chord_definitions.py
│   │   ├── chord_theory.py
│   │   ├── gamification_policy.py
│   │   ├── instrument_definitions.py
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
│       │       ├── instrument_modal.py
│       │       ├── player_modal.py
│       │       └── timing_modal.py
│       └── views/
│           ├── analytics_view.py
│           ├── ear_training_view.py
│           ├── home_view.py
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
│   ├── test_instrument_definitions.py
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
| `src/core/` | Shared application state, view selection, live pitch state, player switching, and progression events. |
| `src/domain/` | Music theory, chord and scale definitions, note spelling, instrument configurations, and gamification rules. |
| `src/dsp/` | Audio-device management, capture and processing pipeline, pitch tracking, chromagram analysis, and generated audio playback. |
| `src/storage/` | SQLite access, multi-player persistence, schema migration, and platform-specific application-data paths. |
| `src/ui/` | Flet application shell, navigation, feature views, and reusable dialogs. |
| `src/assets/` | Application icons, logo assets, and per-view backgrounds. |
| `tests/` | Automated tests for application state, audio processing, theory, storage, instruments, and progression rules. |
| Root diagnostic scripts | Manual audio recording and guitar pitch-analysis utilities. |

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

The PortAudio callback copies incoming samples into a bounded queue. A background worker maintains the rolling analysis buffer and runs pitch and chromagram analysis. Pitch updates are dispatched to the Flet event loop; the main DSP calculations are kept out of the audio callback.

### Application State and Persistence

`AppState` holds the active view, trainer mode, target information, live pitch result, timing preference, active player, instrument configuration, and progression state. Views subscribe to state notifications and refresh when relevant values change.

`DatabaseManager` stores player-scoped profiles, practice attempts, unlocked badges, Hero Boss progress, and instrument configurations in SQLite. Database migrations preserve legacy single-player progress when upgrading to the multi-player schema.

## Development Setup

### Requirements

- Python 3.10 or newer.
- Git.
- An audio input device for live Trainer and Tuner features.
- A supported local audio backend. PortAudio availability and device behavior depend on the operating system and installed drivers.

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

On Linux, SoundDevice may require PortAudio packages or development libraries supplied by the distribution.

## Running Bragi

Run the application from the repository root:

```bash
python src/main.py
```

The application initializes its shared state and views, then starts the audio engine. Connect and configure an input device before using live-input exercises.

## Audio Setup

1. Connect your instrument to an audio interface or supported audio input.
2. Ensure the interface and its driver are available to the operating system.
3. Launch Bragi.
4. Open the audio-input device control in the header.
5. Select an input device when it appears in the list.
6. Play a note and verify that the live input level and pitch display respond.

### Suggested Starting Configuration

| Setting | Starting point |
|---|---|
| Sample rate | Use the input device's native rate; 48 kHz is a suitable common setting. |
| Input | A direct instrument input or clean interface line/instrument input. |
| Input level | Strong enough for reliable analysis without clipping. |
| Signal | Prefer a clean, relatively noise-free signal for pitch exercises. |

Bragi requests mono input for its current live-analysis stream. The audio engine queries the selected device's default sample rate and tries that rate before attempting the alternate common rate.

## Tests

Install the project in the active environment, then run the test suite from the repository root:

```powershell
python -m pytest -v
```

Run an individual test module when working on a specific component:

```powershell
python -m pytest tests/test_pitch_tracker.py -v
python -m pytest tests/test_chord_theory.py -v
python -m pytest tests/test_db_manager.py -v
python -m pytest tests/test_instrument_definitions.py -v
```

The real-guitar fixture at `tests/fixtures/real_guitar/low_e2.wav` supports testing against a recorded instrument signal. The root-level `record_guitar_test.py` and `analyze_guitar_test.py` scripts are manual diagnostic tools and are not part of the automated pytest suite.

The GitHub release workflow runs the full pytest suite before attempting to package the Windows application.

## Local Data

Bragi stores player profiles, XP, practice history, unlocked badges, Hero Boss progress, and instrument configurations in a local SQLite database. The database path is managed by `src/storage/path_utils.py`.

| Platform | Application data directory |
|---|---|
| Windows | `%USERPROFILE%\AppData\Roaming\Bragi` (normally `%APPDATA%\Bragi`) |
| macOS | `~/Library/Application Support/Bragi` |
| Linux / other Unix | `~/.config/Bragi` |

The default database filename is `bragi_progress.db`. Local databases and user data should not be committed to the repository.

## Current Capabilities and Known Limitations

The following describes the implementation on `main`, rather than intended future behavior:

- **Single-note validation:** the Trainer displays the target string and note and checks the detected pitch/in-tune state. It does not independently confirm the physical string that produced the sound.
- **Continuous pitch analysis:** the pitch tracker analyzes rolling audio frames. A dedicated note-onset detector and robust idle-noise rejection are not yet implemented.
- **Chord recognition:** strummed-chord validation checks target pitch classes. It does not identify a complete guitar voicing, inversion, string assignment, or fret position.
- **Arpeggio recognition:** arpeggio mode checks accumulated pitch classes over a 2.5-second window. It does not yet validate note order, rhythmic accuracy, or a specific voicing.
- **Ear-training scope:** the current UI offers single-pitch and four-way chord-quality exercises. Interval-training modes are not currently exposed.
- **Tuning scope:** the tuner is chromatic. It does not currently provide automatic string-by-string tuning plans or alternate-tuning workflows.
- **Progression streak:** the stored streak counts consecutive correct answers, not calendar days. The Analytics screen's current “days” label is inaccurate.
- **Badge progression:** 40 badge definitions are present, but unlock evaluation currently checks only a subset of badge IDs and conditions.
- **Audio-device selection:** the preferred device list is Windows-specific. Generic input enumeration and selection on Linux and macOS still need work.
- **Platform packages:** the current automated beta workflow publishes Windows x64 packages only. Linux/macOS packages and Android/iOS apps are not currently part of the release pipeline.

These limitations should be considered when interpreting exercise results and analytics.

## Development Practices

- Keep real-time audio capture callbacks short; perform analysis in the background worker.
- Keep DSP algorithms in `src/dsp/` and avoid coupling them to Flet controls.
- Keep music-theory definitions and calculations in `src/domain/`.
- Keep shared application state and notifications in `src/core/app_state.py`.
- Keep database access and local data paths in `src/storage/`.
- Keep screen-specific presentation in `src/ui/views/` and reusable UI elements in `src/ui/components/`.
- Add or update tests when changing behavior.
- Do not commit virtual environments, local databases, caches, or generated build output.

## Manual Audio Diagnostics

The repository includes two root-level utilities:

- `record_guitar_test.py` — records an input stream for manual inspection.
- `analyze_guitar_test.py` — analyzes recorded guitar audio and reports pitch-detection results.

Use these scripts when investigating input-level, device, or pitch-tracking behavior.

## License

No license has been added to the repository yet. Until a license is selected and committed, all rights remain with the copyright holder. Do not assume the repository is open source or that redistribution rights are granted beyond the terms explicitly stated by the copyright holder.
